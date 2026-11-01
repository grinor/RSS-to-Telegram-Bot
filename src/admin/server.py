"""Same-process aiohttp admin API; opt in with WEB_ADMIN_TOKEN."""
import asyncio
import hmac
import logging
import json
import os
from pathlib import Path
from aiohttp import web
from tortoise.exceptions import IntegrityError, DoesNotExist
from .. import db, env
from . import backup
from .validation import options, global_options, integer, url

logger = logging.getLogger('RSStT.admin')
ASSETS = Path(__file__).parent
TOKEN_KEY = web.AppKey('token', str)
LOCK_KEY = web.AppKey('write_lock', asyncio.Lock)


@web.middleware
async def security(request, handler):
    try:
        if request.path.startswith('/api/'):
            expected = 'Bearer ' + request.app[TOKEN_KEY]
            provided = request.headers.get('Authorization', '')
            if not hmac.compare_digest(provided.encode(), expected.encode()):
                raise web.HTTPUnauthorized(text='需要管理员登录')
            if request.method not in ('GET', 'HEAD'):
                origin = request.headers.get('Origin')
                if origin and origin != f'{request.scheme}://{request.host}':
                    raise web.HTTPForbidden(text='请求来源无效')
                if request.method in ('POST', 'PUT', 'PATCH') and request.path != '/api/restore' and not request.path.endswith('/opml') and request.content_type != 'application/json':
                    raise web.HTTPUnsupportedMediaType(text='需要 JSON 请求')
        response = await handler(request)
    except (ValueError, TypeError, KeyError) as exc:
        response = web.json_response({'error': str(exc)}, status=400)
    except (DoesNotExist,):
        response = web.json_response({'error': '记录不存在'}, status=404)
    except IntegrityError:
        response = web.json_response({'error': '记录已存在或关联关系无效'}, status=409)
    except web.HTTPException as exc:
        response = web.json_response({'error': exc.text}, status=exc.status)
    response.headers.update({
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY',
        'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; "
                                   "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'",
    })
    return response


async def body(request):
    value = await request.json()
    if not isinstance(value, dict):
        raise ValueError('请求必须是 JSON 对象')
    return value


async def index(request):
    return web.Response(text=(ASSETS / 'index.html').read_text(), content_type='text/html')


async def script(request):
    return web.Response(text=(ASSETS / 'admin.js').read_text(), content_type='application/javascript')


async def state(request):
    users = await db.User.all().order_by('id').values()
    subs = await db.Sub.all().order_by('id').values()
    feeds = {f['id']: f for f in await db.Feed.all().values()}
    for sub in subs:
        sub['feed'] = feeds[sub['feed_id']]
    return web.json_response({'users': users, 'subscriptions': subs, 'options': db.EffectiveOptions.options,
                              'bot': {'id': env.bot_id, 'username': getattr(env.bot_peer, 'username', None)}},
                             dumps=lambda obj: json.dumps(obj, default=str))


async def add_target(request):
    from telethon import utils
    from telethon.tl.types import Channel, Chat
    data = await body(request)
    target = data.get('target')
    if not isinstance(target, str) or len(target) > 128:
        raise ValueError('请输入频道用户名或聊天 ID')
    target = int(target) if target.lstrip('-').isdigit() else target
    try:
        entity = await env.bot.get_entity(target)
        uid = utils.get_peer_id(entity)
        if isinstance(entity, (Channel, Chat)):
            await env.bot.get_permissions(entity, 'me')
            state_value = 51 if isinstance(entity, Chat) or getattr(entity, 'megagroup', False) else 50
        else:
            if not await db.User.filter(id=uid).exists():
                raise ValueError('请先在 Telegram 中向 Bot 发送 /start')
            state_value = 0
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('无法访问目标，请先把 Bot 加入频道/群聊并赋予发送权限') from exc
    await db.User.get_or_create(id=uid, defaults={'state': state_value, 'admin': min(env.MANAGER)})
    return web.json_response({'id': uid})


async def add_sub(request):
    from ..command.inner import sub as inner_sub
    data = await body(request)
    uid = integer(data.get('user_id'), -(2**63), 2**63 - 1)
    target = await db.User.get(id=uid)
    link = url(data.get('url'))
    values = options(data.get('options', {}))
    result = await inner_sub.sub(uid, link, lang=target.lang)
    sub = result['sub']
    if sub is None:
        raise ValueError(result['msg'] or '添加失败，请检查 RSS 地址')
    if values:
        await db.Sub.filter(id=sub.id).update(**values)
        from ..command.inner.utils import update_interval
        await update_interval(sub.feed_id)
    return web.json_response({'id': sub.id}, status=201)


async def edit_sub(request):
    from ..command.inner.utils import update_interval
    sub = await db.Sub.get(id=int(request.match_info['id']))
    values = options(await body(request))
    if values:
        await db.Sub.filter(id=sub.id).update(**values)
        await update_interval(sub.feed_id)
    return web.json_response({'ok': True})


async def delete_sub(request):
    from ..command.inner.utils import update_interval
    sub = await db.Sub.get(id=int(request.match_info['id']))
    fid = sub.feed_id
    await sub.delete()
    await update_interval(fid)
    return web.json_response({'ok': True})


async def edit_user(request):
    from ..command.inner.utils import update_interval
    user = await db.User.get(id=int(request.match_info['id']))
    values = options(await body(request), user=True)
    if values:
        await db.User.filter(id=user.id).update(**values)
        for fid in await user.subs.all().values_list('feed_id', flat=True):
            await update_interval(fid)
    return web.json_response({'ok': True})


async def edit_options(request):
    values = global_options(await body(request))
    for key, value in values.items():
        await db.EffectiveOptions.set(key, value)
    # Recompute feed intervals, including feeds inheriting target defaults.
    from ..command.inner.utils import update_interval
    for fid in await db.Feed.all().values_list('id', flat=True):
        await update_interval(fid)
    await db.EffectiveTasks.init(flush=True)
    return web.json_response({'ok': True})


async def export(request):
    raw = await backup.export_backup(include_runtime=request.query.get('runtime') == '1')
    return web.Response(body=raw, content_type='application/zip', headers={
        'Content-Disposition': 'attachment; filename="rsstt-backup.zip"'})


async def restore(request):
    raw = await request.read()
    data = backup.read_backup(raw)
    if request.query.get('preview') == '1':
        return web.json_response(backup.summary(data))
    if request.headers.get('X-Confirm-Restore') != 'merge':
        raise ValueError('请先预览并确认合并还原')
    # Recovery snapshot created before any modification and retained outside the import transaction.
    recovery = await backup.export_backup(include_runtime=True)
    folder = Path(env.config_folder_path) / 'web-backups'
    folder.mkdir(mode=0o700, exist_ok=True)
    from datetime import datetime, timezone
    destination = folder / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.zip')
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(recovery)
    result = await backup.restore_backup(data, restore_runtime=request.query.get('runtime') == '1')
    result['recovery_backup'] = destination.name
    return web.json_response(result)



async def target_opml(request):
    from . import opml
    uid = integer(int(request.match_info['id']), -(2**63), 2**63 - 1)
    if request.method == 'GET':
        content = await opml.export_feeds(uid)
        return web.Response(body=content, content_type='application/xml', headers={
            'Content-Disposition': f'attachment; filename="rsstt-{uid}.opml"'})
    # Enforce the smaller OPML limit while streaming, including chunked uploads.
    if request.content_length is not None and request.content_length > opml.MAX_OPML_BYTES:
        raise ValueError('OPML 文件不能为空，且不能超过 2 MB')
    raw = bytearray()
    async for chunk in request.content.iter_chunked(65536):
        raw.extend(chunk)
        if len(raw) > opml.MAX_OPML_BYTES:
            raise ValueError('OPML 文件不能为空，且不能超过 2 MB')
    if request.query.get('preview') == '1':
        return web.json_response(await opml.preview(uid, bytes(raw)))
    if request.headers.get('X-Confirm-OPML') != 'import':
        raise ValueError('请先预览并确认 OPML 导入')
    lang = 'en' if request.headers.get('Accept-Language', '').startswith('en') else 'zh-Hans'
    return web.json_response(await opml.import_feeds(uid, bytes(raw), lang=lang))


def create_app(token):
    if not token or len(token) < 32:
        raise ValueError('WEB_ADMIN_TOKEN 至少需要 32 个字符')
    app = web.Application(middlewares=[security], client_max_size=backup.MAX_BYTES)
    app[TOKEN_KEY] = token
    app[LOCK_KEY] = asyncio.Lock()

    def serialized(handler):
        async def wrapped(request):
            async with app[LOCK_KEY]:
                return await handler(request)
        return wrapped

    app.add_routes([
        web.get('/', index), web.get('/admin.js', script), web.get('/api/state', serialized(state)),
        web.post('/api/targets', serialized(add_target)), web.post('/api/subscriptions', serialized(add_sub)),
        web.patch('/api/subscriptions/{id}', serialized(edit_sub)),
        web.delete('/api/subscriptions/{id}', serialized(delete_sub)),
        web.patch('/api/targets/{id}', serialized(edit_user)),
        web.get('/api/targets/{id}/opml', serialized(target_opml)),
        web.post('/api/targets/{id}/opml', serialized(target_opml)), web.patch('/api/options', serialized(edit_options)),
        web.get('/api/backup', serialized(export)), web.post('/api/restore', serialized(restore)),
    ])
    return app


async def start():
    token = os.environ.get('WEB_ADMIN_TOKEN')
    if not token:
        return None
    host = os.environ.get('WEB_ADMIN_HOST', '127.0.0.1')
    port = int(os.environ.get('WEB_ADMIN_PORT', '8080'))
    app = create_app(token)
    runner = web.AppRunner(app, access_log=None)
    try:
        await runner.setup()
        await web.TCPSite(runner, host, port).start()
    except BaseException:
        await runner.cleanup()
        raise
    logger.info('Web admin listening on %s:%s', host, port)
    return runner

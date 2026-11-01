"""Versioned, portable ZIP backups. Never extracts user-controlled filenames."""
import io
import json
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from tortoise.transactions import in_transaction
from .. import db, env
from .validation import options, global_options, integer, url

MAX_BYTES = 16 * 1024 * 1024
RUNTIME_KEYS = {
    'TOKEN', 'MANAGER', 'API_ID', 'API_HASH', 'TELEGRAPH_TOKEN', 'MULTIUSER',
    'ERROR_LOGGING_CHAT', 'T_PROXY', 'R_PROXY', 'HTTP_TIMEOUT', 'VERIFY_TLS',
    'USER_AGENT', 'CRON_SECOND', 'TRAFFIC_SAVING', 'LAZY_MEDIA_VALIDATION',
    'IMG_RELAY_SERVER', 'IMAGES_WESERV_NL', 'IPV6_PRIOR', 'PROXY_BYPASS_PRIVATE',
    'PROXY_BYPASS_DOMAINS', 'HTTP_CONCURRENCY', 'HTTP_CONCURRENCY_PER_HOST',
    'HTTP_MAX_LINE_SIZE', 'HTTP_MAX_FIELD_SIZE', 'TABLE_TO_IMAGE', 'MULTIPROCESSING',
}


async def export_backup(include_runtime=False):
    async with in_transaction():
        data = {
            'format': 'rsstt-web-backup', 'version': 1,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'users': await db.User.all().values(),
            'feeds': await db.Feed.all().values(),
            'subscriptions': await db.Sub.all().values(),
            'options': db.EffectiveOptions.options,
        }
    if include_runtime:
        data['runtime'] = {key: os.environ[key] for key in sorted(RUNTIME_KEYS) if key in os.environ}
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('backup.json', json.dumps(data, ensure_ascii=False, default=str))
        archive.writestr('README.txt', 'RSStT backup v1. Contains private chat IDs and possibly bot credentials.\n'
                          'Restore using the web admin. Telegram session files are deliberately excluded.\n'
                          'DATABASE_URL, web authentication and listen settings are not overwritten.\n')
    return out.getvalue()


def read_backup(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError('备份文件超过 16 MB')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            if len(members) > 5 or sum(m.file_size for m in members) > MAX_BYTES:
                raise ValueError('解压后备份超过限制')
            if sum(m.filename == 'backup.json' for m in members) != 1:
                raise ValueError('缺少唯一的 backup.json')
            data = json.loads(archive.read('backup.json'))
    except (zipfile.BadZipFile, KeyError, RuntimeError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('不是有效的 RSStT 备份 ZIP 文件') from exc
    if not isinstance(data, dict) or data.get('format') != 'rsstt-web-backup' or data.get('version') != 1:
        raise ValueError('备份格式或版本不受支持')
    for key in ('users', 'feeds', 'subscriptions'):
        if not isinstance(data.get(key), list) or len(data[key]) > 100000:
            raise ValueError('备份记录格式无效或过多')
    global_options(data.get('options'))
    users, feeds, pairs, sub_ids = set(), set(), set(), set()
    for row in data['users']:
        if not isinstance(row, dict):
            raise ValueError('用户记录无效')
        uid = integer(row.get('id'), -(2**63), 2**63 - 1)
        if uid == 0 or uid in users:
            raise ValueError('用户 ID 无效或重复')
        users.add(uid)
        integer(row.get('state'), -1, 100)
        if row['state'] not in (-1, 0, 1, 50, 51, 100):
            raise ValueError('用户状态无效')
        if not isinstance(row.get('lang'), str) or len(row['lang']) > 16:
            raise ValueError('语言字段无效')
        if row.get('admin') is not None:
            integer(row['admin'], -(2**63), 2**63 - 1)
        if row.get('sub_limit') is not None:
            integer(row['sub_limit'], -1, 32767)
        options({k: v for k, v in row.items() if k in db.User._meta.fields_map and k in
                 {'interval', 'notify', 'send_mode', 'length_limit', 'link_preview', 'display_author',
                  'display_via', 'display_title', 'display_entry_tags', 'style', 'display_media'}}, user=True)
    links = set()
    for row in data['feeds']:
        if not isinstance(row, dict):
            raise ValueError('订阅源记录无效')
        fid = integer(row.get('id'), 1, 2**31 - 1)
        link = url(row.get('link'))
        if fid in feeds or link in links:
            raise ValueError('订阅源 ID 或地址重复')
        feeds.add(fid)
        links.add(link)
        if not isinstance(row.get('title'), str) or len(row['title']) > 1024:
            raise ValueError('源标题无效')
        if row.get('entry_hashes') is not None and (not isinstance(row['entry_hashes'], list) or
                any(not isinstance(h, str) or not re.fullmatch(r'[0-9a-f]{1,8}', h) for h in row['entry_hashes'])):
            raise ValueError('文章历史记录无效')
    for row in data['subscriptions']:
        if not isinstance(row, dict):
            raise ValueError('订阅记录无效')
        sid = integer(row.get('id'), 1, 2**31 - 1)
        pair = (row.get('user_id'), row.get('feed_id'))
        if any(type(v) is not int for v in pair) or pair[0] not in users or pair[1] not in feeds:
            raise ValueError('订阅关联的目标或源不存在')
        if pair in pairs or sid in sub_ids:
            raise ValueError('重复的订阅记录')
        pairs.add(pair)
        sub_ids.add(sid)
        options({k: v for k, v in row.items() if k not in ('id', 'user_id', 'feed_id', 'created_at', 'updated_at')})
    runtime = data.get('runtime', {})
    if not isinstance(runtime, dict) or set(runtime) - RUNTIME_KEYS or any(
            not isinstance(v, str) or len(v) > 32768 or '\x00' in v for v in runtime.values()):
        raise ValueError('运行配置无效')
    return data


def summary(data):
    return {key: len(data[key]) for key in ('users', 'feeds', 'subscriptions')} | {
        'runtime_included': bool(data.get('runtime')), 'created_at': data.get('created_at')}


async def restore_backup(data, restore_runtime=False):
    # Merge by natural keys: chat ID, feed URL, (chat ID, feed URL). IDs are remapped.
    # No unrelated subscription is removed. A failed DB import rolls back all its changes.
    runtime_path = Path(env.config_folder_path) / 'web-restored.env'
    previous = runtime_path.read_bytes() if runtime_path.exists() else None
    wrote_runtime = False
    try:
        async with in_transaction():
            for row in data['users']:
                fields = {k: v for k, v in row.items() if k in db.User._meta.db_fields and
                          k not in ('id', 'created_at', 'updated_at')}
                await db.User.update_or_create(id=row['id'], defaults=fields)
            feed_map = {}
            for row in data['feeds']:
                # Existing feeds retain delivery history, new feeds inherit the backup's hashes.
                feed, _ = await db.Feed.get_or_create(link=row['link'], defaults={
                    'title': row['title'], 'entry_hashes': row.get('entry_hashes')})
                feed_map[row['id']] = feed.id
            for row in data['subscriptions']:
                values = options({k: v for k, v in row.items() if k not in
                                  ('id', 'user_id', 'feed_id', 'created_at', 'updated_at')})
                await db.Sub.update_or_create(user_id=row['user_id'], feed_id=feed_map[row['feed_id']], defaults=values)
            for key, value in data['options'].items():
                await db.Option.update_or_create(key=key, defaults={'value': str(value)})
            if restore_runtime and data.get('runtime'):
                # dotenv quoted values: escape backslashes/quotes and disable interpolation at load time.
                content = ''.join(f'{k}={json.dumps(v, ensure_ascii=False)}\n' for k, v in data['runtime'].items())
                temporary = runtime_path.with_suffix('.tmp')
                fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, 'w') as stream:
                    stream.write(content)
                os.replace(temporary, runtime_path)
                wrote_runtime = True
    except BaseException:
        if wrote_runtime:
            if previous is None:
                runtime_path.unlink(missing_ok=True)
            else:
                runtime_path.write_bytes(previous)
        raise
    await db.EffectiveOptions.cache()
    from ..command.inner.utils import update_interval
    for fid in await db.Feed.all().values_list('id', flat=True):
        await update_interval(fid)
    await db.EffectiveTasks.init(flush=True)
    return {**summary(data), 'restart_required': wrote_runtime}

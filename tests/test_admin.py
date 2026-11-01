"""Run: PYTHONPATH=. python tests/test_admin.py (no Telegram credentials required)."""
import asyncio
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

_test_dir = tempfile.TemporaryDirectory()
os.environ.update(TOKEN='test', MANAGER='1', NO_UVLOOP='1', MULTIPROCESSING='0',
                  MPLCONFIGDIR=_test_dir.name)
sys.argv = [sys.argv[0], '-c', _test_dir.name]
from src import db, env
from src.admin import backup
from src.admin.server import create_app
from src.keyword_filter import matches_entry, validate_rule
from aiohttp.test_utils import TestClient, TestServer
from tortoise import Tortoise


def pack(data):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('backup.json', json.dumps(data))
    return out.getvalue()


class FilterTests(unittest.TestCase):
    def test_literal_unicode_and_html(self):
        rule = validate_rule({'include': ['AI', '开源'], 'mode': 'all'})
        self.assertTrue(matches_entry({'title': 'ＡＩ', 'content': [{'value': '<p>开<b>源</b>工具</p>'}]}, rule))
        self.assertFalse(matches_entry({'title': 'AI 工具'}, rule))
        self.assertTrue(matches_entry({'title': 'c++'}, {'include': ['c++']}))

    def test_exclude_priority_and_scope(self):
        rule = validate_rule({'include': ['开源'], 'exclude': ['广告']})
        entry = {'title': '开源', 'summary': '<b>广告</b>'}
        self.assertFalse(matches_entry(entry, rule))
        rule['scope'] = 'title'
        self.assertTrue(matches_entry(entry, rule))
        self.assertTrue(matches_entry(entry, None))
        self.assertFalse(matches_entry({'title': '', 'summary': '<script>开源</script>'}, rule))

    def test_validation(self):
        for rule in ({'include': ['']}, {'scope': 'unknown'}, {'include': ['a'] * 101}, {'include': 'a'}):
            with self.assertRaises(ValueError):
                validate_rule(rule)


class AdminTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url='sqlite://:memory:', modules={'models': ['src.db.models']})
        await Tortoise.generate_schemas()
        await db.effective_utils.init()
        self.u = await db.User.create(id=1)
        await db.User.create(id=-10042, state=50, admin=1)
        self.feed = await db.Feed.create(title='测试源', link='https://example.com/rss', entry_hashes=['abcd1234'])
        self.sub = await db.Sub.create(user=self.u, feed=self.feed)
        self.other = await db.Sub.create(user_id=-10042, feed=self.feed,
                                        keyword_filter={'include': ['独立'], 'exclude': [], 'mode': 'any', 'scope': 'all'})
        env.bot_id = 123
        env.bot_peer = type('Bot', (), {'username': 'test_bot'})()
        self.client = TestClient(TestServer(create_app('t' * 32)))
        await self.client.start_server()
        self.headers = {'Authorization': 'Bearer ' + 't' * 32}

    async def asyncTearDown(self):
        await self.client.close()
        await Tortoise.close_connections()

    async def test_auth_security_and_state(self):
        r = await self.client.get('/api/state')
        self.assertEqual(r.status, 401)
        r = await self.client.get('/api/state', headers=self.headers)
        self.assertEqual(r.status, 200)
        self.assertEqual(len((await r.json())['subscriptions']), 2)
        self.assertEqual(r.headers['X-Frame-Options'], 'DENY')
        r = await self.client.patch('/api/options', headers={**self.headers, 'Origin': 'https://evil.example'}, json={})
        self.assertEqual(r.status, 403)
        r = await self.client.get('/')
        self.assertEqual(r.status, 200)
        self.assertIn('RSS 管理台', await r.text())

    async def test_edit_independent_rules_and_schedule(self):
        rule = {'include': ['开源'], 'exclude': ['广告'], 'mode': 'all', 'scope': 'title'}
        r = await self.client.patch(f'/api/subscriptions/{self.sub.id}', headers=self.headers,
                                    json={'keyword_filter': rule, 'title': '新标题', 'state': 0})
        self.assertEqual(r.status, 200, await r.text())
        await self.sub.refresh_from_db(); await self.other.refresh_from_db()
        self.assertEqual(self.sub.keyword_filter, rule)
        self.assertEqual(self.other.keyword_filter['include'], ['独立'])
        r = await self.client.patch(f'/api/subscriptions/{self.sub.id}', headers=self.headers, json={'interval': 0})
        self.assertEqual(r.status, 400)

    async def test_create_and_delete_with_existing_feed(self):
        new_user = await db.User.create(id=2)
        r = await self.client.post('/api/subscriptions', headers=self.headers,
                                   json={'user_id': new_user.id, 'url': self.feed.link,
                                         'options': {'title': '新增', 'keyword_filter': {'exclude': ['广告']}}})
        self.assertEqual(r.status, 201, await r.text())
        sid = (await r.json())['id']
        r = await self.client.delete(f'/api/subscriptions/{sid}', headers=self.headers)
        self.assertEqual(r.status, 200)
        self.assertFalse(await db.Sub.filter(id=sid).exists())
        self.assertTrue(await db.Feed.filter(id=self.feed.id).exists())

    async def test_backup_preview_restore_id_remap(self):
        await db.EffectiveOptions.set('default_interval', 17)
        raw = await backup.export_backup()
        saved = backup.read_backup(raw)
        self.assertNotIn('runtime', saved)
        r = await self.client.post('/api/restore?preview=1', headers=self.headers, data=raw)
        self.assertEqual(r.status, 200, await r.text())
        self.assertEqual((await r.json())['subscriptions'], 2)
        r = await self.client.post('/api/restore', headers=self.headers, data=raw)
        self.assertEqual(r.status, 400)
        await db.Sub.all().delete(); await db.Feed.all().delete()
        extra_feed = await db.Feed.create(id=100, title='保留', link='https://other.example/rss')
        await db.Sub.create(user_id=1, feed=extra_feed)
        await db.EffectiveOptions.set('default_interval', 10)
        r = await self.client.post('/api/restore', headers={**self.headers, 'X-Confirm-Restore': 'merge'}, data=raw)
        self.assertEqual(r.status, 200, await r.text())
        restored = await db.Sub.get(user_id=1, feed__link=self.feed.link).prefetch_related('feed')
        self.assertNotEqual(restored.feed_id, self.feed.id)
        self.assertEqual(restored.feed.entry_hashes, ['abcd1234'])
        self.assertEqual(db.EffectiveOptions.default_interval, 17)
        self.assertTrue(await db.Feed.filter(link='https://other.example/rss').exists())
        self.assertEqual(await db.Sub.all().count(), 3)
        self.assertTrue(list((Path(env.config_folder_path) / 'web-backups').glob('*.zip')))

    async def test_invalid_backup_does_not_modify(self):
        saved = backup.read_backup(await backup.export_backup())
        saved['subscriptions'][0]['feed_id'] = 999
        r = await self.client.post('/api/restore', headers={**self.headers, 'X-Confirm-Restore': 'merge'}, data=pack(saved))
        self.assertEqual(r.status, 400)
        self.assertEqual(await db.Sub.all().count(), 2)
        with self.assertRaises(ValueError):
            backup.read_backup(b'not a zip')

    async def test_notifier_applies_subscription_filter(self):
        from src.monitor._notifier import Notifier
        self.sub.keyword_filter = {'include': ['开源'], 'exclude': ['广告'], 'mode': 'any', 'scope': 'all'}
        notifier = Notifier(feed=self.feed, subs=[self.sub], entries=[{'title': '开源工具'}, {'title': '开源广告'}])
        notifier._get_post = AsyncMock(return_value=object())
        notifier._do_send = AsyncMock()
        await notifier._notify_sub_with_entry_idx(0, self.sub)
        await notifier._notify_sub_with_entry_idx(1, self.sub)
        self.assertEqual(notifier._do_send.await_count, 1)

    async def test_opml_export_scoped_and_titles(self):
        from lxml import etree
        self.sub.title = '我的标题 & <工具>'
        self.sub.state = 0
        await self.sub.save()
        extra = await db.Feed.create(title='别的源', link='https://other.example/rss')
        await db.Sub.create(user_id=-10042, feed=extra)
        r = await self.client.get('/api/targets/1/opml', headers=self.headers)
        self.assertEqual(r.status, 200, await r.text())
        root = etree.fromstring(await r.read())
        outlines = root.findall('.//outline')
        self.assertEqual(len(outlines), 1)
        self.assertEqual(outlines[0].get('text'), self.sub.title)
        self.assertEqual(outlines[0].get('xmlUrl'), self.feed.link)
        from src.admin.opml import parse_opml
        self.assertEqual(parse_opml(await r.read())[0]['title'], self.sub.title)
        self.assertIn('rsstt-1.opml', r.headers['Content-Disposition'])
        await db.User.create(id=2)
        self.assertEqual((await self.client.get('/api/targets/2/opml', headers=self.headers)).status, 400)
        self.assertEqual((await self.client.get('/api/targets/999/opml', headers=self.headers)).status, 404)
        self.assertEqual((await self.client.get('/api/targets/1/opml')).status, 401)

    async def test_opml_preview_import_preserves_other_targets(self):
        await db.User.create(id=2)
        r = await self.client.get('/api/targets/1/opml', headers=self.headers)
        raw = await r.read()
        r = await self.client.post('/api/targets/2/opml?preview=1', headers=self.headers, data=raw)
        self.assertEqual(r.status, 200, await r.text())
        self.assertEqual((await r.json())['total'], 1)
        self.assertEqual(await db.Sub.filter(user_id=2).count(), 0)
        r = await self.client.post('/api/targets/2/opml', headers=self.headers, data=raw)
        self.assertEqual(r.status, 400)
        r = await self.client.post('/api/targets/2/opml', headers={**self.headers, 'X-Confirm-OPML': 'import'}, data=raw)
        self.assertEqual(r.status, 200, await r.text())
        self.assertEqual((await r.json())['success'], 1)
        imported = await db.Sub.get(user_id=2)
        self.assertEqual(imported.feed_id, self.feed.id)
        await self.other.refresh_from_db()
        self.assertEqual(self.other.keyword_filter['include'], ['独立'])
        r = await self.client.post('/api/targets/2/opml', headers={**self.headers, 'X-Confirm-OPML': 'import'}, data=raw)
        result = await r.json()
        self.assertEqual(result['success'], 0)
        self.assertEqual(result['failed'], 1)
        self.assertEqual(await db.Sub.filter(user_id=2).count(), 1)

    async def test_opml_custom_title_nested_and_limit(self):
        from src.admin.opml import parse_opml
        raw = b'''<?xml version="1.0"?><opml version="2.0"><body><outline text="Folder">
        <outline type="rss" text="Custom &amp; title" title="Original" xmlUrl="https://example.com/rss"/>
        <outline type="rss" text="Duplicate" xmlUrl="https://example.com/rss"/>
        </outline></body></opml>'''
        feeds = parse_opml(raw)
        self.assertEqual(feeds, [{'url': self.feed.link, 'title': 'Custom & title'}])
        await db.User.create(id=2, sub_limit=0)
        r = await self.client.post('/api/targets/2/opml', headers={**self.headers, 'X-Confirm-OPML': 'import'}, data=raw)
        self.assertEqual((await r.json())['success'], 0)
        self.assertFalse(await db.Sub.filter(user_id=2).exists())
        await db.User.filter(id=2).update(sub_limit=1)
        r = await self.client.post('/api/targets/2/opml', headers={**self.headers, 'X-Confirm-OPML': 'import'}, data=raw)
        self.assertEqual((await r.json())['success'], 1)
        self.assertEqual((await db.Sub.get(user_id=2)).title, 'Custom & title')

    async def test_opml_invalid_xml_entities_and_sizes(self):
        from src.admin.opml import parse_opml, MAX_OPML_BYTES
        invalid = [b'<html/>', b'<opml>', b'<opml><body/></opml>',
                   b'<opml><body><outline xmlUrl="file:///etc/passwd"/></body></opml>',
                   b'<!DOCTYPE opml [<!ENTITY x SYSTEM "file:///etc/passwd">]><opml><body>&x;</body></opml>',
                   '<!DOCTYPE opml [<!ENTITY x "text">]><opml><body>&x;</body></opml>'.encode('utf-16'),
                   b'x' * (MAX_OPML_BYTES + 1)]
        for raw in invalid:
            with self.assertRaises(ValueError):
                parse_opml(raw)
        oversized = '<opml><body>' + ''.join(f'<outline xmlUrl="https://example.com/{i}"/>' for i in range(1001)) + '</body></opml>'
        with self.assertRaises(ValueError):
            parse_opml(oversized.encode())
        r = await self.client.post('/api/targets/1/opml?preview=1', headers=self.headers, data=b'bad xml')
        self.assertEqual(r.status, 400)
        r = await self.client.post('/api/targets/1/opml?preview=1', headers=self.headers, data=b'x' * (MAX_OPML_BYTES + 1))
        self.assertEqual(r.status, 400)
        self.assertEqual(await db.Sub.all().count(), 2)

    async def test_transaction_rollback(self):
        saved = backup.read_backup(await backup.export_backup())
        saved['users'][0]['lang'] = 'en'
        with patch.object(db.Sub, 'update_or_create', side_effect=RuntimeError('simulated storage failure')):
            with self.assertRaises(RuntimeError):
                await backup.restore_backup(saved)
        await self.u.refresh_from_db()
        self.assertEqual(self.u.lang, 'zh-Hans')

    async def test_runtime_roundtrip_and_default_settings(self):
        raw = await backup.export_backup(include_runtime=True)
        saved = backup.read_backup(raw)
        self.assertEqual(saved['runtime']['TOKEN'], 'test')
        saved['runtime']['R_PROXY'] = 'socks5://user:${literal}@localhost:1080'
        result = await backup.restore_backup(saved, restore_runtime=True)
        self.assertTrue(result['restart_required'])
        from dotenv import dotenv_values
        runtime = dotenv_values(Path(env.config_folder_path) / 'web-restored.env', interpolate=False)
        self.assertEqual(runtime['R_PROXY'], saved['runtime']['R_PROXY'])
        self.assertNotIn('DATABASE_URL', runtime)
        r = await self.client.patch('/api/targets/-10042', headers=self.headers,
                                    json={'interval': 15, 'notify': 0, 'send_mode': 2})
        self.assertEqual(r.status, 200, await r.text())
        self.assertEqual((await db.User.get(id=-10042)).interval, 15)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]], verbosity=2)

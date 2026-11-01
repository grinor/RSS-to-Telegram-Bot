"""Destination-scoped OPML exchange using the bot's existing subscription helpers."""
import asyncio

import listparser
from bs4 import BeautifulSoup
from lxml import etree

from .. import db
from .validation import url

MAX_OPML_BYTES = 2 * 1024 * 1024
MAX_OPML_FEEDS = 1000


def parse_opml(raw):
    if not raw or len(raw) > MAX_OPML_BYTES:
        raise ValueError('OPML 文件不能为空，且不能超过 2 MB')
    # Validate XML before giving it to the same listparser used by the bot command.
    # Disable external resources and reject DTDs, including UTF-16 encoded input.
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    try:
        root = etree.fromstring(raw, parser=parser)
    except etree.XMLSyntaxError as exc:
        raise ValueError('OPML XML 格式无效') from exc
    if root.getroottree().docinfo.doctype or etree.QName(root).localname.lower() != 'opml':
        raise ValueError('请上传不含 DTD 的 OPML 文件')
    if len(root.xpath('//*[local-name()="outline"][@xmlUrl or @xmlurl]')) > MAX_OPML_FEEDS:
        raise ValueError('每次最多导入 1000 个订阅源')
    # Importing compat applies the upstream text/title_orig preservation patch.
    from .. import compat  # noqa: F401
    parsed = listparser.parse(etree.tostring(root, encoding='utf-8', xml_declaration=True))
    feeds = []
    for feed in parsed.feeds:
        link = url(feed.url)
        title = feed.text if feed.text and feed.text != feed.title_orig else None
        if title and len(title) > 1024:
            raise ValueError('OPML 中的自定义标题过长')
        feeds.append({'url': link, 'title': title})
    if not feeds:
        raise ValueError('OPML 文件中没有有效的订阅源')
    if len(feeds) > MAX_OPML_FEEDS:
        raise ValueError('每次最多导入 1000 个订阅源')
    return feeds


async def preview(user_id, raw):
    await db.User.get(id=user_id)
    feeds = await asyncio.to_thread(parse_opml, raw)
    existing = set(await db.Sub.filter(user_id=user_id).values_list('feed__link', flat=True))
    return {'user_id': user_id, 'total': len(feeds),
            'existing': sum(feed['url'] in existing for feed in feeds), 'feeds': feeds}


async def import_feeds(user_id, raw, lang=None):
    from ..command.inner import sub as inner_sub
    target = await db.User.get(id=user_id)
    feeds = await asyncio.to_thread(parse_opml, raw)
    from ..command.inner.utils import check_sub_limit
    from ..i18n import i18n
    reached, _, _, _ = await check_sub_limit(user_id)
    if reached:
        return {'user_id': user_id, 'total': len(feeds), 'success': 0, 'failed': len(feeds),
                'details': i18n[lang or target.lang]['sub_limit_reached']}
    result = await inner_sub.subs(user_id, tuple(
        (feed['url'], feed['title']) if feed['title'] else feed['url'] for feed in feeds
    ), lang=lang or target.lang)
    return {
        'user_id': user_id, 'total': len(feeds), 'success': result['success_count'],
        'failed': result['failure_count'],
        # Command helpers produce Telegram HTML; expose only text to the browser.
        'details': BeautifulSoup(result['failure_msg'], 'html.parser').get_text('\n', strip=True),
    }


async def export_feeds(user_id):
    from ..command.inner import sub as inner_sub
    await db.User.get(id=user_id)
    content = await inner_sub.export_opml(user_id)
    if content is None:
        raise ValueError('此接收目标暂无订阅可导出')
    return content

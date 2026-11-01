import asyncio, os, sys, tempfile
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
folder = tempfile.TemporaryDirectory()
os.environ.update(TOKEN='test', MANAGER='1', NO_UVLOOP='1', MULTIPROCESSING='0', MPLCONFIGDIR=folder.name)
sys.argv = ['migration-smoke', '-c', folder.name]
from src import db
import aerich.models

async def main():
    await db.init()
    user = await db.User.create(id=1)
    feed = await db.Feed.create(title='before upgrade', link='https://example.com/rss')
    sub = await db.Sub.create(user=user, feed=feed, keyword_filter={'include': ['开源']})
    conn = db.Sub._meta.db
    await conn.execute_script('ALTER TABLE "sub" DROP COLUMN "keyword_filter";')
    await aerich.models.Aerich.filter(version__startswith='5_').delete()
    await db.close()
    await db.init()
    original = await db.Sub.get(id=sub.id)
    assert original.keyword_filter is None
    original.keyword_filter = {'exclude': ['广告']}
    await original.save()
    assert (await db.Sub.get(id=sub.id)).keyword_filter == {'exclude': ['广告']}
    assert (await db.Feed.get(id=feed.id)).title == 'before upgrade'
    await db.close()
    print('Fresh SQLite schema and existing-data upgrade: PASS')

asyncio.run(main())

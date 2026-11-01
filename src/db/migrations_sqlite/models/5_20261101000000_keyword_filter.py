from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return 'ALTER TABLE "sub" ADD "keyword_filter" JSON;'


async def downgrade(db: BaseDBAsyncClient) -> str:
    return 'ALTER TABLE "sub" DROP COLUMN "keyword_filter";'

import asyncio
import asyncpg
import logging
# from .db import proxy_table, location_table
from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import insert

logger = logging.getLogger(__name__)


class ProxyToDB:
    _db: asyncpg.pool.Pool
    table_proxy: Table
    table_location: Table

    def __init__(self, db_connect: asyncpg.pool.Pool, table_proxy: Table,
                 table_location: Table):
        self._db = db_connect
        self.table_proxy = table_proxy
        self.table_location = table_location

    def insert_proxy(self, proxy):
        """Insert proxy
        INSERT INTO {self.table.proxy} ("host", "port", "user_", "password", "data_creation", "protocol", "latency",
         "is_alive", "anonymous", "location") VALUES (...) ON CONFLICT DO NOTHING
        """
        async with self._db.acquire() as conn:
            async with conn.transaction():
                query = insert(self.table_proxy).values(**proxy).on_conflict_do_nothing()
                res = await conn.execute(query)
                return res

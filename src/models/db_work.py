import asyncio
import asyncpg
import logging
from typing import Optional
# from .db import proxy_table, location_table
from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import insert
import sys
from . import Proxy
if sys.version_info < (3, 7)[:2]:
    from asyncio import ensure_future as create_task
else:
    from asyncio import create_task

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

    async def insert_proxy(self, kwargs):
        """Insert proxy
        INSERT INTO {self.table.proxy} ("host", "port", "user_", "password", "data_creation", "protocol", "latency",
         "is_alive", "anonymous", "location") VALUES (...) ON CONFLICT DO NOTHING
        """
        async with self._db.acquire() as conn:
            async with conn.transaction():
                query = insert(self.table_proxy).values(**kwargs).on_conflict_do_nothing()
                res = await conn.execute(query)
                return res


class TaskHandlerToDB:

    incoming_queue: asyncio.Queue
    proxy_to_db: ProxyToDB
    _instance_start: Optional[asyncio.Task]

    def __init__(self, incoming_queue: asyncio.Queue, proxy_to_db: ProxyToDB):
        self.incoming_queue = incoming_queue
        self.proxy_to_db = proxy_to_db

    async def start(self) -> None:
        self._instance_start = create_task(self._start())

    async def _start(self) -> None:
        while True:
            proxy = await self.incoming_queue.get()
            self.incoming_queue.task_done()
            if not isinstance(proxy, Proxy):
                logger.error(f'{proxy} -- not instance Proxy')
                continue
            create_task(self.processing_task(proxy))
            await asyncio.sleep(0)

    async def processing_task(self, proxy: Proxy) -> None:
        """save db"""
        try:
            dict_proxy = proxy.as_dict()
            res = await self.proxy_to_db.insert_proxy(**dict_proxy)
            logger.debug(f'{dict_proxy} ::: {res}')
        except Exception as e:
            logger.error(f'{e} ::: {e.args}')
            logger.exception(e)
            raise

    def is_stoped(self) -> bool:
        if self._instance_start:
            return self._instance_start.cancelled()
        else:
            return True

    def stop(self) -> None:
        self._instance_start.cancel()



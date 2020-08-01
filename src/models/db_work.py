import asyncio
import asyncpg
import logging
import datetime
from typing import Optional
# from .db import proxy_table, location_table
from sqlalchemy import Table, select, update, and_, or_, delete, null
from sqlalchemy.dialects.postgresql import insert
import sys
from . import Proxy, proxy_table, Location
if sys.version_info < (3, 7)[:2]:
    from asyncio import ensure_future as create_task
else:
    from asyncio import create_task

logger = logging.getLogger(__name__)

__all__ = ("TaskHandlerToDB", 'ProxyDb', 'LocationDb', )


class LocationDb:
    _db: asyncpg.pool.Pool
    table_location: Table

    def __init__(self, db_connect: asyncpg.pool.Pool, table_location: Table):
        self.table_location = table_location
        self._db = db_connect

    async def insert_location(self, **kwargs):
        async with self._db.acquire() as conn:
            query = insert(self.table_location).values(**kwargs).on_conflict_do_nothing()
            res = await conn.execute(query)
            return res

    async def select_pm(self, ip: str):
        async with self._db.acquire() as conn:
            query = select([self.table_location]).where(self.table_location.c.ip == ip)
            res = await conn.fetchrow(query)
            return res

    async def delete_for_ip(self, ip: str):
        async with self._db.acquire() as conn:
            query = delete(self.table_location).where(self.table_location.c.ip == ip)
            res = await conn.execute(query)
            return res


class ProxyDb:
    _db: asyncpg.pool.Pool
    table_proxy: Table
    delta_minutes: int = 60

    def __init__(self, db_connect: asyncpg.pool.Pool, table_proxy: Table):
        self._db = db_connect
        self.table_proxy = table_proxy

    async def insert_proxy(self, **kwargs):
        """Insert proxy
        INSERT INTO {self.table.proxy} ("host", "port", "login", "password", "data_creation", "protocol", "latency",
         "is_alive", "anonymous", "location") VALUES (...) ON CONFLICT DO NOTHING
        """
        async with self._db.acquire() as conn:
            query = insert(self.table_proxy).values(**kwargs).on_conflict_do_nothing()
            res = await conn.execute(query)
            return res

    async def select_proxy_pm(self, host: str, port: int):
        """select proxy
        SELECT * FROM {self.table_proxy} WHERE (host = $1 and port =$2);
        """
        async with self._db.acquire() as conn:
            async with conn.transaction():
                query = select([self.table_proxy]).where(and_(
                    self.table_proxy.c.host == host,
                    self.table_proxy.c.port == port
                ))
                res = await conn.fetchrow(query)
        return res

    async def delete_proxy_pm(self, host: str, port: int):
        async with self._db.acquire() as conn:
            query = delete(self.table_proxy).where(and_(
                self.table_proxy.c.host == host,
                self.table_proxy.c.port == port
            ))
            res = await conn.execute(query)
        return res

    async def update_proxy_pm(self, **kwargs):
        async with self._db.acquire() as conn:
            query = update(self.table_proxy).where(and_(
                self.table_proxy.c.host == kwargs['host'],
                self.table_proxy.c.port == kwargs['port']
            )).values(**kwargs)
            res = await conn.execute(query)
        return res

    async def select_and_set_proxy_to_process(self):
        """
        BEGIN;
        (SELECT * FROM proxy WHERE proxy.date_update IS NULL AND proxy.in_process = false) as q1
        IF NOT EXIST q1 (SELECT * FROM proxy WHERE proxy.date_update < :date_update_1 AND proxy.in_process = false) as q2
        IF EXIST q1 OR q2(
        UPDATE proxy SET in_process=:in_process WHERE proxy.host = :host_1 AND proxy.port = :port_1);
        COMMIT;
        :return:
        """
        async with self._db.acquire() as conn:
            async with conn.transaction():
                query = select([self.table_proxy]).where(
                    and_(self.table_proxy.c.date_update == None, self.table_proxy.c.in_process == False)) # noqa
                res = await conn.fetchrow(query)
                if not res:
                    query = select([self.table_proxy]).where(
                        and_(
                            self.table_proxy.c.date_update < datetime.datetime.utcnow() - datetime.timedelta(
                                minutes=self.delta_minutes),
                            self.table_proxy.c.in_process == False)) # noqa
                    res = await conn.fetchrow(query)
                if res:
                    query_update = update(self.table_proxy).where(
                        and_(
                            self.table_proxy.c.host == res['host'],
                            self.table_proxy.c.port == res['port']
                        )
                    ).values({"in_process": True})
                    update_result = await conn.execute(query_update)
                    return res
        return res


class TaskHandlerToDB:

    incoming_queue: asyncio.Queue
    proxy_db: ProxyDb
    _instance_start: Optional[asyncio.Task]

    def __init__(self, incoming_queue: asyncio.Queue, proxy_db: ProxyDb):
        self.incoming_queue = incoming_queue
        self.proxy_db = proxy_db

    async def start(self) -> None:
        self._instance_start = create_task(self._start())

    async def _start(self) -> None:
        """get proxy from queue and processing"""
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
            res = await self.proxy_db.insert_proxy(**dict_proxy)
            logger.debug(f'{dict_proxy} ::: {res}')
        except Exception as e:
            logger.error(f'{e} ::: {e.args}')
            logger.exception(e)
            raise

    def is_running(self) -> bool:
        if self._instance_start:
            return bool(not self._instance_start.cancelled())
        else:
            return True

    def stop(self) -> None:
        self._instance_start.cancel()


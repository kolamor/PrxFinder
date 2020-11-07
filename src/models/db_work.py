import asyncio
import asyncpg
import asyncpgsa
import logging
import datetime
from typing import Optional
# from .checker import BaseTaskHandler
from .db import proxy_table, location_table
from sqlalchemy import Table, select, update, and_, or_, delete, exists, text, asc
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.dialects import postgresql

import sys
from . import Proxy
if sys.version_info < (3, 7)[:2]:
    from asyncio import ensure_future as create_task
else:
    from asyncio import create_task

logger = logging.getLogger(__name__)

__all__ = ("TaskHandlerToDB", 'ProxyDb', 'LocationDb', 'StartProxyHandler', 'DbConnectPool')


class NoSetDbConnect(Exception):
    pass


class DbConnectPool:
    """Descriptor db connect"""
    _dsn: str
    _db_connect_kwargs: dict
    pool: asyncpg.pool.Pool

    @classmethod
    async def create_connect(cls, dsn: str, db_connect_kwargs: dict) -> None:
        cls._dsn = dsn
        cls._db_connect_kwargs = db_connect_kwargs
        cls.pool = await asyncpgsa.create_pool(dsn=dsn, **db_connect_kwargs)

    @classmethod
    def set_connect(cls, pool: asyncpg.pool.Pool) -> None:
        cls.pool = pool

    def __get__(self, instance, owner) -> asyncpg.pool.Pool:
        conn = self.__class__.pool
        if not conn:
            raise NoSetDbConnect(f'{self.__class__} don\'t set db connect')
        return conn


class LocationDb:
    _db: asyncpg.pool.Pool = DbConnectPool()
    table_location: Table = location_table

    def __init__(self, table_location: Optional[Table] = None):
        if table_location is not None:
            self.table_location = table_location

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

    async def exist_ip(self, ip: str) -> bool:
        async with self._db.acquire() as conn:

            # query = exists(select([self.table_location.c.ip]).where(self.table_location.c.ip == ip))

            query = text(f'''SELECT exists (SELECT {self.table_location.c.ip}
                                FROM {self.table_location}
                                WHERE {self.table_location.c.ip} = $1) as "exists";''')
            res = await conn.fetchrow(query, ip)
            return res['exists']


class ProxyDb:
    _db: asyncpg.pool.Pool = DbConnectPool()
    table_proxy: Table = location_table
    delta_minutes_for_check: int

    def __init__(self, table_proxy: Optional[Table] = None,
                 delta_minutes_for_check: int = 60):
        if table_proxy is not None:
            self.table_proxy = table_proxy
        self.delta_minutes_for_check = delta_minutes_for_check

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
        host = kwargs.pop('host')
        port = kwargs.pop('port')
        async with self._db.acquire() as conn:
            query = update(self.table_proxy).where(and_(
                self.table_proxy.c.host == host,
                self.table_proxy.c.port == port
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
                                minutes=self.delta_minutes_for_check),
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

    # async def get_good_proxy(self, limit: int = 10, schema: str = None):
    #     """select * from proxy where is_alive = true order by  latency asc;"""
    #
    #     async with self._db.acquire() as conn:
    #         query = select([self.table_proxy]).where(self.table_proxy.c.is_alive == True) # noqa
    #         if schema:
    #             query = query.where(self.table_proxy.c.schema == schema)
    #         query = query.order_by(asc(self.table_proxy.c.latency)).limit(limit)
    #         res = await conn.fetch(query)
    #     return res


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
            if dict_proxy.get('in_process', False):
                proxy.in_process = False
                dict_proxy.update({"in_process": False})
                res = await self.proxy_db.update_proxy_pm(**dict_proxy)
                logger.debug(f'{dict_proxy} ::: {res}')
            else:
                # db auto set date_creation
                dict_proxy.pop('date_creation')
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


class StartProxyHandler(TaskHandlerToDB):
    proxy_db: ProxyDb
    outgoing_queue: asyncio.Queue
    max_tasks_semaphore: asyncio.Semaphore
    works = asyncio.Event()

    def __init__(self, outgoing_queue: asyncio.Queue, proxy_db: ProxyDb, max_tasks: int = 20):
        self.proxy_db = proxy_db
        self.outgoing_queue = outgoing_queue
        self.max_tasks_semaphore = asyncio.Semaphore(max_tasks)

    def pause(self):
        self.works.clear()

    async def _start(self) -> None:
        logger.info(f'{self.__class__.__name__} starting')
        self.works.set()
        while True:
            try:
                await self.works.wait()
                proxy = await self.get_proxy()
                if not proxy:
                    await asyncio.sleep(1)
                    continue
                print(proxy)
                proxy.in_process = True
            except Exception as e:
                logger.error(f"{self.__class__.__name__} {e}, {e.args}")
                logger.exception(e)
                continue
            try:
                await self.put_proxy_to_queue(proxy)
            except Exception as e:
                logger.error(f"{self.__class__.__name__} {e}, {e.args}")
                logger.exception(e)
            await asyncio.sleep(0)

    async def put_proxy_to_queue(self, proxy: Proxy) -> None:
        await self.outgoing_queue.put(proxy)

    async def get_proxy(self) -> Optional[Proxy]:
        row = await self.proxy_db.select_and_set_proxy_to_process()
        if not row:
            return
        proxy = Proxy(**{k: v for k, v in row.items()})
        return proxy



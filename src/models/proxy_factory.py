from .db_work import DbConnectPool
import asyncpg
import abc
from .client import Proxy, Location
from .db_work import DbConnectPool
from .db import proxy_table, location_table
from sqlalchemy import Table, select, update, and_, or_, delete, exists, text, asc
from typing import List, Union
from random import choice


class ProxyFactoryABC:

    def __init__(self):
        pass

    @abc.abstractmethod
    async def get_random_alive_proxy(self, scheme: str = None, last_uptime_sec: int = None) -> Proxy:
        """it give proxy from delta(now and last uptime)"""
        pass

    @abc.abstractmethod
    async def get_random_alive_proxy_from_location(self, location: Location, scheme: str = None,
                                                   last_uptime_sec: int = None) -> Proxy:
        pass


class RandomAliveProxies:
    table_proxy = proxy_table
    _db = DbConnectPool()

    async def get(self, scheme: str = None, last_uptime_sec: int = None, limit: int = 1):
        """select * from proxy where is_alive = true order by  latency asc;"""
        async with self._db.acquire() as conn:
            query = select([self.table_proxy]).where(self.table_proxy.c.is_alive == True)  # noqa
            if scheme:
                query = query.where(self.table_proxy.c.schema == scheme)
            query = query.order_by(asc(self.table_proxy.c.latency)).limit(limit)
            res = await conn.fetch(query)
        return res


class ProxyFactoryDb(ProxyFactoryABC):

    async def get_random_alive_proxy(self, scheme: str = None, last_uptime_sec: int = None,
                                     limit: int = 100) -> Union[List[Proxy], Proxy]:
        obj = RandomAliveProxies()
        proxies_db = await obj.get(scheme=scheme, last_uptime_sec=last_uptime_sec, limit=limit)
        proxies = []
        for record in proxies_db:
            record_dict = {k: v for k, v in record.items()}
            proxy = Proxy(**record_dict)
            proxies.append(proxy)
        if proxies:
            return choice(proxies)
        return proxies

    async def get_random_alive_proxy_from_location(self, location: Location, scheme: str = None,
                                                   last_uptime_sec: int = 60*60) -> Proxy:
        raise NotImplemented


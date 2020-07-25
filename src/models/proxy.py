import asyncio
import datetime
import logging
try:
    from urllib2 import _parse_proxy
except ImportError:
    from urllib.request import _parse_proxy
from typing import Optional

logger = logging.getLogger(__name__)

__all__ = ('Location', 'Proxy', 'ProxyChecker')


class Location:
    pass


class Proxy:
    """

    """
    def __init__(self,
                 host: str,
                 port: str,
                 user: Optional[str],
                 password: Optional[str],
                 location: Optional[Location] = None,
                 schema: str = 'http',
                 is_alive: Optional[bool] = None,
                 latency: Optional[int] = None,
                 checked_at: Optional[datetime.datetime] = None
                 ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.location = location
        self.schema = schema
        self.is_alive = is_alive
        self.latency = latency
        self.checked_at = checked_at

    def _create_uri(self):
        host_port = f'{self.host}:{self.port}'
        if self.user and self.password:
            uri = f'{self.schema}://{self.user}:{self.password}@{host_port}'
        else:
            uri = f'{self.schema}://{host_port}'
        return uri

    @classmethod
    def create_from_url(cls, url: str) -> 'Proxy':
        proxy_type, user, password, hostport = _parse_proxy(url)
        if ':' in hostport:
            host, port = hostport.split(':')
            kw = {'host': host, "port": port}
        else:
            kw = {'host': hostport}
        self = cls(schema=proxy_type, user=user, password=password, **kw)
        return self

    @property
    def url(self):
        return self._create_uri()

    def __str__(self):
        return self._create_uri()


class ProxyChecker:
    """Check proxy"""
    def __init__(self, proxy):
        self._proxy = proxy

    @classmethod
    async def check(cls, proxy: Proxy) -> 'ProxyChecker':
        self = cls(proxy=proxy)
        return self

    async def __check(self):
        pass

import asyncio
import datetime
import logging
try:
    from urllib2 import _parse_proxy
except ImportError:
    from urllib.request import _parse_proxy
from typing import Optional, Union
from .client import ProxyClient

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

    def as_dict(self):
        keys = ('host', 'port', 'user', 'password', 'latency', 'is_alive', 'sheme', )
        context = {k: v for k, v in self.__dict__ .items() if k in keys}
        return context

    def __repr__(self):
        return self.as_dict()

    def __str__(self):
        return self._create_uri()


class ProxyChecker:
    """Check proxy"""

    def __init__(self, proxy: Proxy):
        self.proxy = proxy
        self.proxy_policy = CheckProxyPolicy()

    @classmethod
    async def check(cls, proxy: Proxy) -> 'Proxy':
        self = cls(proxy=proxy)
        proxy = await self.check_proxy()
        return proxy

    async def check_proxy(self) -> Proxy:
        answer = None
        async with ProxyClient(proxy=self.proxy) as sess:
            try:
                answer = await sess.get()
            except Exception as e:
                logger.info(f'{Proxy} -- {e}, -- {e.args}')
        if not answer:
            self.proxy.is_alive = False
            return self.proxy
        is_valid = self.check_policy(answer)
        if is_valid:
            self.rebuild_proxy(answer=answer)
        else:
            self.proxy.is_alive = False
        return self.proxy

    def rebuild_proxy(self, answer: dict) -> None:
        self.proxy.latency = float(round(answer['latency'], 2))
        status = answer.get('status_response', False)
        if status and int(status) < 400:
            self.proxy.is_alive = True
        else:
            self.proxy.is_alive = False

    def check_policy(self, data: dict) -> bool:
        return self.proxy_policy.is_valid(data=data)


class CheckProxyPolicy:
    status_response = 200

    def is_valid(self, data: Union[dict, str, None]) -> bool:
        if data and data['status_response'] == self.status_response:
            return True
        return False


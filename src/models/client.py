import aiohttp
import asyncio
from aiohttp_proxy import ProxyConnector, ProxyType

import datetime
from types import TracebackType
from typing import Optional, Type, Union, Any
# from .proxy import Proxy
import logging
import time
import weakref
try:
    from urllib2 import _parse_proxy
except ImportError:
    from urllib.request import _parse_proxy

logger = logging.getLogger(__name__)

__all__ = ('ProxyClient', 'Proxy', 'Location', "ReferenceProxy", "ReferenceLocation", )


def latency(coro):
    """wrapper -  approximately time read response, adds latency to returned dict"""
    async def wrapped(*args, **kwargs):
        t1 = time.time()
        result = await coro(*args, **kwargs)
        _latency = time.time() - t1
        result.update({'latency': _latency})
        return result
    return wrapped


def retry(coro):
    """wrapper -  retry"""
    async def wrapped(*args, **kwargs):
        nretry = 3
        result = {}
        for n in range(nretry):
            try:
                result = await coro(*args, **kwargs)
            except (aiohttp.ClientProxyConnectionError, aiohttp.ServerConnectionError, aiohttp.ServerDisconnectedError,
                    aiohttp.ServerTimeoutError) as e:
                logger.info(f'retry {args}, {kwargs} ::: -> {e}, {e.args}')
                if n >= nretry - 1:
                    raise
            return result
    return wrapped


class ProxyClient:
    """Support http(s), socks(4,5) proxy
     Use
     proxy = Proxy.create_from_url(proxy)
     async with ProxyClient(proxy=proxy) as sess:
         answ = await sess.get()
     assert answ['status_response'] == 200

     answ: Type[Dict] = {
        'url': type[str],
        'status_response': Type[str],
        'headers': Type[CIMultiDictProxy],
        'content: Type[byte],
     }
     """
    test_url: str = 'http://httpbin.org/status/200'
    return_content: bool = False

    def __init__(self, proxy: 'Proxy', test_url: str = None):
        self.proxy = proxy
        if test_url:
            self.test_url = test_url

    @classmethod
    async def create(cls, proxy: 'Proxy', test_url: str = None) -> 'ProxyClient':
        self = cls(proxy=proxy, test_url=test_url)
        await self._create_connector()
        return self

    async def _create_connector(self) -> None:
        connector = ProxyConnector.from_url(self.proxy.url)
        self._session = aiohttp.ClientSession(connector=connector)

    async def __aenter__(self, *args, **kwargs) -> 'ProxyClient':
        await self._create_connector()
        return self

    @retry
    @latency
    async def get(self, url: Optional[str] = None, timeout: int = 180) -> dict:
        """ get request from url or self.test_url,
        context =  {'url': type[str],
                    'status_response': Type[str],
                    'headers': Type[CIMultiDictProxy],
                    'content: Type[byte],
                }
        :param timeout: int:
        :param url: str
        :return: context: dict
        """
        if not url:
            url = self.test_url
        async with self._session.get(url=url, timeout=timeout) as response:
            context = {
                'url': url,
                'status_response': response.status,
                'headers': response.headers,
            }
            if self.return_content:
                content = await response.read()
                context.update({'content': content})
        return context

    async def close(self) -> None:
        await self._session.close()

    @property
    def closed(self) -> bool:
        return self._session.closed

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException],
                        exc_tb: Optional[TracebackType]) -> None:
        await self.close()


class ReferenceLocation:

    @classmethod
    def get(cls):
        cls.__create_weak_set()
        return cls._references

    @classmethod
    def add(cls, ref_obj: Any):
        cls.__create_weak_set()
        cls._references.add(ref_obj)

    @classmethod
    def __create_weak_set(cls):
        if not getattr(cls, '_references', None):
            cls._references = weakref.WeakSet()


class ReferenceProxy(ReferenceLocation):
    pass


class Location:
    keys: tuple = ('ip', 'country_code', 'country_name', 'region_code', 'region_name', 'city', 'zip_code', 'time_zone',
                   'latitude', 'longitude', 'metro_code',)

    def __init__(self,
                 ip: str,
                 country_code: Optional[str] = None,
                 country_name: Optional[str] = None,
                 region_code: Optional[str] = None,
                 region_name: Optional[str] = None,
                 city: Optional[str] = None,
                 zip_code: Union[str] = None,
                 time_zone: Optional[str] = None,
                 latitude: Optional[float] = None,
                 longitude: Optional[float] = None,
                 metro_code: Optional[int] = None
                 ):
        self.ip = ip
        self.country_code = country_code
        self.country_name = country_name
        self.region_code = region_code
        self.region_name = region_name
        self.city = city
        self.zip_code = zip_code
        self.time_zone = time_zone
        self.latitude = latitude
        self.longitude = longitude
        self.metro_code = metro_code

        ReferenceLocation.add(self)

    def as_dict(self, ignore_none: bool = False):
        """return attrs as dict from keys, ignore_none - delete items with None value """
        if ignore_none:
            context = {k: v for k, v in self.__dict__.items() if k in self.keys and v is not None}
        else:
            context = {k: v for k, v in self.__dict__.items() if k in self.keys}
        return context

    def __repr__(self):
        return str(self.as_dict())


class Proxy:
    """

    """
    def __init__(self,
                 host: str,
                 port: int,
                 login: Optional[str],
                 password: Optional[str],
                 location: Optional[Location] = None,
                 scheme: str = 'http',
                 is_alive: Optional[bool] = None,
                 latency: Optional[float] = None,
                 date_update: Optional[datetime.datetime] = None,
                 date_creation: Optional[datetime.datetime] = None,
                 anonymous: Optional[bool] = None,
                 in_process: Optional[bool] = None
                 ):
        self.host = host
        self.port = int(port)
        self.login = login
        self.password = password
        self.location = location
        self.scheme = scheme
        self.is_alive = is_alive
        self.latency = latency
        self.date_update = date_update
        self.date_creation = date_creation
        self.anonymous = anonymous
        self.in_process = in_process

        ReferenceProxy.add(self)

    def _create_uri(self) -> str:
        host_port = f'{self.host}:{self.port}'
        if self.login and self.password:
            uri = f'{self.scheme}://{self.login}:{self.password}@{host_port}'
        else:
            uri = f'{self.scheme}://{host_port}'
        return uri

    @classmethod
    def create_from_url(cls, url: str) -> 'Proxy':
        proxy_type, login, password, hostport = _parse_proxy(url)
        if ':' in hostport:
            host, port = hostport.split(':')
            kw = {'host': host, "port": port}
        else:
            kw = {'host': hostport}
        self = cls(scheme=proxy_type, login=login, password=password, **kw)
        return self

    @property
    def url(self) -> str:
        return self._create_uri()

    def as_dict(self) -> dict:
        keys = ('host', 'port', 'login', 'password', 'latency', 'is_alive', 'scheme', 'date_update', 'date_creation',
                'anonymous', 'in_process', )
        context = {k: v for k, v in self.__dict__ .items() if k in keys}
        return context

    def __repr__(self):
        return str(self.as_dict())

    def __str__(self):
        return self._create_uri()

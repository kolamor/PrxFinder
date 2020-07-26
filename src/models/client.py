import aiohttp
import asyncio
from aiohttp_proxy import ProxyConnector, ProxyType

from types import TracebackType
from typing import Optional, Type
# from .proxy import Proxy
import logging
import time

logger = logging.getLogger(__name__)

__all__ = ('ProxyClient', )


def latency(coro):
    """wrapper -  approximately time read response, adds latency to returned dict"""
    async def wrapped(*args, **kwargs):
        t1 = time.time()
        result = await coro(*args, **kwargs)
        latency = time.time() - t1
        result.update({'latency': latency})
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

    async def close(self) -> None:
        await self._session.close()

    @latency
    async def get(self, url: Optional[str] = None) -> dict:
        """ get request from url or self.test_url,
        context =  {'url': type[str],
                    'status_response': Type[str],
                    'headers': Type[CIMultiDictProxy],
                    'content: Type[byte],
                }
        :param url: str
        :return: context: dict
        """
        if not url:
            url = self.test_url
        async with self._session.get(url=url) as response:
            context = {
                'url': url,
                'status_response': response.status,
                'headers': response.headers,
            }
            if self.return_content:
                content = await response.read()
                context.update({'content': content})
        return context

    @property
    def closed(self) -> bool:
        return self._session.closed

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException],
                        exc_tb: Optional[TracebackType]) -> None:
        await self.close()



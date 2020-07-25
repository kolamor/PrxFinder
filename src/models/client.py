import aiohttp
import asyncio
from aiohttp_proxy import ProxyConnector, ProxyType

from  types import TracebackType
from typing import Optional, Type
import logging
from .proxy import Proxy
from multidict import CIMultiDictProxy

logger = logging.getLogger(__name__)

__all__ = ('ProxyClient', )


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
    test_url = 'http://httpbin.org/status/200'

    def __init__(self, proxy: Proxy, test_url: str = None):
        self.proxy = proxy
        if test_url:
            self.test_url = test_url

    @classmethod
    async def create(cls, proxy: Proxy, test_url: str = None) -> 'ProxyClient':
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
            content = await response.read()
            context = {
                'url': url,
                'status_response': response.status,
                'headers': response.headers,
                'content': content
            }
        return context

    @property
    def closed(self) -> bool:
        return self._session.closed

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException],
                        exc_tb: Optional[TracebackType]) -> None:
        await self.close()



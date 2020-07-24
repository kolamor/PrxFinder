import aiohttp
import asyncio
from aiohttp_proxy import ProxyConnector, ProxyType

from  types import TracebackType
from typing import Optional, Type
import logging
from .proxy import Proxy

logger = logging.getLogger(__name__)

__all__ = ('ProxyClient', )


class ProxyClient:
    test_url = 'httpbin.org/status/200'

    def __init__(self, proxy: Proxy, test_url: str = None):
        self.proxy = proxy
        if test_url:
            self.test_url = test_url

    @classmethod
    async def create(cls, proxy: Proxy, test_url: str = None) -> 'ProxyClient':
        self = cls(proxy=proxy, test_url=test_url)
        await self._create_connector()
        return self

    async def _create_connector(self):
        connector = ProxyConnector.from_url(self.proxy.url)
        self._session = aiohttp.ClientSession(connector=connector)

    async def __aenter__(self, *args, **kwargs) -> 'ProxyClient':
        await self._create_connector()
        return self

    async def close(self) -> None:
        await self._session.close()

    @property
    def closed(self) -> bool:
        return self._session.closed

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException],
                        exc_tb: Optional[TracebackType]) -> None:
        await self.close()


import aiohttp
import asyncio
from aiohttp_proxy import ProxyConnector, ProxyType

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
        connector = ProxyConnector.from_url(Proxy.url)
        self._session = aiohttp.ClientSession(connector=connector)

    async def __aenter__(self, proxy: Proxy, test_url: str = None):
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._session.close()


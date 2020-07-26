import asyncio
import datetime
import logging
from typing import Optional, Union
from .client import ProxyClient, Proxy

logger = logging.getLogger(__name__)

__all__ = ('ProxyChecker', )


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


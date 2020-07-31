import asyncio
import logging
import sys
from typing import Optional, Union
from .client import ProxyClient, Proxy
from abc import ABC, abstractmethod

if sys.version_info < (3, 7)[:2]:
    from asyncio import ensure_future as create_task
else:
    from asyncio import create_task

logger = logging.getLogger(__name__)

__all__ = ('ProxyChecker', 'TaskProxyCheckHandler', 'CheckProxyPolicy', 'BaseTaskHandler')


class BaseTaskHandler(ABC):
    _instance_start: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self._instance_start = create_task(self._start())

    def is_running(self) -> bool:
        if self._instance_start:
            return not self._instance_start.cancelled()
        else:
            return True

    def stop(self) -> None:
        self._instance_start.cancel()

    @abstractmethod
    async def _start(self) -> None:
        pass




class ProxyChecker:
    """Check proxy"""

    def __init__(self, proxy: Proxy):
        self.proxy = proxy
        self.proxy_policy = CheckProxyPolicy()

    @classmethod
    async def check(cls, proxy: Proxy) -> 'Proxy':
        """shortcut"""
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
        self.proxy.is_alive = True

    def check_policy(self, data: dict) -> bool:
        return self.proxy_policy.is_valid(data=data)


class CheckProxyPolicy:
    status_response = 200

    def is_valid(self, data: Union[dict, str, None]) -> bool:
        if data and data['status_response'] == self.status_response:
            return True
        return False


class TaskProxyCheckHandler(BaseTaskHandler):
    incoming_queue: asyncio.Queue
    outgoing_queue: asyncio.Queue
    max_tasks_semaphore: asyncio.Semaphore
    _instance_start: Optional[asyncio.Task]

    def __init__(self, incoming_queue: asyncio.Queue, outgoing_queue: asyncio.Queue, max_tasks: int = 20):
        self.incoming_queue = incoming_queue
        self.outgoing_queue = outgoing_queue
        self.max_tasks_semaphore = asyncio.Semaphore(max_tasks)

    async def _start(self) -> None:
        print(f'{self.__class__} starting')
        while True:
            await self.max_tasks_semaphore.acquire()
            proxy = await self.incoming_queue.get()
            self.incoming_queue.task_done()
            if not isinstance(proxy, Proxy):
                logger.error(f'{proxy} -- not instance Proxy')
                self.max_tasks_semaphore.release()
                continue
            create_task(self.processing_task(proxy))
            await asyncio.sleep(0)

    async def processing_task(self, proxy: Proxy) -> None:
        """Check proxy and put to queue"""
        try:
            checked_proxy = await ProxyChecker.check(proxy=proxy)
            await self.put_proxy_to_queue(checked_proxy)
        except Exception as e:
            logger.error(f'{proxy} ::: {proxy}, {e} ::: {e.args}')
            logger.exception(e)
        finally:
            self.max_tasks_semaphore.release()

    async def put_proxy_to_queue(self, proxy: Proxy) -> None:
        await self.outgoing_queue.put(proxy)


class ProxyLocation(BaseTaskHandler):
    """

    template_api_response: dict = {
        "ip":"145.150.154.25",
        "country_code":"RU",
        "country_name":"Россия",
        "region_code":"MOS",
        "region_name":"МО",
        "city":"Пушкино",
        "zip_code":"141207",
        "time_zone":"Europe/Moscow",
        "latitude":56.0172,
        "longitude":37.8667,
        "metro_code":0}
    """
    template_api_response: dict
    url_api_location: str = 'https://freegeoip.app/json/'
    db_location = None
    # http_session:

    async def _start(self) -> None:
        print('Start check location')

    async def processing_task(self, proxy: Proxy):
        pass

    async def get_api(self, proxy: Proxy) -> dict:
        pass


import re
import logging
from typing import Optional, Union
from aiohttp import ClientSession

logger = logging.getLogger(__name__)

__all__ = ('request_get', 'DefaultParse')


async def request_get(session: ClientSession, url: str, proxy: Optional[str] = None) -> Union[str, None]:
    async with session.get(url=url, proxy=proxy) as response:
        if response.status == 200:
            text = await response.text()
        else:
            text = None
        return text


class DefaultParse:

    def __init__(self, session: ClientSession, proxy: Optional[str]):
        self._session = session
        self._proxy = proxy

    async def get_page(self, url: str) -> Union[str, None]:
        try:
            text = await request_get(session=self._session, url=url, proxy=self._proxy)
        except Exception as e:
            logger.error(f'--- get {url} - {e}, {e.args}')
            logger.exception(e)
            text = None
        return text

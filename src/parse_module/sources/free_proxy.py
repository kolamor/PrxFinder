import asyncio
import pathlib
from typing import List
import aiohttp
import sys
from lxml import etree
from io import StringIO
# from .utils import HEADERS
from src.parse_module.utils import IPPattern, IPPortPatternLine
from src.models.client import Proxy
import zipfile
import re
if sys.version_info < (3, 7)[:2]:
    from asyncio import ensure_future as create_task
else:
    from asyncio import create_task

__all__ = ('Sslproxies24_top', )

HEADERS = {
    # 'Host': 'workupload.com',
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:79.0) Gecko/20100101 Firefox/79.0',
    'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate, br'
}

# IPPattern = re.compile(
#     r'(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)'
# )

# IPPortPatternLine = re.compile(
#     r'^.*?(?P<ip>(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)).*?(?P<port>\d{2,5}).*$',  # noqa
#     flags=re.MULTILINE,
# )


class Sslproxies24_top:

    base_url = 'http://www.sslproxies24.top/'
    _client_session: aiohttp.ClientSession
    _http_proxy: str
    headers: dict = HEADERS
    tokens = {}
    out_queue: asyncio.Queue

    def __init__(self, client_session: aiohttp.ClientSession, url: str = None, http_proxy: str = None,
                 out_queue: asyncio.Queue = None):
        if url:
            self.base_url = url
        self._client_session = client_session
        self._http_proxy = http_proxy
        self.out_queue = out_queue

    async def _get_content(self, url: str = None, returned_body: str = 'text') -> str:
        url = url if url else self.base_url
        t = self.tokens.get(url.split('/')[-1])
        context = {
            'url': url,
            'proxy': self._http_proxy,
            'headers': self.headers
        }
        if t:
            context.update({'cookies': {'token': t}})
        async with self._client_session.get(**context) as resp:
            text = await getattr(resp, returned_body)()
            # print('--', resp.cookies.get('token'))
            if resp.cookies.get('token'):
                token = resp.cookies.get('token').value
                self.tokens.update({url.split('/')[-1]: token})

        return text

    async def parse(self):
        start_html = await self._get_content()
        text = StringIO(start_html)
        htmlparser = etree.HTMLParser()
        tree = etree.parse(text, htmlparser)
        hrefs = tree.xpath('//h3//a/@href')
        tasks = []
        for url in hrefs:
            task = create_task(self._get_content(url=url))
            tasks.append(task)
        list_html = await asyncio.gather(*tasks)

        hrefs = []
        for html in list_html:
            text = StringIO(html)
            htmlparser = etree.HTMLParser()
            tree = etree.parse(text, htmlparser)
            hrefs.extend(tree.xpath("//div[contains(@id, 'post-body')]/a/@href"))


        for href in hrefs:
            print(href)
            task = create_task(self._get_content(url=href, returned_body='text'))
            tasks.append(task)
        answers = await asyncio.gather(*tasks)

        for href in hrefs:
            href = href.replace('/file/', '/start/')
            task = create_task(self._get_content(url=href, returned_body='text'))
            tasks.append(task)
        answers = await asyncio.gather(*tasks)

        # https://workupload.com/api/file/getDownloadServer/3JmLAyaL39w
        tasks = []
        for href in hrefs:
            print(href)
            if 'workupload.com' in href:
                href = 'https://workupload.com/api/file/getDownloadServer/' + href.split('/')[-1]
            # print(href)
            task = create_task(self._get_content(url=href, returned_body='json'))
            tasks.append(task)
        answers = await asyncio.gather(*tasks)
        tasks = []
        for row in answers:
            url = row['data']['url']
            tasks.append(create_task(self._get_content(url=url, returned_body='read')))
        answers = await asyncio.gather(*tasks)
        n = 1
        self.create_tmp_dir()
        for zipf in answers:
            path = f'tmp/archive{str(n)}.zip'
            with open(path, 'wb') as f:
                f.write(zipf)
            path_extract = path.split('.', 1)[0]
            self.create_tmp_dir(path_extract)
            n += 1
            path_extract_dir = self.unzip(path)
            path_extract_dir = pathlib.Path(path_extract_dir)
            for child in path_extract_dir.iterdir():
                if child.suffix == '.txt':
                    with open(child) as f:
                        text = f.read()
                    proxies = self.create_proxies(text=text)
                    for prx in proxies:
                        print(prx)
                        await self.put_out_queue(prx)

    async def put_out_queue(self, proxy: Proxy):
        await self.out_queue.put(proxy)

    def create_proxies(self, text: str) -> List[Proxy]:
        ips = IPPortPatternLine.findall(text)
        proxies = [Proxy.create_from_url(f'http://{prx[0]}:{prx[1]}') for prx in ips]
        return proxies

    def create_tmp_dir(self, tmp_dir: str = 'tmp'):
        path = pathlib.Path(tmp_dir)
        if not(path.exists() and path.is_dir()):
            path.mkdir(parents=True, exist_ok=True)

    def unzip(self, path_to_zip_file: str):
        if zipfile.is_zipfile(path_to_zip_file):
            with zipfile.ZipFile(path_to_zip_file, 'r') as zip_ref:
                zip_ref.extractall(path_to_zip_file.split('.')[0] + '/')
        return path_to_zip_file.split('.')[0]


async def _main():
    async with aiohttp.ClientSession() as sess:
        ss = Sslproxies24_top(client_session=sess)
        await ss.parse()

if __name__ == '__main__':
    asyncio.run(_main())








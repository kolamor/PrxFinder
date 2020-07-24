import aiohttp
import pytest
from aiohttp import ClientSession, TCPConnector
from src.app import create_tcp_connector
from src.parse_module import request_get, DefaultParse
from src.parse_module.utils import IPPortPatternLine
from src import ProxyClient, Proxy


@pytest.mark.asyncio
async def test_create_tcp_connector():
    tcp_conn = create_tcp_connector({})
    assert isinstance(tcp_conn, TCPConnector)


@pytest.fixture()
async def aiohttp_session():
    async with ClientSession() as session:
        yield session
    pass


urls = ('https://google.com', 'http://httpbin.org/')


@pytest.mark.parametrize('url', urls)
@pytest.mark.asyncio
async def test_request_get(url, aiohttp_session):
    text = await request_get(session=aiohttp_session, url=url)
    assert isinstance(text, str)
    assert len(text) > 0


proxy_templates = [('''https://wert:ioopp@192.134.65.88:9000
                    http://23.11.67.100:80
                    socks4://89.78.13.10:44890
                    socks5://67.105.188.1:5001''',
                    ('192.134.65.88', '9000'), ('23.11.67.100', '80'), ('89.78.13.10', '44890'), ('67.105.188.1', '5001'))
                   ]


@pytest.mark.parametrize('template',  proxy_templates)
@pytest.mark.regexp
def test_parse_ip(template):
    temp, *res = template
    pars = IPPortPatternLine.findall(temp)

    for r in res:
        assert r in pars


proxy_list = ['socks5://138.197.2.106:56658', 'http://login:passs@37.45.89.1:4890']


class TestProxy:

    @pytest.mark.parametrize('proxy', proxy_list)
    def test_create_from_url(self, proxy):
        prx = Proxy.create_from_url(proxy)
        assert prx.url == proxy


class TestClient:

    @pytest.mark.parametrize('proxy', proxy_list)
    @pytest.mark.client
    @pytest.mark.asyncio
    async def test_proxy_client(self, proxy):
        proxy = Proxy.create_from_url(proxy)
        async with ProxyClient(proxy=proxy) as sess:
            assert isinstance(sess._session, aiohttp.ClientSession)
            assert sess.closed is False
        assert sess.closed is True



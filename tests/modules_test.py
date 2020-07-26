import aiohttp
import pytest
from pathlib import Path
from aiohttp import ClientSession, TCPConnector
from src.app import create_tcp_connector
from src.parse_module import request_get, DefaultParse
from src.parse_module.utils import IPPortPatternLine
from src import ProxyClient
from src import ProxyChecker, Proxy


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


def load_proxy_from_file():
    path = Path(__file__).parent.parent / '.secrets/proxys'
    with open(path) as f:
        proxys = f.read().strip().split('\n')
    return proxys


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

   # TODO create functions tests

    @pytest.mark.skip
    @pytest.mark.parametrize('proxy', load_proxy_from_file())
    @pytest.mark.asyncio
    async def test_get(self, proxy):
        proxy = Proxy.create_from_url(proxy)
        async with ProxyClient(proxy=proxy) as sess:
            answ = await sess.get()
            assert answ['status_response'] == 200
            assert 'latency' in answ.keys()


class TestProxyChecker:

    @pytest.mark.skip
    @pytest.mark.parametrize('proxy', load_proxy_from_file())
    @pytest.mark.asyncio
    async def test(self, proxy):
        proxy = Proxy.create_from_url(proxy)
        check_proxy = await ProxyChecker.check(proxy=proxy)
        assert check_proxy.is_alive is True
        assert isinstance(check_proxy.latency, float)
        assert isinstance(check_proxy.as_dict(), dict)
        keys = ['host', 'port', 'scheme', 'user', 'password']
        for k in keys:
            assert k in check_proxy.as_dict()
        print(check_proxy.as_dict())





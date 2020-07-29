import asyncio
import aiohttp
import pytest
import os
from pathlib import Path
from aiohttp import ClientSession, TCPConnector
from src.app import create_tcp_connector
from src.parse_module import request_get, DefaultParse
from src.parse_module.utils import IPPortPatternLine
from src import ProxyClient, TaskHandlerToDB, PsqlDb
from src import ProxyChecker, Proxy, TaskProxyCheckHandler, proxy_table, location_table
import asyncpgsa
import asyncpg
import sqlalchemy
import yaml

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


@pytest.mark.skipif(bool(os.environ.get('CI_TEST', False)) is False, reason='CI skip')
def load_proxy_from_file():
    try:
        path = Path(__file__).parent.parent / '.secrets/proxys'
        with open(path) as f:
            proxys = f.read().strip().split('\n')
    except Exception as e:
        proxys = []
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
    @pytest.mark.skipif(bool(os.environ.get('CI_TEST', False)) is False, reason='CI skip')
    @pytest.mark.parametrize('proxy', load_proxy_from_file())
    @pytest.mark.asyncio
    async def test_get(self, proxy):
        proxy = Proxy.create_from_url(proxy)
        async with ProxyClient(proxy=proxy) as sess:
            answ = await sess.get()
            assert answ['status_response'] == 200
            assert 'latency' in answ.keys()


class TestProxyChecker:

    @pytest.mark.skipif(bool(os.environ.get('CI_TEST', False)) is False, reason='CI skip')
    @pytest.mark.parametrize('proxy', load_proxy_from_file())
    @pytest.mark.asyncio
    async def test_check(self, proxy):
        proxy = Proxy.create_from_url(proxy)
        check_proxy = await ProxyChecker.check(proxy=proxy)
        assert check_proxy.is_alive is True
        assert isinstance(check_proxy.latency, float)
        assert isinstance(check_proxy.as_dict(), dict)
        keys = ['host', 'port', 'scheme', 'user', 'password']
        for k in keys:
            assert k in check_proxy.as_dict()


class TestTaskProxyCheckHandler:

    @pytest.mark.skipif(bool(os.environ.get('CI_TEST', False)) is False, reason='CI skip')
    @pytest.mark.parametrize('proxy', load_proxy_from_file())
    @pytest.mark.asyncio
    async def test_processing(self, proxy):
        queue_in = asyncio.Queue(2)
        queue_out = asyncio.Queue(2)
        proxy = Proxy.create_from_url(proxy)
        handler = TaskProxyCheckHandler(incoming_queue=queue_in, outgoing_queue=queue_out)
        await handler.processing_task(proxy)
        proxy_out = await asyncio.wait_for(queue_out.get(), 1)
        queue_out.task_done()
        assert isinstance(proxy_out, Proxy)

    @pytest.mark.skipif(bool(os.environ.get('CI_TEST', False)) is False, reason='CI skip')
    @pytest.mark.parametrize('proxy', load_proxy_from_file())
    @pytest.mark.asyncio
    async def test_start(self, proxy):
        queue_in = asyncio.Queue(2)
        queue_out = asyncio.Queue(2)
        proxy = Proxy.create_from_url(proxy)
        handler = TaskProxyCheckHandler(incoming_queue=queue_in, outgoing_queue=queue_out)
        await handler.start()
        await queue_in.put(proxy)
        proxy_out = await asyncio.wait_for(queue_out.get(), 30)
        queue_out.task_done()
        handler.stop()
        assert isinstance(proxy_out, Proxy)


@pytest.mark.asyncio
@pytest.mark.db
@pytest.fixture()
async def db_pool():

    default_file = Path(__file__).parent.parent / '.secrets/local_conf.yaml'
    with open(default_file, 'r') as f:
        config = yaml.safe_load(f)
    db_connect_kwargs = {}
    pool = await asyncpgsa.create_pool(dsn=config.get('POSTGRESQL_URI'), **db_connect_kwargs)
    yield pool
    await pool.close()


class TestTaskHandlerToDB:

    async def clear_test_data(self, pool_db, proxy: Proxy):
        async with pool_db.acquire() as conn:
            query = sqlalchemy.text(f"select * from proxy where host= $1 and port = $2")
            res = await conn.fetchrow(query, proxy.host, proxy.port)
            if res:
                query = sqlalchemy.text('delete from proxy where (host = $1 and port = $2)')
                res = await conn.execute(query, proxy.host, proxy.port)
            yield
            query = sqlalchemy.text('delete from proxy where (host = $1 and port = $2)')
            res = await conn.execute(query, proxy.host, proxy.port)
            yield

    @pytest.mark.skipif(bool(os.environ.get('CI_TEST', False)) is False, reason='CI skip')
    @pytest.mark.parametrize('proxy', load_proxy_from_file())
    @pytest.mark.asyncio
    @pytest.mark.db
    async def test_start(self, proxy, db_pool: asyncpg.pool.Pool, caplog):
        import logging
        caplog.set_level(logging.DEBUG)
        queue_in = asyncio.Queue(2)
        proxy = Proxy.create_from_url(proxy)
        psql_db = PsqlDb(db_connect=db_pool, table_proxy=proxy_table, table_location=location_table)
        handler = TaskHandlerToDB(incoming_queue=queue_in, psql_db=psql_db)
        await handler.start()
        assert handler.is_running() is True
        clear_test_data = self.clear_test_data(db_pool, proxy)
        await clear_test_data.__anext__()
        await queue_in.put(proxy)
        await asyncio.sleep(1)
        query = sqlalchemy.text(f"select * from proxy where host= $1 and port = $2")
        async with db_pool.acquire() as conn:
            res = await conn.fetchrow(query, proxy.host, proxy.port)
            assert res['host'] == proxy.host and res['port'] == proxy.port
        await clear_test_data.__anext__()
        handler.stop()






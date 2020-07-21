import pytest
from aiohttp import ClientSession, TCPConnector
from src.app import create_tcp_connector
from src.parse_module import request_get, DefaultParse


@pytest.mark.asyncio
async def test_create_tcp_connector():
    tcp_conn = create_tcp_connector({})
    assert isinstance(tcp_conn, TCPConnector)


@pytest.fixture()
async def aiohttp_session():
    async with ClientSession() as session:
        yield session
    pass


@pytest.mark.asyncio
async def test_request_get(aiohttp_session):
    url = 'https://google.com'
    text = await request_get(session=aiohttp_session, url=url)
    assert isinstance(text, str)
    assert len(text) > 0

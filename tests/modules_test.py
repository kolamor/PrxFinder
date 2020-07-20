import pytest
import aiohttp
from src.app import create_tcp_connector


@pytest.mark.asyncio
async def test_create_tcp_connector():
    tcp_conn = create_tcp_connector({})
    assert tcp_conn, aiohttp.TCPConnector

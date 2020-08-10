import asyncio
from asyncio import StreamWriter, StreamReader
from ..models import Proxy
from typing import Optional


class Client:
    def __init__(self, host: str, port: int, reader: StreamReader, writer: StreamWriter):
        self._reader = reader
        self._writer = writer
        self._host = host
        self._port: int = port
        self.read_timeout: int = 10
        self.write_timeout: int = 10
        self.proxy: Optional[Proxy] = None

    @classmethod
    async def init(cls, host: str, port: int) -> 'Client':
        """
        factory method
        :param host :type str
        :param port :type int
        :return: Client
        """
        reader, writer = await cls._open_connection(host=host, port=port)
        self = cls(host=host, port=port, reader=reader, writer=writer)
        return self

    @classmethod
    async def _open_connection(cls, host, port):
        reader, writer = await asyncio.open_connection(
            host, port)
        return reader, writer

    async def send(self, data: bytes):
        self._writer.write(data)
        await asyncio.wait_for(self._writer.drain(), self.write_timeout)

    async def read(self, chunk_limit: int = 2**12) -> bytes:
        reader = self._reader
        data = await asyncio.wait_for(
            reader.read(chunk_limit), self.read_timeout
        )
        return data

    def at_of(self):
        return self._reader.at_eof()


class ProxyClient:
    def __init__(self, client: Client, proxy: 'Proxy'):
        self.client = client  # type: Client
        self._proxy = proxy

    @classmethod
    async def init(cls, proxy: 'Proxy') -> 'ProxyClient':
        client = await Client.init(host=proxy.host, port=proxy.port)
        self = cls(client=client, proxy=proxy)
        return self

    async def create_proxy_connect(self, start_row: bytes):
        if self._proxy.user_pass_base64:
            proxy_auth = self._proxy.user_pass_base64
            data = start_row + b"Proxy-Authorization: Basic " + proxy_auth + b"\r\n"
        else:
            data = start_row
        await self.client.send(data=data)

    async def read(self):
        data = await self.client.read()
        return data

    async def send(self, data):
        await self.client.send(data)

    def reader_at_of(self):
        return self.client.at_of()

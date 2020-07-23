import asyncio
import datetime
from typing import Optional


class Location:
    pass


class Proxy:
    """

    """
    def __init__(self,
                 host: str,
                 port: str,
                 user: Optional[str],
                 password: Optional[str],
                 location: Optional[Location] = None,
                 schema: str = 'http',
                 is_alive: Optional[bool] = None,
                 latency: Optional[float] = None,
                 checked_at: Optional[datetime.datetime] = None
                 ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.location = location
        self.schema = schema
        self.is_alive = is_alive
        self.latency = latency
        self.checked_at = checked_at

    def create_uri(self):
        host_port = f'{self.host}:{self.port}'
        if self.user and self.password:
            uri = f'{self.schema}://{self.user}:{self.password}@{host_port}'
        else:
            uri = f'{self.schema}://{host_port}'
        return uri

    def __str__(self):
        return self.create_uri

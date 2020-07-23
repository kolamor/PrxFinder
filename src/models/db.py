from sqlalchemy import (
    Table, Text, Integer, VARCHAR, MetaData, Column, BOOLEAN, ForeignKey, DateTime, CheckConstraint, REAL,
    UniqueConstraint
)
import sqlalchemy as sa
from sqlalchemy.sql import func
import datetime

from sqlalchemy.sql import expression
from sqlalchemy.ext.compiler import compiles

__all__ = ('proxy', 'location')

meta = MetaData()
proxy = Table(
    'proxy', meta,
    Column('host', VARCHAR),
    Column('port', Integer),
    Column('user', VARCHAR, nullable=True),
    Column('password', VARCHAR, nullable=True),
    Column('checked_at', DateTime(timezone=False), server_default=func.now()),
    Column('schema', VARCHAR(6)),
    Column('location', VARCHAR, ForeignKey('location.code', ondelete='SET NULL'), ),
    Column('latency', REAL, nullable=True),
    Column('is_alive', BOOLEAN, nullable=True),
    Column('anonymous', BOOLEAN, nullable=True),
    UniqueConstraint('host', 'port', name='unique_host_port'),
)

location = Table(
    'location', meta,
    Column('city', VARCHAR),
    Column('country', VARCHAR),
    Column('code', VARCHAR, primary_key=True),
    Column('region_code', nullable=True)

)

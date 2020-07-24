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
# Model table Proxy
proxy = Table(
    'proxy', meta,
    Column('host', VARCHAR),
    Column('port', Integer),
    Column('user_', VARCHAR, nullable=True),
    Column('password', VARCHAR, nullable=True),
    Column('date_creation', DateTime(timezone=False)),
    Column('protocol', VARCHAR(6)),
    Column('location_code', VARCHAR, ForeignKey('location.code', ondelete='SET NULL'), ),
    Column('latency', Integer, nullable=True),
    Column('is_alive', BOOLEAN, nullable=True),
    Column('anonymous', BOOLEAN, nullable=True),
    UniqueConstraint('host', 'port', name='unique_host_port'),
)

# Model table location, use from proxy sort
location = Table(
    'location', meta,
    Column('city', VARCHAR),
    Column('country', VARCHAR),
    Column('code', VARCHAR, primary_key=True),
    Column('region_code', nullable=True)

)

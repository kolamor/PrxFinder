from sqlalchemy import (
    Table, Text, Integer, VARCHAR, MetaData, Column, BOOLEAN, ForeignKey, DateTime, CheckConstraint, REAL,
    UniqueConstraint, Float
)
import sqlalchemy as sa
from sqlalchemy.sql import func
import datetime

from sqlalchemy.sql import expression
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import INET

__all__ = ('proxy_table', 'location_table')

meta = MetaData()

# Model table Proxy
proxy_table = Table(
    'proxy', meta,
    # Column('host', VARCHAR),
    Column('host', INET, nullable=False),
    Column('port', Integer),
    Column('login', VARCHAR, nullable=True),
    Column('password', VARCHAR, nullable=True),
    Column('date_creation', DateTime(timezone=False)),
    Column('scheme', VARCHAR(6)),
    Column('latency', Float, nullable=True),
    Column('is_alive', BOOLEAN, nullable=True),
    Column('anonymous', BOOLEAN, nullable=True),
    UniqueConstraint('host', 'port', name='unique_host_port'),
)

# Model table location, use from proxy sort
location_table = Table(
    'location', meta,
    Column('ip', INET, primary_key=True),
    Column('country_name', VARCHAR),
    Column('country_code', VARCHAR, nullable=True),
    Column('region_code', nullable=True),
    Column('city', VARCHAR),
    Column('time_zone', VARCHAR),
    Column('latitude', Float),
    Column('longitude', Float),
    Column('metro_code', VARCHAR)
)

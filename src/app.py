import asyncpgsa
import aiohttp
import asyncio
import logging
from aiohttp import web, ClientSession, TCPConnector
from .routes import setup_routes

logger = logging.getLogger(__name__)


async def create_app(config: dict) -> aiohttp.web.Application:
    app = web.Application()
    app['config'] = config

    setup_routes(app)
    app.on_startup.append(on_start)
    app.on_cleanup.append(on_shutdown)

    return app


async def on_start(app):
    config = app['config']
    tcp_config = {}
    app['http_client'] = aiohttp.ClientSession(connector=create_tcp_connector(tcp_config))
    # app['db'] = await asyncpgsa.create_pool(dsn=config['database_uri'])


async def on_shutdown(app):
    logger.info('on_shutdown')
    # await app['db'].close()
    # logger.info('PSQL closed')
    await app['http_client'].close()
    logger.info('http_client closed')


def create_tcp_connector(config: dict) -> TCPConnector:
    """
    :param config: dict

    :return: TCPConnector
    """
    connector = TCPConnector(
        limit_per_host=config.get('TCP_limit_per_host', 100),
        limit=config.get('TCP_limit_per_host', 100),
        verify_ssl=config.get('verify_ssl', False),
        **config
    )
    return connector

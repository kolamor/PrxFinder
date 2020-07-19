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
    # app['db'] = await asyncpgsa.create_pool(dsn=config['database_uri'])
    # app['http_client'] = ClientSession(connector=TCPConnector(limit=config['http_client_limit_TCPConnector'],
    #                                                           limit_per_host=config['http_client_limit_per_host_TCPConnector']
    #                                                           ))

async def on_shutdown(app):
    # logger.info('on_shutdown')
    # await app['db'].close()
    # logger.info('PSQL closed')
    await app['http_client'].close()
    logger.info('http_client closed')

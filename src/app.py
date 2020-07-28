import asyncpgsa
import aiohttp
import asyncio
import logging
from aiohttp import web, ClientSession, TCPConnector
import src
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
    db_connect_kwargs = {}
    app['db'] = await asyncpgsa.create_pool(dsn=config['POSTGRESQL_URI'], **db_connect_kwargs)
    app['in_checker_queue'] = asyncio.Queue(config.get('limit_checker_queues', 0))
    app['out_checker_queue'] = asyncio.Queue(config.get('limit_checker_queues', 0))
    app['proxy_save_db_queue'] = asyncio.Queue()
    app['proxy_to_db'] = src.ProxyToDB(db_connect=app['db'], table_proxy=src.proxy_table,
                                       table_location=src.location_table)
    await start_check_proxy(app=app, config=config)


async def on_shutdown(app):
    logger.info('on_shutdown')
    await app['db'].close()
    logger.info('PSQL closed')
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


async def start_check_proxy(app: aiohttp.web.Application , config: dict):
    if config.get('start_check_proxy', True) is True:
        handler = src.TaskProxyCheckHandler(incoming_queue=app['in_checker_queue'],
                                            outgoing_queue=app['out_checker_queue'],
                                            max_tasks=config.get('limit_check_proxy', 50))
        await handler.start()
        app['proxy_check_handler'] = handler
        print('Start proxy_check_handler')
        return

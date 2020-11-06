import functools
import asyncpgsa
import aiohttp
import asyncio
import logging
from aiohttp import web, ClientSession, TCPConnector
import src
import src.parse_module.sources as sources
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
    app['http_client'] = ClientSession(connector=create_tcp_connector(tcp_config))
    db_connect_kwargs = {}
    app['asyncpgsa_db_pool'] = await asyncpgsa.create_pool(dsn=config['POSTGRESQL_URI'], **db_connect_kwargs)
    app['in_checker_queue'] = asyncio.Queue(config.get('limit_checker_queues', 0))
    app['out_checker_queue'] = asyncio.Queue(config.get('limit_checker_queues', 0))
    await start_check_proxy(app=app, config=config)
    asyncio.ensure_future(src.start_prx_serve(app))



async def on_shutdown(app):

    logger.info('on_shutdown')
    await shutdown_proxy_in_process(app)
    await app['asyncpgsa_db_pool'].close()
    logger.info('PSQL closed')
    await app['http_client'].close()
    logger.info('http_client closed')


async def shutdown_proxy_in_process(app):  # TODO need full update in process
    try:
        start_proxy_handler: src.StartProxyHandler = app['start_proxy_handler']
        start_proxy_handler.pause()
        # create hard refs
        refs = set(src.ReferenceProxy.get())
        proxy_db: src.ProxyDb = app['ProxyDb']
    except Exception as e:
        logger.error(f'shutdown error {e}, {e.args}')
        refs = []
    tasks = []
    for proxy in refs:
        try:
            logger.debug(f"replace in process false {proxy}  of {len(src.ReferenceProxy.get())}")
            context = {
                "host": proxy.host,
                "port": proxy.port,
                "in_process": False
            }
            task = asyncio.ensure_future( proxy_db.update_proxy_pm(**context))
            tasks.append(task)
        except Exception as e:
            logger.info(f"Shutdown Proxy, :: {e}, {e.args}")
    res = await asyncio.gather(*tasks, return_exceptions=True)
    start_proxy_handler.stop()
    logger.info(f'STOP {start_proxy_handler.__class__.__name__}')


def create_tcp_connector(config: dict) -> TCPConnector:
    """
    """
    connector = TCPConnector(
        limit_per_host=config.get('TCP_limit_per_host', 100),
        limit=config.get('TCP_limit_per_host', 100),
        verify_ssl=config.get('verify_ssl', False),
        **config
    )
    return connector


async def start_check_proxy(app: aiohttp.web.Application, config: dict):
    if config.get('start_check_proxy', True) is True:
        await create_task_handlers_api_to_db(app=app, config=config)
        print('Start proxy_check_handler')
        return


async def create_task_handlers_api_to_db(app: aiohttp.web.Application, config: dict):
    db = app['asyncpgsa_db_pool']
    proxy_db = app['ProxyDb'] = src.ProxyDb(db_connect=db, table_proxy=src.proxy_table)
    queue_api_to_db = app['queue_api_to_db'] = asyncio.Queue()
    task_handler_api_to_db = app['task_handler_api_to_db'] = src.TaskHandlerToDB(incoming_queue=queue_api_to_db,
                                                                                 proxy_db=proxy_db)
    await task_handler_api_to_db.start()

    start_proxy_queue = app['start_proxy_queue'] = asyncio.Queue(1)
    start_proxy_handler = app['start_proxy_handler'] = src.StartProxyHandler(proxy_db=proxy_db,
                                                                             outgoing_queue=start_proxy_queue)
    await start_proxy_handler.start()

    checker_out_queue = app['checker_out_queue'] = asyncio.Queue()
    checker_handler = app['checker_handler'] = src.TaskProxyCheckHandler(incoming_queue=start_proxy_queue,
                                                                         outgoing_queue=checker_out_queue,
                                                                         max_tasks=100)
    await checker_handler.start()

    api_location = src.ApiLocation(app['http_client'])
    location_db = src.LocationDb(db_connect=db, table_location=src.location_table)
    location_handler = app['location_handler'] = src.LocationTaskHandler(api_location=api_location,
                                                                         location_db=location_db,
                                                                         incoming_queue=checker_out_queue,
                                                                         outgoing_queue=queue_api_to_db, max_tasks=20)
    await location_handler.start()

    #  start parse

    await parse_sources(app=app, config=config, queue=queue_api_to_db)


async def parse_sources(app: aiohttp.web.Application, config: dict, queue: asyncio.Queue):
    """start parse sources
        queue - income(api to db)
    """

    for source in config['PARSE_SOURCES']:
        cls_source = getattr(sources, source)
        obj = cls_source(client_session=app['http_client'], out_queue=queue)
        print(f'start parse {cls_source}')
        asyncio.create_task(obj.parse()).add_done_callback(functools.partial(callback_parse, cls_source.__name__))


def callback_parse(*args, **kwargs):
    resource, task = args
    coro = task.get_coro()
    logger.debug(f'{resource} :: {task}')









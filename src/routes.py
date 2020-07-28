from .handlers import api
from aiohttp import web
import logging


logger = logging.getLogger(__name__)


def setup_routes(app):
	app.router.add_route('GET', '/', api.Root)
	app.router.add_routes([
		web.post('/proxy', api.ProxyHandler, ),
	])

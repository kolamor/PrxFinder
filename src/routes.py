from .handlers import api
import logging

logger = logging.getLogger(__name__)


def setup_routes(app):
	app.router.add_route('GET', '/', api.Root)
	app.router.add_routes([
	])
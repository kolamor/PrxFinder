from aiohttp.web import View, json_response
from ..models import Proxy, ReferenceLocation, ReferenceProxy
import logging

logger = logging.getLogger(__name__)


class Root(View):
    async def get(self):
        contex = {
            'test': 'hello word'
        }
        return json_response(contex, status=200)


class ProxyHandler(View):
    async def post(self):
        """input json(proxy), create Proxy, put in Queue.
            template = {
            proxys : ['http://login@password@123.23.55.23',
                      'socks5://12.34.65.1, ... ]
            }
        """
        try:
            data = await self.request.json()
            proxys = [Proxy.create_from_url(prx) for prx in data['proxys']]
        except Exception as e:
            logger.error(f'{e} ::: {e.args}')
            return json_response(status=400, data={'Error': f'Bad_request {e} :: {e.args}'})
        for prx in proxys:
            await self.request.app['queue_api_to_db'].put(prx)
        return json_response(status=200, data={'status': 'put to processing'})


class StatsHandler(View):

    async def get(self):
        context = {
            "Proxy": len(ReferenceProxy.get()),
            "Location": len(ReferenceLocation.get())
        }
        return json_response(status=200, data=context, )

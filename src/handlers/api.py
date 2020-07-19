from aiohttp.web import View, json_response


class Root(View):
    async def get(self):
        contex = {
            'test': 'hello word'
        }
        return json_response(contex, status=200)
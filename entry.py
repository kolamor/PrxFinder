import argparse
import asyncio
import aiohttp
import logging
from src.settings import load_config
from src import create_app


try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    print("uvloop is not install")

parser = argparse.ArgumentParser(description='app api_es')
parser.add_argument('--host', help='Host to listen', default='0.0.0.0')
parser.add_argument('--port', help='Port to accept connections', default='5000')
parser.add_argument('--reload', action='store_true', help='Auto reload code on change')
parser.add_argument('-c', '--config', type=argparse.FileType('r'), 	help='Path to configuration file')

args = parser.parse_args()
config = load_config(args.config)
app = create_app(config=config)

if args.reload:
    print('Start with code reload')
    import aioreloader
    aioreloader.start()


if __name__ == '__main__':
    logging.basicConfig(level=getattr(logging, config.get('LOGGING_LEVEL', 'DEBUG')))
    aiohttp.web.run_app(app, host=args.host, port=args.port)
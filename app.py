import os
import waitress
import subprocess

from flask import Flask, jsonify
from flask_restx import Resource, Api
from flask.logging import create_logger


# instantiate the app
app = Flask(__name__)

api = Api(app)

LOGGER = create_logger(app)

DEV_MODE = 0
HOST = '0.0.0.0'
PORT = os.environ['PORT']
THREADS = 8
URL_SCHEME = 'http'
URL_PREFIX = ''

if "DEV_MODE" in os.environ:
    try:
        DEV_MODE_TMP = int(os.environ['DEV_MODE'])
        if DEV_MODE_TMP in (1, 0):
            DEV_MODE = DEV_MODE_TMP
            LOGGER.info('Overriding DEV_MODE=%s', DEV_MODE)
        else:
            LOGGER.error('Wrong env var value. Setting DEV_MODE=0 by default')
    except Exception as ex:
        LOGGER.error('Wrong env var value. Setting DEV_MODE=0 by default')


@app.route("/version")
def version_endpoint():
    result = subprocess.run(['allure', '--version'], stdout=subprocess.PIPE)
    body = {
        "message": result
    }
    resp = jsonify(body)
    resp.status_code = 200
    return resp


if __name__ == '__main__':
    if DEV_MODE == 1:
        LOGGER.info('Starting in DEV_MODE')
        app.run(host=HOST, port=int(PORT))
    else:
        waitress.serve(app, threads=THREADS, host=HOST, port=PORT,
                       url_scheme=URL_SCHEME, url_prefix=URL_PREFIX)


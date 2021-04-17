from threading import Thread

from flask import Blueprint, Flask
from loguru import logger
from waitress import serve

blueprint = Blueprint("celery_exporter", __name__)


@blueprint.route("/")
def index():
    return "OK"


@blueprint.route("/health")
def health():
    return "OK"


def start_http_server(port):
    app = Flask(__name__)
    app.register_blueprint(blueprint)
    Thread(
        target=serve,
        args=(app,),
        kwargs=dict(host="0.0.0.0", port=port, _quiet=True),
        daemon=True,
    ).start()
    logger.info("Started http server at port={}", port)

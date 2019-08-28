import logging
import os

from flask import Flask
from flask_cors import CORS

from rest.api.definitions import swaggerui_blueprint, SWAGGER_URL
from rest.api.docker_scheduler import DockerScheduler
from rest.api.eureka_registrator import EurekaRegistrator


def create_app():
    app_append_id = ""
    if os.environ.get('APP_APPEND_ID'):
        app_append_id = os.environ.get('APP_APPEND_ID')
    if os.environ.get('EUREKA_SERVER'):
        EurekaRegistrator(os.environ.get('EUREKA_SERVER')).register_app(os.environ.get("APP_IP_PORT"), app_append_id)
    DockerScheduler().start()
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('rest.api.flask_config.Config')
    CORS(app)
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
    app.logger.setLevel(logging.DEBUG)
    with app.app_context():
        return app

import logging

from flask import Flask
from flask_cors import CORS

from rest.api.definitions import swaggerui_blueprint, SWAGGER_URL
from rest.api.docker_scheduler import DockerScheduler


def create_app():
    DockerScheduler().start()
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('rest.api.flask_config.Config')
    CORS(app)
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
    app.logger.setLevel(logging.DEBUG)
    with app.app_context():
        return app

import logging

from flask import Flask
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint

from rest.api.views.flask_config import Config
from rest.utils.env_startup import EnvStartup


class FlaskApp:
    __instance = None

    @staticmethod
    def get_instance():
        if FlaskApp.__instance is None:
            FlaskApp()
        return FlaskApp.__instance

    def __init__(self):
        FlaskApp.__instance = Flask(__name__, instance_relative_config=False)
        FlaskApp.__instance.config.from_object(Config)
        CORS(FlaskApp.__instance)
        FlaskApp.__instance.logger.setLevel(logging.DEBUG)


app = FlaskApp.get_instance()
app.register_blueprint(get_swaggerui_blueprint(
    base_url='/{}/api/docs'.format(EnvStartup.get_instance().get("deploy_on")),
    api_url='/{}/swagger/swagger.yml'.format(EnvStartup.get_instance().get("deploy_on")),
    config={
        'app_name': "estuary-deployer"
    }), url_prefix='/{}/api/docs'.format(EnvStartup.get_instance().get("deploy_on")))

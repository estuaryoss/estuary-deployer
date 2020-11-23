import json
import logging

from flask import Flask, Response
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint

from rest.api.exception.api_exception import ApiException
from rest.api.responsehelpers.http_response import HttpResponse
from rest.api.views.flask_config import Config


class AppCreatorSingleton:
    __instance = None
    __app = None

    @staticmethod
    def get_instance():
        if AppCreatorSingleton.__instance is None:
            AppCreatorSingleton()
        return AppCreatorSingleton.__instance

    def __init__(self):
        """ The constructor. This class gets a single flask app """
        self.app = Flask(__name__, instance_relative_config=False)
        self.app.config.from_object(Config)
        CORS(self.app)
        self.app.register_blueprint(get_swaggerui_blueprint(
            base_url='/api/docs',
            api_url='/docker/swagger/swagger.yml',
            config={
                'app_name': "estuary-deployer"
            }), url_prefix='/api/docs')
        self.app.logger.setLevel(logging.DEBUG)

        if AppCreatorSingleton.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            AppCreatorSingleton.__instance = self

    @staticmethod
    def handle_api_error(e):
        return Response(json.dumps(
            HttpResponse().response(code=e.code, message=e.message,
                                    description="Exception({})".format(e.exception.__str__()))), 500,
            mimetype="application/json")

    def get_app(self):
        with self.app.app_context():
            self.app.register_error_handler(ApiException, self.handle_api_error)
            return self.app


app = AppCreatorSingleton.get_instance().get_app()

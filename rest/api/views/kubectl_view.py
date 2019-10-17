import json
import logging
import os
import sys
import traceback
from secrets import token_hex

from flask import request, Response, Flask
from flask_classful import FlaskView, route
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint

from about import properties
from entities.render import Render
from rest.api.apiresponsehelpers.active_deployments_response import ActiveDeployments
from rest.api.apiresponsehelpers.constants import Constants
from rest.api.apiresponsehelpers.error_codes import ErrorCodes
from rest.api.apiresponsehelpers.http_response import HttpResponse
from rest.api.definitions import env_vars
from rest.api.flask_config import Config
from rest.api.views.routes import Routes
from rest.utils.io_utils import IOUtils
from rest.utils.kubectl_utils import KubectlUtils


class KubectlView(FlaskView, Routes):

    def __init__(self):
        self.app = Flask(__name__, instance_relative_config=False)
        self.app.config.from_object(Config)
        CORS(self.app)
        self.app.register_blueprint(self.get_swagger_blueprint(), url_prefix='/kubectl/api/docs')
        self.app.logger.setLevel(logging.DEBUG)

    def get_swagger_blueprint(self):
        return get_swaggerui_blueprint(
            base_url='/kubectl/api/docs',
            api_url='/kubectl/swagger/swagger.yml',
            config={
                'app_name': "estuary-deployer"
            },
        )

    def index(self):
        return "kubectl"

    def get_app(self):
        return self.app

    @route('/swagger/swagger.yml')
    def swagger(self):
        return self.app.send_static_file("kubectl.yml")

    @route('/env')
    def get_vars(self):
        http = HttpResponse()
        return Response(
            json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), env_vars)),
            200, mimetype="application/json")

    @route('/ping')
    def ping(self):
        http = HttpResponse()
        return Response(
            json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), "pong")),
            200, mimetype="application/json")

    @route('/about')
    def about(self):
        http = HttpResponse()
        return Response(
            json.dumps(
                http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), properties["name"])),
            200, mimetype="application/json")

    @route('/getenv/<name>', methods=['GET'])
    def get_env(self, name):
        name = name.upper().strip()
        http = HttpResponse()
        try:
            response = Response(json.dumps(
                http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), os.environ[name])), 200,
                mimetype="application/json")
        except Exception as e:
            result = "Exception({0})".format(e.__str__())
            response = Response(json.dumps(http.failure(Constants.GET_CONTAINER_ENV_VAR_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.GET_CONTAINER_ENV_VAR_FAILURE) % name,
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
        return response

    @route('/rend/<template>/<variables>', methods=['GET'])
    def get_content(self, template, variables):
        os.environ['TEMPLATE'] = template.strip()
        os.environ['VARIABLES'] = variables.strip()
        http = HttpResponse()
        try:
            r = Render(os.environ.get('TEMPLATE'), os.environ.get('VARIABLES'))
            response = Response(r.rend_template(), 200, mimetype="text/plain")
            # response = Response(json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result)), 200, mimetype="application/json")
        except Exception as e:
            result = "Exception({0})".format(e.__str__())
            response = Response(json.dumps(http.failure(Constants.JINJA2_RENDER_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.JINJA2_RENDER_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/rendwithenv/<template>/<variables>', methods=['POST'])
    def get_content_with_env(self, template, variables):
        try:
            input_json = request.get_json(force=True)
            for key, value in input_json.items():
                if key not in env_vars:
                    os.environ[str(key)] = str(value)
        except:
            pass

        os.environ['TEMPLATE'] = template.strip()
        os.environ['VARIABLES'] = variables.strip()

        http = HttpResponse()
        try:
            r = Render(os.environ.get('TEMPLATE'), os.environ.get('VARIABLES'))
            response = Response(r.rend_template(), 200, mimetype="text/plain")
        except Exception as e:
            result = "Exception({0})".format(e.__str__())
            response = Response(json.dumps(http.failure(Constants.JINJA2_RENDER_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.JINJA2_RENDER_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/getdeploymentinfo', methods=['GET'])
    def get_active_deployments(self):
        kubectl_utils = KubectlUtils()
        http = HttpResponse()
        active_deployments = kubectl_utils.get_active_deployments()
        self.app.logger.debug('Active deployments: %s', len(active_deployments))

        return Response(
            json.dumps(
                http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), active_deployments)),
            200, mimetype="application/json")

    @route('/deploystart', methods=['POST'])
    def deploystart(self):
        kubectl_utils = KubectlUtils()
        http = HttpResponse()

        token = token_hex(8)
        dir = f"{Constants.DOCKER_PATH}{token}"
        file = f"{dir}/{token}"

        try:
            IOUtils.create_dir(dir)
            input_data = request.data.decode('utf-8')
            IOUtils.write_to_file(file, input_data)
            [out, err] = kubectl_utils.up(f"{file}")
            if err:
                return Response(json.dumps(http.failure(Constants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE),
                                                        err,
                                                        str(traceback.format_exc()))), 404,
                                mimetype="application/json")
            response = Response(
                json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), token)), 200,
                mimetype="application/json")
        except FileNotFoundError as e:
            result = "Exception({0})".format(e.__str__())
            response = Response(json.dumps(http.failure(Constants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
        except:
            result = "Exception({0})".format(sys.exc_info()[0])
            response = Response(json.dumps(http.failure(Constants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/deploystartenv/<template>/<variables>', methods=['POST'])
    def deploystartenv(self, template, variables):
        kubectl_utils = KubectlUtils()
        try:
            input_json = request.get_json(force=True)
            for key, value in input_json.items():
                if key not in env_vars:
                    os.environ[str(key)] = str(value)
        except:
            pass

        os.environ['TEMPLATE'] = template.strip()
        os.environ['VARIABLES'] = variables.strip()
        self.self.app.logger.debug("Templates: " + os.environ.get('TEMPLATE'))
        self.app.logger.debug("Variables: " + os.environ.get('VARIABLES'))
        token = token_hex(8)
        dir = f"{Constants.DOCKER_PATH}{token}"
        file = f"{dir}/{token}"
        http = HttpResponse()

        try:
            r = Render(os.environ.get('TEMPLATE'), os.environ.get('VARIABLES'))
            IOUtils.create_dir(dir)
            IOUtils.write_to_file(file)
            IOUtils.write_to_file(file, r.rend_template())
            kubectl_utils.up(f"{file}")
            result = str(token)
            response = Response(
                json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result)), 200,
                mimetype="application/json")
        except FileNotFoundError as e:
            result = "Exception({0})".format(e.__str__())
            response = Response(json.dumps(http.failure(Constants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
        except:
            result = "Exception({0})".format(sys.exc_info()[0])
            response = Response(json.dumps(http.failure(Constants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/deploystart/<template>/<variables>', methods=['GET'])
    def deploystart_from_server(self, template, variables):
        kubectl_utils = KubectlUtils()
        http = HttpResponse()
        os.environ['TEMPLATE'] = template.strip()
        os.environ['VARIABLES'] = variables.strip()
        self.app.logger.debug("Templates: " + os.environ.get('TEMPLATE'))
        self.app.logger.debug("Variables: " + os.environ.get('VARIABLES'))
        token = token_hex(8)
        dir = f"{Constants.DOCKER_PATH}{token}"
        file = f"{dir}/{token}"

        try:
            r = Render(os.environ.get('TEMPLATE'), os.environ.get('VARIABLES'))
            IOUtils.create_dir(dir)
            IOUtils.write_to_file(file)
            IOUtils.write_to_file(file, r.rend_template())
            kubectl_utils.up(f"{file}")
            result = str(token)
            response = Response(
                json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result)), 200,
                mimetype="application/json")
        except FileNotFoundError as e:
            result = "Exception({0})".format(e.__str__())
            response = Response(json.dumps(http.failure(Constants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
        except:
            result = "Exception({0})".format(sys.exc_info()[0])
            response = Response(json.dumps(http.failure(Constants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/deploystatus/<id>', methods=['GET'])
    def deploy_status(self, id):
        id = id.strip()
        kubectl_utils = KubectlUtils()
        http = HttpResponse()
        try:
            [out, err] = kubectl_utils.ps(id)
            if "Cannot connect to the Docker daemon".lower() in err.lower():
                return Response(json.dumps(http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING),
                                                        err,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
            result = out.split("\n")[1:-1]
            response = Response(
                json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS),
                                        ActiveDeployments.active_deployment(id, result))), 200,
                mimetype="application/json")
            self.app.logger.debug('Output: %s', out)
            self.app.logger.debug('Error: %s', err)
        except FileNotFoundError as e:
            result = "Exception({0})".format(e.__str__())
            response = Response(json.dumps(http.failure(Constants.DEPLOY_STATUS_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_STATUS_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
        except:
            result = "Exception({0})".format(sys.exc_info()[0])
            response = Response(json.dumps(http.failure(Constants.DEPLOY_STATUS_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_STATUS_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/getdeployerfile', methods=['POST'])
    def get_deployer_file(self):
        http = HttpResponse()
        try:
            input_json = request.get_json(force=True)
            file = input_json["file"]
        except Exception as e:
            exception = "Exception({0})".format(sys.exc_info()[0])
            return Response(json.dumps(http.failure(Constants.MISSING_PARAMETER_POST,
                                                    ErrorCodes.HTTP_CODE.get(Constants.MISSING_PARAMETER_POST) % "file",
                                                    exception,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        try:
            result = Response(IOUtils.read_file(file), 200, mimetype="text/plain")
        except:
            exception = "Exception({0})".format(sys.exc_info()[0])
            result = Response(json.dumps(http.failure(Constants.GET_ESTUARY_DEPLOYER_FILE_FAILURE,
                                                      ErrorCodes.HTTP_CODE.get(
                                                          Constants.GET_ESTUARY_DEPLOYER_FILE_FAILURE),
                                                      exception,
                                                      str(traceback.format_exc()))), 404, mimetype="application/json")
        return result

    @route('/deploylogs/<id>', methods=['GET'])
    def deploy_logs(self, id):
        id = id.strip()
        dir = f"{Constants.DOCKER_PATH}{id}"
        file = f"{dir}/{id}"
        kubectl_utils = KubectlUtils()
        http = HttpResponse()

        try:
            [out, err] = kubectl_utils.logs(file)
            self.app.logger.debug('Output: %s', out)
            self.app.logger.debug('Error: %s', err)
            if err:
                return Response(json.dumps(http.failure(Constants.GET_LOGS_FAILED,
                                                        ErrorCodes.HTTP_CODE.get(Constants.GET_LOGS_FAILED) % id, err,
                                                        err)), 404, mimetype="application/json")
        except:
            exception = "Exception({0})".format(sys.exc_info()[0])
            return Response(json.dumps(http.failure(Constants.GET_LOGS_FAILED,
                                                    ErrorCodes.HTTP_CODE.get(Constants.GET_LOGS_FAILED) % id, exception,
                                                    exception)), 404, mimetype="application/json")

        return Response(
            json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), out.split("\n"))),
            200, mimetype="application/json")

    @route('/uploadfile', methods=['POST'])
    def uploadfile(self):
        io_utils = IOUtils()
        http = HttpResponse()
        try:
            input_data = request.get_json(force=True)
            file_content = input_data["content"]
            file_path = input_data["file"]
            if not input_data:
                return Response(json.dumps(http.failure(Constants.EMPTY_REQUEST_BODY_PROVIDED,
                                                        ErrorCodes.HTTP_CODE.get(Constants.EMPTY_REQUEST_BODY_PROVIDED),
                                                        ErrorCodes.HTTP_CODE.get(Constants.EMPTY_REQUEST_BODY_PROVIDED),
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
        except Exception as e:
            exception = "Exception({0})".format(e.__str__())
            return Response(json.dumps(http.failure(Constants.UPLOAD_FILE_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(Constants.UPLOAD_FILE_FAILURE),
                                                    exception,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        try:
            io_utils.write_to_file(file_path, file_content)
        except Exception as e:
            exception = "Exception({0})".format(e.__str__())
            return Response(json.dumps(http.failure(Constants.UPLOAD_FILE_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(Constants.UPLOAD_FILE_FAILURE),
                                                    exception,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")

        return Response(json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS),
                                                ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))),
                        200,
                        mimetype="application/json")

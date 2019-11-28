import json
import logging
import os
import re
import sys
import traceback
from secrets import token_hex

from flask import request, Response, Flask
from flask_classful import FlaskView, route
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from fluent import sender

from about import properties
from entities.render import Render
from rest.api.apiresponsehelpers.constants import Constants
from rest.api.apiresponsehelpers.error_codes import ErrorCodes
from rest.api.apiresponsehelpers.http_response import HttpResponse
from rest.api.definitions import env_vars, kubectl_swagger_file_content
from rest.api.flask_config import Config
from rest.api.logginghelpers.request_dumper import RequestDumper
from rest.api.views.routes_abc import Routes
from rest.utils.cmd_utils import CmdUtils
from rest.utils.fluentd_utils import FluentdUtils
from rest.utils.io_utils import IOUtils
from rest.utils.kubectl_utils import KubectlUtils


class KubectlView(FlaskView, Routes):

    def __init__(self):
        self.app = Flask(__name__, instance_relative_config=False)
        self.app.config.from_object(Config)
        CORS(self.app)
        self.app.register_blueprint(self.get_swagger_blueprint(), url_prefix='/kubectl/api/docs')
        self.app.logger.setLevel(logging.DEBUG)
        self.logger = sender.FluentSender(properties.get('name'), host=properties["fluentd_ip"],
                                          port=int(properties["fluentd_port"]))
        self.fluentd_utils = FluentdUtils(self.logger)
        self.request_dumper = RequestDumper()

    def before_request(self, name, *args, **kwargs):
        ctx = self.app.app_context()
        ctx.g.cid = token_hex(8)
        self.request_dumper.set_correlation_id(ctx.g.cid)

        response = self.fluentd_utils.debug(tag="api", msg=self.request_dumper.dump(request=request))
        self.app.logger.debug(f"{response}")

    def after_request(self, name, http_response):
        headers = dict(http_response.headers)
        headers['Correlation-Id'] = self.request_dumper.get_correlation_id()
        http_response.headers = headers

        response = self.fluentd_utils.debug(tag="api", msg=self.request_dumper.dump(http_response))
        self.app.logger.debug(f"{response}")

        return http_response

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

    def get_view_fluentd_utils(self):
        return self.fluentd_utils

    def get_view_logger(self):
        return self.logger

    def get_view_app(self):
        return self.app

    @route('/swagger/swagger.yml')
    def swagger(self):
        return Response(kubectl_swagger_file_content, 200, mimetype="application/json")

    @route('/env')
    def get_env_vars(self):
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

    @route('/getenv/<envvar>', methods=['GET'])
    def get_env_var(self, envvar):
        envvar = envvar.upper().strip()
        http = HttpResponse()
        try:
            response = Response(json.dumps(
                http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), os.environ[envvar])), 200,
                mimetype="application/json")
        except Exception as e:
            result = "Exception({0})".format(e.__str__())
            response = Response(json.dumps(http.failure(Constants.GET_CONTAINER_ENV_VAR_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.GET_CONTAINER_ENV_VAR_FAILURE) % envvar,
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
        self.app.logger.debug({"msg": {"active_deployments": f"{len(active_deployments)}"}})
        return Response(
            json.dumps(
                http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), active_deployments)),
            200, mimetype="application/json")

    @route('/deploystart', methods=['POST'])
    def deploy_start(self):
        kubectl_utils = KubectlUtils()
        http = HttpResponse()
        fluentd_tag = "deploy_start"
        token = token_hex(8)
        dir = f"{Constants.DEPLOY_FOLDER_PATH}{token}"
        file = f"{dir}/{token}"

        try:
            IOUtils.create_dir(dir)
            input_data = request.data.decode('utf-8')
            IOUtils.write_to_file(file, input_data)
            status = kubectl_utils.up(f"{file}")
            self.fluentd_utils.emit(fluentd_tag, {"msg": status})
            if status.get('err'):
                return Response(json.dumps(http.failure(Constants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE),
                                                        status.get('err'),
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
    def deploy_start_env(self, template, variables):
        http = HttpResponse()
        kubectl_utils = KubectlUtils()
        fluentd_tag = "deploy_start_env"
        try:
            input_json = request.get_json(force=True)
            for key, value in input_json.items():
                if key not in env_vars:
                    os.environ[str(key)] = str(value)
        except:
            pass

        os.environ['TEMPLATE'] = template.strip()
        os.environ['VARIABLES'] = variables.strip()
        self.app.logger.debug({"msg": {"template_file": os.environ.get('TEMPLATE')}})
        self.app.logger.debug({"msg": {"variables_file": os.environ.get('VARIABLES')}})
        token = token_hex(8)
        dir = f"{Constants.DEPLOY_FOLDER_PATH}{token}"
        file = f"{dir}/{token}"

        try:
            r = Render(os.environ.get('TEMPLATE'), os.environ.get('VARIABLES'))
            IOUtils.create_dir(dir)
            IOUtils.write_to_file(file)
            IOUtils.write_to_file(file, r.rend_template())
            status = kubectl_utils.up(f"{file}")
            self.fluentd_utils.emit(fluentd_tag, {"msg": status})
            if status.get('err'):
                return Response(json.dumps(http.failure(Constants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE),
                                                        status.get('err'),
                                                        str(traceback.format_exc()))), 404,
                                mimetype="application/json")
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
    def deploy_start_from_server(self, template, variables):
        kubectl_utils = KubectlUtils()
        http = HttpResponse()
        fluentd_tag = "deploy_start_from_server"
        os.environ['TEMPLATE'] = template.strip()
        os.environ['VARIABLES'] = variables.strip()
        self.app.logger.debug({"msg": {"template_file": os.environ.get('TEMPLATE')}})
        self.app.logger.debug({"msg": {"variables_file": os.environ.get('VARIABLES')}})
        token = token_hex(8)
        dir = f"{Constants.DEPLOY_FOLDER_PATH}{token}"
        file = f"{dir}/{token}"

        try:
            r = Render(os.environ.get('TEMPLATE'), os.environ.get('VARIABLES'))
            IOUtils.create_dir(dir)
            IOUtils.write_to_file(file)
            IOUtils.write_to_file(file, r.rend_template())
            status = kubectl_utils.up(f"{file}")
            self.fluentd_utils.emit(fluentd_tag, {"msg": status})
            if status.get('err'):
                return Response(json.dumps(http.failure(Constants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE),
                                                        status.get('err'),
                                                        str(traceback.format_exc()))), 404,
                                mimetype="application/json")
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

    @route('/deploystop/<deployment>', methods=['GET'])
    def deploy_stop(self, deployment):
        deployment = deployment.strip()
        kubectl_utils = KubectlUtils()
        http = HttpResponse()
        header_key = 'K8s-Namespace'
        fluentd_tag = "deploy_stop"

        try:
            namespace = "default"
            if request.headers.get(f"{header_key}"):
                namespace = request.headers.get(f"{header_key}")
            status = kubectl_utils.down(deployment, namespace)
            self.fluentd_utils.emit(fluentd_tag, {"msg": status})
            if "Error from server".lower() in status.get('err').lower():
                return Response(json.dumps(http.failure(Constants.KUBERNETES_SERVER_ERROR,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.KUBERNETES_SERVER_ERROR) % status.get('err'),
                                                        status.get('err'),
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
            result = status.get('out').split("\n")[1:-1]
            response = Response(
                json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result)), 200,
                mimetype="application/json")
        except:
            result = "Exception({0})".format(sys.exc_info()[0])
            response = Response(json.dumps(http.failure(Constants.DEPLOY_STOP_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_STOP_FAILURE), result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/deploystatus/<deployment>', methods=['GET'])
    def deploy_status(self, deployment):
        deployment = deployment.strip()
        kubectl_utils = KubectlUtils()
        http = HttpResponse()
        try:
            deployment = kubectl_utils.get_active_deployment(deployment)
            response = Response(
                json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS),
                                        deployment)), 200,
                mimetype="application/json")
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

    @route('/getfile', methods=['GET', 'POST'])
    def get_file(self):
        http = HttpResponse()
        header_key = 'File-Path'

        file_path = request.headers.get(f"{header_key}")
        if not file_path:
            return Response(json.dumps(http.failure(Constants.HTTP_HEADER_NOT_PROVIDED,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        Constants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        Constants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        try:
            result = Response(IOUtils.read_file(file_path), 200, mimetype="text/plain")
        except:
            exception = "Exception({0})".format(sys.exc_info()[0])
            result = Response(json.dumps(http.failure(Constants.GET_FILE_FAILURE,
                                                      ErrorCodes.HTTP_CODE.get(
                                                          Constants.GET_FILE_FAILURE),
                                                      exception,
                                                      str(traceback.format_exc()))), 404, mimetype="application/json")
        return result

    @route('/deploylogs/<deployment>', methods=['GET'])
    def deploy_logs(self, deployment):
        deployment = deployment.strip()
        kubectl_utils = KubectlUtils()
        http = HttpResponse()
        header_key = 'K8s-Namespace'

        try:
            namespace = "default"
            if request.headers.get(f"{header_key}"):
                namespace = request.headers.get(f"{header_key}")
            status = kubectl_utils.logs(deployment, namespace)
            if status.get('err'):
                return Response(json.dumps(http.failure(Constants.GET_LOGS_FAILED,
                                                        status,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.GET_LOGS_FAILED) % deployment,
                                                        status.get('err'))), 404, mimetype="application/json")
        except:
            exception = "Exception({0})".format(sys.exc_info()[0])
            return Response(json.dumps(http.failure(Constants.GET_LOGS_FAILED,
                                                    ErrorCodes.HTTP_CODE.get(Constants.GET_LOGS_FAILED) % deployment,
                                                    exception,
                                                    exception)), 404, mimetype="application/json")

        return Response(
            json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS),
                                    status.get('out'))),
            200, mimetype="application/json")

    @route('/uploadfile', methods=['POST'])
    def upload_file(self):
        io_utils = IOUtils()
        http = HttpResponse()
        header_key = 'File-Path'
        try:
            file_content = request.get_data()
            file_path = request.headers.get(f"{header_key}")
            if not file_path:
                return Response(json.dumps(http.failure(Constants.HTTP_HEADER_NOT_PROVIDED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
            if not file_content:
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
            io_utils.write_to_file_binary(file_path, file_content)
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

    @route('/executecommand', methods=['POST'])
    def execute_command(self):
        io_utils = IOUtils()
        cmd_utils = CmdUtils()
        http = HttpResponse()
        info_init = {"command": {}}

        input_data = request.data.decode('utf-8').strip()
        if not input_data:
            return Response(json.dumps(http.failure(Constants.EMPTY_REQUEST_BODY_PROVIDED,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        Constants.EMPTY_REQUEST_BODY_PROVIDED),
                                                    ErrorCodes.HTTP_CODE.get(
                                                        Constants.EMPTY_REQUEST_BODY_PROVIDED),
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        try:
            cmd = io_utils.get_filtered_list_regex(input_data.split("\n")[0:1], re.compile(
                r'(\s+|[^a-z]|^)rm\s+.*$'))  # supports only one command at a time
            if not cmd:
                return Response(json.dumps(http.failure(Constants.EXEC_COMMAND_NOT_ALLOWED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.EXEC_COMMAND_NOT_ALLOWED) % input_data,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.EXEC_COMMAND_NOT_ALLOWED) % input_data,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
            command_dict = dict.fromkeys(cmd, {"details": {}})
            info_init["command"] = command_dict
            status = cmd_utils.run_cmd(["bash", "-c", f'''{cmd[0]}'''])
            info_init["command"][cmd[0]]["details"] = json.loads(json.dumps(status))
        except Exception as e:
            exception = "Exception({0})".format(e.__str__())
            return Response(json.dumps(http.failure(Constants.COMMAND_EXEC_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(Constants.COMMAND_EXEC_FAILURE) % cmd[0],
                                                    exception,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")

        return Response(
            json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), info_init)),
            200,
            mimetype="application/json")

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
from rest.api.apiresponsehelpers.error_codes import ErrorCodes
from rest.api.apiresponsehelpers.http_response import HttpResponse
from rest.api.constants.api_constants import ApiConstants
from rest.api.constants.env_constants import EnvConstants
from rest.api.definitions import kubectl_swagger_file_content, unmodifiable_env_vars
from rest.api.flask_config import Config
from rest.api.logginghelpers.message_dumper import MessageDumper
from rest.utils.cmd_utils import CmdUtils
from rest.utils.fluentd_utils import FluentdUtils
from rest.utils.io_utils import IOUtils
from rest.utils.kubectl_utils import KubectlUtils


class KubectlView(FlaskView):

    def __init__(self):
        self.app = Flask(__name__, instance_relative_config=False)
        self.app.config.from_object(Config)
        CORS(self.app)
        self.app.register_blueprint(self.get_swagger_blueprint(), url_prefix='/kubectl/api/docs')
        self.app.logger.setLevel(logging.DEBUG)
        self.logger = sender.FluentSender(properties.get('name'), host=properties["fluentd_ip"],
                                          port=int(properties["fluentd_port"]))
        self.fluentd_utils = FluentdUtils(self.logger)
        self.message_dumper = MessageDumper()

    def before_request(self, name, *args, **kwargs):
        ctx = self.app.app_context()
        ctx.g.xid = token_hex(8)
        http = HttpResponse()
        request_uri = request.environ.get("REQUEST_URI")
        # add here your custom header to be logged with fluentd
        self.message_dumper.set_header("X-Request-ID", request.headers.get('X-Request-ID') if request.headers.get(
            'X-Request-ID') else ctx.g.xid)
        self.message_dumper.set_header("Request-Uri", request_uri)

        response = self.fluentd_utils.debug(tag="api", msg=self.message_dumper.dump(request=request))
        self.app.logger.debug(f"{response}")
        if not str(request.headers.get("Token")) == str(os.environ.get("HTTP_AUTH_TOKEN")):
            if not ("/api/docs" in request_uri or "/swagger/swagger.yml" in request_uri):  # exclude swagger
                headers = {
                    'X-Request-ID': self.message_dumper.get_header("X-Request-ID")
                }
                return Response(json.dumps(http.failure(ApiConstants.UNAUTHORIZED,
                                                        ErrorCodes.HTTP_CODE.get(ApiConstants.UNAUTHORIZED),
                                                        "Invalid Token",
                                                        str(traceback.format_exc()))), 401, mimetype="application/json",
                                headers=headers)

    def after_request(self, name, http_response):
        headers = dict(http_response.headers)
        headers['X-Request-ID'] = self.message_dumper.get_header("X-Request-ID")
        http_response.headers = headers

        response = self.fluentd_utils.debug(tag="api", msg=self.message_dumper.dump(http_response))
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
        return Response(kubectl_swagger_file_content, 200, mimetype="text/plain;charset=UTF-8")

    @route('/env')
    def get_env_vars(self):
        http = HttpResponse()
        return Response(
            json.dumps(
                http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), dict(os.environ))),
            200, mimetype="application/json")

    @route('/ping')
    def ping(self):
        http = HttpResponse()
        return Response(
            json.dumps(http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), "pong")),
            200, mimetype="application/json")

    @route('/about')
    def about(self):
        http = HttpResponse()
        return Response(
            json.dumps(
                http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), properties["name"])),
            200, mimetype="application/json")

    @route('/env/<env_var>', methods=['GET'])
    def get_env_var(self, env_var):
        env_var = env_var.upper().strip()
        http = HttpResponse()
        try:
            response = Response(json.dumps(
                http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                             os.environ[env_var])),
                200,
                mimetype="application/json")
        except Exception as e:
            result = "Exception({0})".format(e.__str__())
            response = Response(json.dumps(http.failure(ApiConstants.GET_CONTAINER_ENV_VAR_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.GET_CONTAINER_ENV_VAR_FAILURE) % env_var,
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
        return response

    @route('/render/<template>/<variables>', methods=['GET', 'POST'])
    def get_content_with_env(self, template, variables):
        try:
            input_json = request.get_json(force=True)
            for key, value in input_json.items():
                if key not in unmodifiable_env_vars:
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
            response = Response(json.dumps(http.failure(ApiConstants.JINJA2_RENDER_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(ApiConstants.JINJA2_RENDER_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/deployments', methods=['GET'])
    def get_deployment_info(self):
        kubectl_utils = KubectlUtils()
        http = HttpResponse()
        header_keys = ["Label-Selector", 'K8s-Namespace']

        for header_key in header_keys:
            if not request.headers.get(f"{header_key}"):
                return Response(json.dumps(http.failure(ApiConstants.HTTP_HEADER_NOT_PROVIDED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                        str(traceback.format_exc()))), 404,
                                mimetype="application/json")
        label_selector = request.headers.get(f"{header_keys[0]}")
        namespace = request.headers.get(f"{header_keys[1]}")
        active_pods = kubectl_utils.get_active_pods(label_selector, namespace)
        self.app.logger.debug({"msg": {"active_deployments": f"{len(active_pods)}"}})
        return Response(
            json.dumps(
                http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), active_pods)),
            200, mimetype="application/json")

    @route('/deployments', methods=['POST'])
    def deploy_start(self):
        kubectl_utils = KubectlUtils()
        http = HttpResponse()
        fluentd_tag = "deploy_start"
        token = token_hex(8)
        deploy_dir = f"{EnvConstants.DEPLOY_PATH}/{token}"
        file = f"{deploy_dir}/{token}"

        try:
            IOUtils.create_dir(deploy_dir)
            input_data = request.data.decode('utf-8')
            IOUtils.write_to_file(file, input_data)
            status = kubectl_utils.up(f"{file}")
            self.fluentd_utils.emit(fluentd_tag, {"msg": status})
            if status.get('err'):
                return Response(json.dumps(http.failure(ApiConstants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_START_FAILURE),
                                                        status.get('err'),
                                                        str(traceback.format_exc()))), 404,
                                mimetype="application/json")
            response = Response(
                json.dumps(http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), token)),
                200,
                mimetype="application/json")
        except OSError  as e:
            result = "Exception({0})".format(e.__str__())
            response = Response(json.dumps(http.failure(ApiConstants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_START_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
        except:
            result = "Exception({0})".format(sys.exc_info()[0])
            response = Response(json.dumps(http.failure(ApiConstants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_START_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/deployments/<template>/<variables>', methods=['POST'])
    def deploy_start_env(self, template, variables):
        http = HttpResponse()
        kubectl_utils = KubectlUtils()
        fluentd_tag = "deploy_start"
        try:
            input_json = request.get_json(force=True)
            for key, value in input_json.items():
                if key not in unmodifiable_env_vars:
                    os.environ[str(key)] = str(value)
        except:
            pass

        os.environ['TEMPLATE'] = template.strip()
        os.environ['VARIABLES'] = variables.strip()
        self.app.logger.debug({"msg": {"template_file": os.environ.get('TEMPLATE')}})
        self.app.logger.debug({"msg": {"variables_file": os.environ.get('VARIABLES')}})
        token = token_hex(8)
        deploy_dir = f"{EnvConstants.DEPLOY_PATH}/{token}"
        file = f"{deploy_dir}/{token}"

        try:
            r = Render(os.environ.get('TEMPLATE'), os.environ.get('VARIABLES'))
            IOUtils.create_dir(deploy_dir)
            IOUtils.write_to_file(file)
            IOUtils.write_to_file(file, r.rend_template())
            status = kubectl_utils.up(f"{file}")
            self.fluentd_utils.emit(fluentd_tag, {"msg": status})
            if status.get('err'):
                return Response(json.dumps(http.failure(ApiConstants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_START_FAILURE),
                                                        status.get('err'),
                                                        str(traceback.format_exc()))), 404,
                                mimetype="application/json")
            result = str(token)
            response = Response(
                json.dumps(http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), result)),
                200,
                mimetype="application/json")
        except OSError  as e:
            result = "Exception({0})".format(e.__str__())
            response = Response(json.dumps(http.failure(ApiConstants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_START_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
        except:
            result = "Exception({0})".format(sys.exc_info()[0])
            response = Response(json.dumps(http.failure(ApiConstants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_START_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/deployments/<deployment>', methods=['DELETE'])
    def deploy_stop(self, deployment):
        deployment = deployment.strip()
        kubectl_utils = KubectlUtils()
        http = HttpResponse()
        header_key = 'K8s-Namespace'
        fluentd_tag = "deploy_stop"

        if not request.headers.get(f"{header_key}"):
            return Response(json.dumps(http.failure(ApiConstants.HTTP_HEADER_NOT_PROVIDED,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                    str(traceback.format_exc()))), 404,
                            mimetype="application/json")

        try:
            namespace = request.headers.get(f"{header_key}")
            status = kubectl_utils.down(deployment, namespace)
            self.fluentd_utils.emit(fluentd_tag, {"msg": status})
            if "Error from server".lower() in status.get('err').lower():
                return Response(json.dumps(http.failure(ApiConstants.KUBERNETES_SERVER_ERROR,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.KUBERNETES_SERVER_ERROR) % status.get('err'),
                                                        status.get('err'),
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
            result = status.get('out').split("\n")[1:-1]
            response = Response(
                json.dumps(http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), result)),
                200,
                mimetype="application/json")
        except:
            result = "Exception({0})".format(sys.exc_info()[0])
            response = Response(json.dumps(http.failure(ApiConstants.DEPLOY_STOP_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_STOP_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/deployments/<pod>', methods=['GET'])
    def deploy_status(self, pod):
        pod = pod.strip()
        kubectl_utils = KubectlUtils()
        http = HttpResponse()
        header_keys = ["Label-Selector", 'K8s-Namespace']

        for header_key in header_keys:
            if not request.headers.get(f"{header_key}"):
                return Response(json.dumps(http.failure(ApiConstants.HTTP_HEADER_NOT_PROVIDED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                        str(traceback.format_exc()))), 404,
                                mimetype="application/json")

        try:
            label_selector = request.headers.get(f"{header_keys[0]}")
            namespace = request.headers.get(f"{header_keys[1]}")
            deployment = kubectl_utils.get_active_pod(pod, label_selector, namespace)
            response = Response(
                json.dumps(http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                                        deployment)), 200,
                mimetype="application/json")
        except OSError as e:
            result = "Exception({0})".format(e.__str__())
            response = Response(json.dumps(http.failure(ApiConstants.DEPLOY_STATUS_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_STATUS_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
        except:
            result = "Exception({0})".format(sys.exc_info()[0])
            response = Response(json.dumps(http.failure(ApiConstants.DEPLOY_STATUS_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_STATUS_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/file', methods=['POST', 'PUT'])
    def upload_file(self):
        io_utils = IOUtils()
        http = HttpResponse()
        header_key = 'File-Path'
        try:
            file_content = request.get_data()
            file_path = request.headers.get(f"{header_key}")
            if not file_path:
                return Response(json.dumps(http.failure(ApiConstants.HTTP_HEADER_NOT_PROVIDED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
            if not file_content:
                return Response(json.dumps(http.failure(ApiConstants.EMPTY_REQUEST_BODY_PROVIDED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.EMPTY_REQUEST_BODY_PROVIDED),
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.EMPTY_REQUEST_BODY_PROVIDED),
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
        except Exception as e:
            exception = "Exception({0})".format(e.__str__())
            return Response(json.dumps(http.failure(ApiConstants.UPLOAD_FILE_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(ApiConstants.UPLOAD_FILE_FAILURE),
                                                    exception,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        try:
            io_utils.write_to_file_binary(file_path, file_content)
        except Exception as e:
            exception = "Exception({0})".format(e.__str__())
            return Response(json.dumps(http.failure(ApiConstants.UPLOAD_FILE_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(ApiConstants.UPLOAD_FILE_FAILURE),
                                                    exception,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")

        return Response(json.dumps(http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                                                ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS))),
                        200,
                        mimetype="application/json")

    @route('/file', methods=['GET'])
    def get_file(self):
        http = HttpResponse()
        header_key = 'File-Path'

        file_path = request.headers.get(f"{header_key}")
        if not file_path:
            return Response(json.dumps(http.failure(ApiConstants.HTTP_HEADER_NOT_PROVIDED,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        try:
            result = Response(IOUtils.read_file(file_path), 200, mimetype="text/plain")
        except:
            exception = "Exception({0})".format(sys.exc_info()[0])
            result = Response(json.dumps(http.failure(ApiConstants.GET_FILE_FAILURE,
                                                      ErrorCodes.HTTP_CODE.get(
                                                          ApiConstants.GET_FILE_FAILURE),
                                                      exception,
                                                      str(traceback.format_exc()))), 404, mimetype="application/json")
        return result

    @route('/deployments/logs/<deployment>', methods=['GET'])
    def deploy_logs(self, deployment):
        deployment = deployment.strip()
        kubectl_utils = KubectlUtils()
        http = HttpResponse()
        header_key = 'K8s-Namespace'

        if not request.headers.get(f"{header_key}"):
            return Response(json.dumps(http.failure(ApiConstants.HTTP_HEADER_NOT_PROVIDED,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                    str(traceback.format_exc()))), 404,
                            mimetype="application/json")

        try:
            if request.headers.get(f"{header_key}"):
                namespace = request.headers.get(f"{header_key}")
            status = kubectl_utils.logs(deployment, namespace)
            if status.get('err'):
                return Response(json.dumps(http.failure(ApiConstants.GET_LOGS_FAILED,
                                                        status,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.GET_LOGS_FAILED) % deployment,
                                                        status.get('err'))), 404, mimetype="application/json")
        except:
            exception = "Exception({0})".format(sys.exc_info()[0])
            return Response(json.dumps(http.failure(ApiConstants.GET_LOGS_FAILED,
                                                    ErrorCodes.HTTP_CODE.get(ApiConstants.GET_LOGS_FAILED) % deployment,
                                                    exception,
                                                    exception)), 404, mimetype="application/json")

        return Response(
            json.dumps(http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                                    status.get('out'))),
            200, mimetype="application/json")

    @route('/command', methods=['POST', 'PUT'])
    def execute_command(self):
        io_utils = IOUtils()
        cmd_utils = CmdUtils()
        http = HttpResponse()
        info_init = {"command": {}}

        input_data = request.data.decode('utf-8').strip()
        if not input_data:
            return Response(json.dumps(http.failure(ApiConstants.EMPTY_REQUEST_BODY_PROVIDED,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        ApiConstants.EMPTY_REQUEST_BODY_PROVIDED),
                                                    ErrorCodes.HTTP_CODE.get(
                                                        ApiConstants.EMPTY_REQUEST_BODY_PROVIDED),
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        try:
            cmd = io_utils.get_filtered_list_regex(input_data.split("\n"), re.compile(
                r'(\s+|[^a-z]|^)rm\s+.*$'))[0:1]  # supports only one command at a time
            if not cmd:
                return Response(json.dumps(http.failure(ApiConstants.EXEC_COMMAND_NOT_ALLOWED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.EXEC_COMMAND_NOT_ALLOWED) % input_data,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.EXEC_COMMAND_NOT_ALLOWED) % input_data,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
            command_dict = dict.fromkeys(cmd, {"details": {}})
            info_init["command"] = command_dict
            status = cmd_utils.run_cmd_shell_true(cmd[0].strip())
            info_init["command"][cmd[0].strip()]["details"] = json.loads(json.dumps(status))
        except Exception as e:
            exception = "Exception({0})".format(e.__str__())
            return Response(json.dumps(http.failure(ApiConstants.COMMAND_EXEC_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(ApiConstants.COMMAND_EXEC_FAILURE) % cmd[
                                                        0],
                                                    exception,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")

        return Response(
            json.dumps(http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), info_init)),
            200,
            mimetype="application/json")

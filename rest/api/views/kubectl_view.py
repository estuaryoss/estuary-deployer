import json
import os
import re
from secrets import token_hex

from flask import request, Response
from flask_classful import FlaskView, route
from fluent import sender

from about import properties
from entities.render import Render
from rest.api.constants.api_constants import ApiConstants
from rest.api.constants.env_constants import EnvConstants
from rest.api.constants.env_init import EnvInit
from rest.api.constants.header_constants import HeaderConstants
from rest.api.definitions import unmodifiable_env_vars
from rest.api.kubectl_swagger import kubectl_swagger_file_content
from rest.api.loghelpers.message_dumper import MessageDumper
from rest.api.responsehelpers.error_codes import ErrorCodes
from rest.api.responsehelpers.http_response import HttpResponse
from rest.api.views import app
from rest.service.fluentd import Fluentd
from rest.utils.cmd_utils import CmdUtils
from rest.utils.env_startup import EnvStartup
from rest.utils.io_utils import IOUtils
from rest.utils.kubectl_utils import KubectlUtils


class KubectlView(FlaskView):
    logger = \
        sender.FluentSender(tag=properties.get('name'),
                            host=EnvStartup.get_instance().get(EnvConstants.FLUENTD_IP_PORT).split(":")[0],
                            port=int(EnvStartup.get_instance().get(EnvConstants.FLUENTD_IP_PORT).split(":")[1])) \
            if EnvStartup.get_instance().get(EnvConstants.FLUENTD_IP_PORT) else None
    fluentd = Fluentd(logger)
    message_dumper = MessageDumper()

    def before_request(self, name, *args, **kwargs):
        ctx = app.app_context()
        ctx.g.xid = token_hex(8)
        http = HttpResponse()
        request_uri = request.full_path
        # add here your custom header to be logged with fluentd
        self.message_dumper.set_header(HeaderConstants.X_REQUEST_ID,
                                       request.headers.get(HeaderConstants.X_REQUEST_ID) if request.headers.get(
                                           HeaderConstants.X_REQUEST_ID) else ctx.g.xid)
        self.message_dumper.set_header(HeaderConstants.REQUEST_URI, request_uri)

        response = self.fluentd.emit(tag="api", msg=self.message_dumper.dump(request=request))
        app.logger.debug(f"{response}")
        if not str(request.headers.get(HeaderConstants.TOKEN)) == str(
                EnvStartup.get_instance().get(EnvConstants.HTTP_AUTH_TOKEN)):
            if not ("/api/docs" in request_uri or "/swagger/swagger.yml" in request_uri):  # exclude swagger
                headers = {
                    HeaderConstants.X_REQUEST_ID: self.message_dumper.get_header(HeaderConstants.X_REQUEST_ID)
                }
                return Response(json.dumps(http.response(ApiConstants.UNAUTHORIZED,
                                                         ErrorCodes.HTTP_CODE.get(ApiConstants.UNAUTHORIZED),
                                                         "Invalid Token")), 401, mimetype="application/json",
                                headers=headers)

    def after_request(self, name, http_response):
        headers = dict(http_response.headers)
        headers[HeaderConstants.X_REQUEST_ID] = self.message_dumper.get_header(HeaderConstants.X_REQUEST_ID)
        http_response.headers = headers

        http_response.direct_passthrough = False
        response = self.fluentd.emit(tag="api", msg=self.message_dumper.dump(http_response))
        app.logger.debug(f"{response}")

        return http_response

    def index(self):
        return "kubectl"

    @route('/swagger/swagger.yml')
    def swagger(self):
        return Response(kubectl_swagger_file_content, 200, mimetype="text/plain;charset=UTF-8")

    @route('/env')
    def get_env_vars(self):
        http = HttpResponse()
        return Response(
            json.dumps(
                http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), dict(os.environ))),
            200, mimetype="application/json")

    @route('/ping')
    def ping(self):
        http = HttpResponse()
        return Response(
            json.dumps(http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), "pong")),
            200, mimetype="application/json")

    @route('/about')
    def about(self):
        http = HttpResponse()
        return Response(
            json.dumps(
                http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                              properties["name"])),
            200, mimetype="application/json")

    @route('/env/<env_var>', methods=['GET'])
    def get_env_var(self, env_var):
        http = HttpResponse()
        env_var = env_var.upper().strip()
        try:
            response = Response(json.dumps(
                http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                              os.environ[env_var])),
                200,
                mimetype="application/json")
        except Exception as e:
            result = "Exception({})".format(e.__str__())
            response = Response(json.dumps(http.response(ApiConstants.GET_CONTAINER_ENV_VAR_FAILURE,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.GET_CONTAINER_ENV_VAR_FAILURE) % env_var,
                                                         result)), 404, mimetype="application/json")
        return response

    @route('/render/<template>/<variables>', methods=['GET', 'POST'])
    def get_content_with_env(self, template, variables):
        http = HttpResponse()
        try:
            input_json = request.get_json(force=True)
            for key, value in input_json.items():
                if key not in unmodifiable_env_vars:
                    os.environ[str(key)] = str(value)
        except:
            pass

        os.environ[EnvConstants.TEMPLATE] = template.strip()
        os.environ[EnvConstants.VARIABLES] = variables.strip()

        try:
            rendered_content = Render(os.environ.get(EnvConstants.TEMPLATE), os.environ.get(EnvConstants.VARIABLES)).rend_template()
        except Exception as e:
            return Response(json.dumps(http.response(ApiConstants.JINJA2_RENDER_FAILURE,
                                                     ErrorCodes.HTTP_CODE.get(ApiConstants.JINJA2_RENDER_FAILURE),
                                                     "Exception({})".format(e.__str__()))), 404,
                            mimetype="application/json")

        return Response(rendered_content, 200, mimetype="text/plain")

    @route('/deployments', methods=['GET'])
    def get_deployment_info(self):
        http = HttpResponse()
        kubectl_utils = KubectlUtils()
        header_keys = ["Label-Selector", 'K8s-Namespace']

        for header_key in header_keys:
            if not request.headers.get(f"{header_key}"):
                return Response(json.dumps(http.response(ApiConstants.HTTP_HEADER_NOT_PROVIDED,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key)), 404,
                                mimetype="application/json")
        label_selector = request.headers.get(f"{header_keys[0]}")
        namespace = request.headers.get(f"{header_keys[1]}")
        active_pods = kubectl_utils.get_active_pods(label_selector, namespace)
        app.logger.debug({"msg": {"active_deployments": f"{len(active_pods)}"}})
        return Response(
            json.dumps(
                http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), active_pods)),
            200, mimetype="application/json")

    @route('/deployments', methods=['POST'])
    def deploy_start(self):
        http = HttpResponse()
        kubectl_utils = KubectlUtils()
        fluentd_tag = "deploy_start"
        token = token_hex(8)
        deploy_dir = f"{EnvInit.DEPLOY_PATH}/{token}"
        file = f"{deploy_dir}/{token}"

        try:
            IOUtils.create_dir(deploy_dir)
            input_data = request.data.decode('utf-8')
            IOUtils.write_to_file(file, input_data)
            status = kubectl_utils.up(f"{file}")
            self.fluentd.emit(tag=fluentd_tag, msg={"msg": status})
            if status.get('err'):
                return Response(json.dumps(http.response(ApiConstants.DEPLOY_START_FAILURE,
                                                         ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_START_FAILURE),
                                                         status.get('err'))), 404,
                                mimetype="application/json")
        except Exception as e:
            return Response(json.dumps(http.response(ApiConstants.DEPLOY_START_FAILURE,
                                                     ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_START_FAILURE),
                                                     "Exception({})".format(e.__str__()))), 404,
                            mimetype="application/json")

        return Response(
            json.dumps(http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), token)),
            200,
            mimetype="application/json")

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

        os.environ[EnvConstants.TEMPLATE] = template.strip()
        os.environ[EnvConstants.VARIABLES] = variables.strip()
        app.logger.debug({"msg": {"template_file": os.environ.get(EnvConstants.TEMPLATE)}})
        app.logger.debug({"msg": {"variables_file": os.environ.get(EnvConstants.VARIABLES)}})
        token = token_hex(8)
        deploy_dir = f"{EnvInit.DEPLOY_PATH}/{token}"
        file = f"{deploy_dir}/{token}"

        try:
            r = Render(os.environ.get(EnvConstants.TEMPLATE), os.environ.get(EnvConstants.VARIABLES))
            IOUtils.create_dir(deploy_dir)
            IOUtils.write_to_file(file)
            IOUtils.write_to_file(file, r.rend_template())
            status = kubectl_utils.up(f"{file}")
            self.fluentd.emit(tag=fluentd_tag, msg={"msg": status})
            if status.get('err'):
                return Response(json.dumps(http.response(ApiConstants.DEPLOY_START_FAILURE,
                                                         ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_START_FAILURE),
                                                         status.get('err'))), 404, mimetype="application/json")
            result = str(token)
        except Exception as e:
            return Response(json.dumps(http.response(ApiConstants.DEPLOY_START_FAILURE,
                                                     ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_START_FAILURE),
                                                     "Exception({})".format(e.__str__()))), 404,
                            mimetype="application/json")

        return Response(
            json.dumps(http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), result)),
            200,
            mimetype="application/json")

    @route('/deployments/<deployment>', methods=['DELETE'])
    def deploy_stop(self, deployment):
        http = HttpResponse()
        deployment = deployment.strip()
        kubectl_utils = KubectlUtils()
        header_key = 'K8s-Namespace'
        fluentd_tag = "deploy_stop"

        if not request.headers.get(f"{header_key}"):
            return Response(json.dumps(http.response(ApiConstants.HTTP_HEADER_NOT_PROVIDED,
                                                     ErrorCodes.HTTP_CODE.get(
                                                         ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                     ErrorCodes.HTTP_CODE.get(
                                                         ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key)), 404,
                            mimetype="application/json")

        try:
            namespace = request.headers.get(f"{header_key}")
            status = kubectl_utils.down(deployment, namespace)
            self.fluentd.emit(tag=fluentd_tag, msg={"msg": status})
            if "Error from server".lower() in status.get('err').lower():
                return Response(json.dumps(http.response(ApiConstants.KUBERNETES_SERVER_ERROR,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.KUBERNETES_SERVER_ERROR) % status.get('err'),
                                                         status.get('err'))), 404, mimetype="application/json")
            result = status.get('out').split("\n")[1:-1]
        except Exception as e:
            return Response(json.dumps(http.response(ApiConstants.DEPLOY_STOP_FAILURE,
                                                     ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_STOP_FAILURE),
                                                     "Exception({})".format(e.__str__()))), 404,
                            mimetype="application/json")

        return Response(
            json.dumps(http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), result)),
            200,
            mimetype="application/json")

    @route('/deployments/<pod>', methods=['GET'])
    def deploy_status(self, pod):
        http = HttpResponse()
        pod = pod.strip()
        kubectl_utils = KubectlUtils()
        header_keys = ["Label-Selector", 'K8s-Namespace']

        for header_key in header_keys:
            if not request.headers.get(f"{header_key}"):
                return Response(json.dumps(http.response(ApiConstants.HTTP_HEADER_NOT_PROVIDED,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key)), 404,
                                mimetype="application/json")

        try:
            label_selector = request.headers.get(f"{header_keys[0]}")
            namespace = request.headers.get(f"{header_keys[1]}")
            deployment = kubectl_utils.get_active_pod(pod, label_selector, namespace)
        except Exception as e:
            return Response(json.dumps(http.response(ApiConstants.DEPLOY_STATUS_FAILURE,
                                                     ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_STATUS_FAILURE),
                                                     "Exception({})".format(e.__str__()))), 404,
                            mimetype="application/json")

        return Response(
            json.dumps(http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                                     deployment)), 200,
            mimetype="application/json")

    @route('/file', methods=['POST', 'PUT'])
    def upload_file(self):
        http = HttpResponse()
        io_utils = IOUtils()
        header_key = 'File-Path'
        try:
            file_content = request.get_data()
            file_path = request.headers.get(f"{header_key}")
            if not file_path:
                return Response(json.dumps(http.response(ApiConstants.HTTP_HEADER_NOT_PROVIDED,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key)), 404,
                                mimetype="application/json")
            if not file_content:
                return Response(json.dumps(http.response(ApiConstants.EMPTY_REQUEST_BODY_PROVIDED,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.EMPTY_REQUEST_BODY_PROVIDED),
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.EMPTY_REQUEST_BODY_PROVIDED))), 404,
                                mimetype="application/json")
            io_utils.write_to_file_binary(file_path, file_content)
        except Exception as e:
            return Response(json.dumps(http.response(ApiConstants.UPLOAD_FILE_FAILURE,
                                                     ErrorCodes.HTTP_CODE.get(ApiConstants.UPLOAD_FILE_FAILURE),
                                                     "Exception({})".format(e.__str__()))), 404,
                            mimetype="application/json")

        return Response(json.dumps(http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                                                 ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS))),
                        200,
                        mimetype="application/json")

    @route('/file', methods=['GET'])
    def get_file(self):
        http = HttpResponse()
        header_key = 'File-Path'

        file_path = request.headers.get(f"{header_key}")
        if not file_path:
            return Response(json.dumps(http.response(ApiConstants.HTTP_HEADER_NOT_PROVIDED,
                                                     ErrorCodes.HTTP_CODE.get(
                                                         ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                     ErrorCodes.HTTP_CODE.get(
                                                         ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key)), 404,
                            mimetype="application/json")
        try:
            file_content = IOUtils.read_file(file_path)
        except Exception as e:
            return Response(json.dumps(http.response(ApiConstants.GET_FILE_FAILURE,
                                                     ErrorCodes.HTTP_CODE.get(
                                                         ApiConstants.GET_FILE_FAILURE),
                                                     "Exception({})".format(e.__str__()))), 404,
                            mimetype="application/json")
        return Response(file_content, 200, mimetype="text/plain")

    @route('/deployments/logs/<deployment>', methods=['GET'])
    def deploy_logs(self, deployment):
        http = HttpResponse()
        kubectl_utils = KubectlUtils()
        deployment = deployment.strip()
        header_key = 'K8s-Namespace'

        if not request.headers.get(f"{header_key}"):
            return Response(json.dumps(http.response(ApiConstants.HTTP_HEADER_NOT_PROVIDED,
                                                     ErrorCodes.HTTP_CODE.get(
                                                         ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                     ErrorCodes.HTTP_CODE.get(
                                                         ApiConstants.HTTP_HEADER_NOT_PROVIDED) % header_key)), 404,
                            mimetype="application/json")

        try:
            if request.headers.get(f"{header_key}"):
                namespace = request.headers.get(f"{header_key}")
            status = kubectl_utils.logs(deployment, namespace)
            if status.get('err'):
                return Response(json.dumps(http.response(ApiConstants.GET_LOGS_FAILED,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.GET_LOGS_FAILED) % deployment,
                                                         status)), 404, mimetype="application/json")
        except Exception as e:
            return Response(json.dumps(http.response(ApiConstants.GET_LOGS_FAILED,
                                                     ErrorCodes.HTTP_CODE.get(
                                                         ApiConstants.GET_LOGS_FAILED) % deployment,
                                                     "Exception({})".format(e.__str__()))), 404,
                            mimetype="application/json")

        return Response(
            json.dumps(http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                                     status.get('out'))),
            200, mimetype="application/json")

    @route('/command', methods=['POST', 'PUT'])
    def execute_command(self):
        http = HttpResponse()
        io_utils = IOUtils()
        cmd_utils = CmdUtils()
        info_init = {"command": {}}

        input_data = request.data.decode('utf-8').strip()
        if not input_data:
            return Response(json.dumps(http.response(ApiConstants.EMPTY_REQUEST_BODY_PROVIDED,
                                                     ErrorCodes.HTTP_CODE.get(
                                                         ApiConstants.EMPTY_REQUEST_BODY_PROVIDED),
                                                     ErrorCodes.HTTP_CODE.get(
                                                         ApiConstants.EMPTY_REQUEST_BODY_PROVIDED))), 404,
                            mimetype="application/json")
        try:
            cmd = io_utils.get_filtered_list_regex(input_data.split("\n"), re.compile(
                r'(\s+|[^a-z]|^)rm\s+.*$'))[0:1]  # supports only one command at a time
            if not cmd:
                return Response(json.dumps(http.response(ApiConstants.EXEC_COMMAND_NOT_ALLOWED,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.EXEC_COMMAND_NOT_ALLOWED) % input_data,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.EXEC_COMMAND_NOT_ALLOWED) % input_data)), 404,
                                mimetype="application/json")
            command_dict = dict.fromkeys(cmd, {"details": {}})
            info_init["command"] = command_dict
            status = cmd_utils.run_cmd_shell_true(cmd[0].strip())
            info_init["command"][cmd[0].strip()]["details"] = json.loads(json.dumps(status))
        except Exception as e:
            return Response(json.dumps(
                http.response(ApiConstants.COMMAND_EXEC_FAILURE,
                              ErrorCodes.HTTP_CODE.get(ApiConstants.COMMAND_EXEC_FAILURE) % cmd[0],
                              "Exception({})".format(e.__str__()))), 404, mimetype="application/json")

        return Response(
            json.dumps(http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), info_init)),
            200,
            mimetype="application/json")

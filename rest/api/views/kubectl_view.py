import json
from secrets import token_hex

from flask import request, Response, render_template, send_from_directory
from flask_classful import FlaskView, route
from fluent import sender
from werkzeug.utils import redirect

from about import properties, about_system
from rest.api.constants.api_code import ApiCode
from rest.api.constants.env_constants import EnvConstants
from rest.api.constants.env_init import EnvInit
from rest.api.constants.header_constants import HeaderConstants
from rest.api.exception.api_exception_kubectl import ApiExceptionKubectl
from rest.api.jinja2.render import Render
from rest.api.loghelpers.message_dumper import MessageDumper
from rest.api.responsehelpers.error_message import ErrorMessage
from rest.api.responsehelpers.http_response import HttpResponse
from rest.api.views import app
from rest.environment.environment import EnvironmentSingleton
from rest.service.fluentd import Fluentd
from rest.utils.command_in_memory import CommandInMemory
from rest.utils.env_startup import EnvStartupSingleton
from rest.utils.io_utils import IOUtils
from rest.utils.kubectl_utils import KubectlUtils


class KubectlView(FlaskView):
    logger = \
        sender.FluentSender(tag=properties.get('name'),
                            host=EnvStartupSingleton.get_instance().get_config_env_vars().get(
                                EnvConstants.FLUENTD_IP_PORT).split(":")[0],
                            port=int(EnvStartupSingleton.get_instance().get_config_env_vars().get(
                                EnvConstants.FLUENTD_IP_PORT).split(":")[1])) \
            if EnvStartupSingleton.get_instance().get_config_env_vars().get(EnvConstants.FLUENTD_IP_PORT) else None
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
                EnvStartupSingleton.get_instance().get_config_env_vars().get(EnvConstants.HTTP_AUTH_TOKEN)):
            if not ("/apidocs" in request_uri or "/swagger/swagger.json" in request_uri):  # exclude swagger
                headers = {
                    HeaderConstants.X_REQUEST_ID: self.message_dumper.get_header(HeaderConstants.X_REQUEST_ID)
                }
                return Response(json.dumps(http.response(ApiCode.UNAUTHORIZED.value,
                                                         ErrorMessage.HTTP_CODE.get(ApiCode.UNAUTHORIZED.value),
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

    @classmethod
    def handle_api_error(cls, e):
        http_response = Response(json.dumps(
            HttpResponse().response(code=e.code, message=e.message,
                                    description="Exception({})".format(e.exception.__str__()))),
            500, mimetype="application/json")
        http_response.headers[HeaderConstants.X_REQUEST_ID] = KubectlView.message_dumper.get_header(
            HeaderConstants.X_REQUEST_ID)
        response = KubectlView.fluentd.emit(tag="api", msg=KubectlView.message_dumper.dump(http_response))
        app.logger.debug(f"{response}")

        http_response.direct_passthrough = False
        return http_response

    def index(self):
        return render_template('index.html')

    @route('/apidocs')
    def send_swagger(self):
        return render_template('index.html')

    @route('/js/<path:path>')
    def send_js(self, path):
        return send_from_directory('swaggerui/js', path)

    @route('/css/<path:path>')
    def send_css(self, path):
        return send_from_directory('swaggerui/css', path)

    @route('/img/<path:path>')
    def send_img(self, path):
        return send_from_directory('swaggerui/img', path)

    @route('/swagger/swagger.json')
    def swagger(self):
        return render_template('swagger_kubectl.json')

    @route('/ping')
    def ping(self):
        return Response(
            json.dumps(HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                               "pong")),
            200, mimetype="application/json")

    @route('/about')
    def about(self):
        return Response(
            json.dumps(
                HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                        about_system)), 200, mimetype="application/json")

    @route('/env', methods=['GET'])
    def get_env_vars(self):
        return Response(
            json.dumps(
                HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                        EnvironmentSingleton.get_instance().get_env_and_virtual_env())),
            200, mimetype="application/json")

    @route('/env/<env_var>', methods=['GET'])
    def get_env_var(self, env_var):
        return Response(json.dumps(
            HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                    EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(env_var))),
            200, mimetype="application/json")

    @route('/env', methods=['POST'])
    def set_env(self):
        http = HttpResponse()
        input_data = request.data.decode("UTF-8", "replace").strip()

        try:
            env_vars_attempted = json.loads(input_data)
        except Exception as e:
            raise ApiExceptionKubectl(ApiCode.INVALID_JSON_PAYLOAD.value,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.INVALID_JSON_PAYLOAD.value) % str(input_data),
                                      e)

        try:
            env_vars_added = EnvironmentSingleton.get_instance().set_env_vars(env_vars_attempted)
        except Exception as e:
            raise ApiExceptionKubectl(
                ApiCode.SET_ENV_VAR_FAILURE.value, ErrorMessage.HTTP_CODE.get(ApiCode.SET_ENV_VAR_FAILURE.value) % str(
                    input_data), e)
        return Response(
            json.dumps(
                http.response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                              env_vars_added)), 200, mimetype="application/json")

    @route('/render/<template>/<variables>', methods=['GET', 'POST'])
    def get_content_with_env(self, template, variables):
        try:
            input_json = request.get_json(force=True)
            for key, value in input_json.items():
                if key not in EnvironmentSingleton.get_instance().get_env():
                    EnvironmentSingleton.get_instance().set_env_var(str(key), str(value))
        except Exception as e:
            app.logger.debug(f"Exception: {e.__str__}")

        EnvironmentSingleton.get_instance().set_env_var(EnvConstants.TEMPLATE, template.strip())
        EnvironmentSingleton.get_instance().set_env_var(EnvConstants.VARIABLES, variables.strip())

        try:
            rendered_content = Render(
                EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.TEMPLATE),
                EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
                    EnvConstants.VARIABLES)).rend_template()
        except Exception as e:
            raise ApiExceptionKubectl(ApiCode.JINJA2_RENDER_FAILURE.value,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.JINJA2_RENDER_FAILURE.value), e)

        return Response(rendered_content, 200, mimetype="text/plain")

    @route('/deployments', methods=['GET'])
    def get_deployment_info(self):
        http = HttpResponse()
        kubectl_utils = KubectlUtils()
        header_keys = ["Label-Selector", 'K8s-Namespace']

        for header_key in header_keys:
            if not request.headers.get(f"{header_key}"):
                raise ApiExceptionKubectl(ApiCode.HTTP_HEADER_NOT_PROVIDED.value,
                                          ErrorMessage.HTTP_CODE.get(
                                              ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % header_key,
                                          ErrorMessage.HTTP_CODE.get(
                                              ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % header_key)
        label_selector = request.headers.get(f"{header_keys[0]}")
        namespace = request.headers.get(f"{header_keys[1]}")
        active_pods = kubectl_utils.get_active_pods(label_selector, namespace)
        app.logger.debug({"msg": {"active_deployments": f"{len(active_pods)}"}})
        return Response(
            json.dumps(
                http.response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value), active_pods)),
            200, mimetype="application/json")

    @route('/deployments', methods=['POST'])
    def deploy_start(self):
        http = HttpResponse()
        kubectl_utils = KubectlUtils()
        fluentd_tag = "deploy_start"
        token = token_hex(8)
        deploy_dir = f"{EnvInit.DEPLOY_PATH}/{token}"
        file = f"{deploy_dir}/k8s-deployment.yml"

        try:
            IOUtils.create_dir(deploy_dir)
            input_data = request.data.decode('utf-8')
            IOUtils.write_to_file(file, input_data)
            status = kubectl_utils.up(f"{file}")
            self.fluentd.emit(tag=fluentd_tag, msg={"msg": status})
            if status.get('err'):
                raise Exception(status.get('err'))
        except Exception as e:
            raise ApiExceptionKubectl(ApiCode.DEPLOY_START_FAILURE.value,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.DEPLOY_START_FAILURE.value), e)

        return Response(
            json.dumps(http.response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value), token)),
            200, mimetype="application/json")

    @route('/deployments/<template>/<variables>', methods=['POST'])
    def start_deployment_with_template(self, template, variables):
        http = HttpResponse()
        kubectl_utils = KubectlUtils()
        fluentd_tag = "deploy_start"
        try:
            input_json = request.get_json(force=True)
            for key, value in input_json.items():
                if key not in EnvironmentSingleton.get_instance().get_env():
                    EnvironmentSingleton.get_instance().set_env_var(str(key), str(value))
        except Exception as e:
            app.logger.debug(f"Exception: {e.__str__()}")

        EnvironmentSingleton.get_instance().set_env_var(EnvConstants.TEMPLATE, template.strip())
        EnvironmentSingleton.get_instance().set_env_var(EnvConstants.VARIABLES, variables.strip())
        app.logger.debug({"msg": {
            "template_file": EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.TEMPLATE)}})
        app.logger.debug({"msg": {"variables_file": EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
            EnvConstants.VARIABLES)}})
        token = token_hex(8)
        deploy_dir = f"{EnvInit.DEPLOY_PATH}/{token}"
        file = f"{deploy_dir}/k8s-deployment.yml"

        try:
            r = Render(EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.TEMPLATE),
                       EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.VARIABLES))
            IOUtils.create_dir(deploy_dir)
            IOUtils.write_to_file(file)
            IOUtils.write_to_file(file, r.rend_template())
            status = kubectl_utils.up(f"{file}")
            self.fluentd.emit(tag=fluentd_tag, msg={"msg": status})
            if status.get('err'):
                raise Exception(status.get('error'))
            result = str(token)
        except Exception as e:
            raise ApiExceptionKubectl(ApiCode.DEPLOY_START_FAILURE.value,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.DEPLOY_START_FAILURE.value), e)

        return Response(
            json.dumps(http.response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value), result)),
            200, mimetype="application/json")

    @route('/deployments/<deployment>', methods=['DELETE'])
    def delete_deployment(self, deployment):
        http = HttpResponse()
        deployment = deployment.strip()
        kubectl_utils = KubectlUtils()
        header_key = 'K8s-Namespace'
        fluentd_tag = "deploy_stop"

        if not request.headers.get(f"{header_key}"):
            raise ApiExceptionKubectl(ApiCode.HTTP_HEADER_NOT_PROVIDED.value,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % header_key,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % header_key)

        try:
            namespace = request.headers.get(f"{header_key}")
            status = kubectl_utils.down(deployment, namespace)
            self.fluentd.emit(tag=fluentd_tag, msg={"msg": status})
            if "Error".lower() in status.get('err').lower():
                raise Exception(status.get('err'))
            result = status.get('out').split("\n")[1:]
        except Exception as e:
            raise ApiExceptionKubectl(ApiCode.DEPLOY_STOP_FAILURE.value,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.DEPLOY_STOP_FAILURE.value), e)

        return Response(
            json.dumps(http.response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value), result)),
            200, mimetype="application/json")

    @route('/deployments/<pod>', methods=['GET'])
    def get_deployment_status(self, pod):
        http = HttpResponse()
        pod = pod.strip()
        kubectl_utils = KubectlUtils()
        header_keys = ["Label-Selector", 'K8s-Namespace']

        for header_key in header_keys:
            if not request.headers.get(f"{header_key}"):
                raise ApiExceptionKubectl(ApiCode.HTTP_HEADER_NOT_PROVIDED.value,
                                          ErrorMessage.HTTP_CODE.get(
                                              ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % header_key,
                                          ErrorMessage.HTTP_CODE.get(
                                              ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % header_key)

        try:
            label_selector = request.headers.get(f"{header_keys[0]}")
            namespace = request.headers.get(f"{header_keys[1]}")
            deployment = kubectl_utils.get_active_pod(pod, label_selector, namespace)
        except Exception as e:
            raise ApiExceptionKubectl(ApiCode.DEPLOY_STATUS_FAILURE.value,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.DEPLOY_STATUS_FAILURE.value), e)

        return Response(
            json.dumps(http.response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                     deployment)), 200, mimetype="application/json")

    @route('/file', methods=['POST', 'PUT'])
    def upload_file(self):
        http = HttpResponse()
        io_utils = IOUtils()
        header_key = 'File-Path'
        file_content = request.get_data()
        file_path = request.headers.get(f"{header_key}")
        if not file_path:
            raise ApiExceptionKubectl(ApiCode.HTTP_HEADER_NOT_PROVIDED.value,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % header_key,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % header_key)

        if not file_content:
            raise ApiExceptionKubectl(ApiCode.EMPTY_REQUEST_BODY_PROVIDED.value,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.EMPTY_REQUEST_BODY_PROVIDED.value),
                                      ErrorMessage.HTTP_CODE.get(ApiCode.EMPTY_REQUEST_BODY_PROVIDED.value))

        try:
            io_utils.write_to_file_binary(file_path, file_content)
        except Exception as e:
            raise ApiExceptionKubectl(ApiCode.UPLOAD_FILE_FAILURE.value,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.UPLOAD_FILE_FAILURE.value), e)

        return Response(
            json.dumps(http.response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                     ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))),
            200, mimetype="application/json")

    @route('/file', methods=['GET'])
    def get_file(self):
        header_key = 'File-Path'

        file_path = request.headers.get(f"{header_key}")
        if not file_path:
            raise ApiExceptionKubectl(ApiCode.HTTP_HEADER_NOT_PROVIDED.value,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % header_key,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % header_key)
        try:
            file_content = IOUtils.read_file(file_path)
        except Exception as e:
            raise ApiExceptionKubectl(ApiCode.GET_FILE_FAILURE.value,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.GET_FILE_FAILURE.value), e)
        return Response(file_content, 200, mimetype="text/plain")

    @route('/deployments/logs/<deployment>', methods=['GET'])
    def deploy_logs(self, deployment):
        http = HttpResponse()
        kubectl_utils = KubectlUtils()
        deployment = deployment.strip()
        header_key = 'K8s-Namespace'

        if not request.headers.get(f"{header_key}"):
            raise ApiExceptionKubectl(ApiCode.HTTP_HEADER_NOT_PROVIDED.value,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % header_key,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % header_key)

        try:
            if request.headers.get(f"{header_key}"):
                namespace = request.headers.get(f"{header_key}")
            status = kubectl_utils.logs(deployment, namespace)
            if status.get('err'):
                raise Exception(status)
        except Exception as e:
            raise ApiExceptionKubectl(ApiCode.GET_LOGS_FAILED.value,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.GET_LOGS_FAILED.value) % deployment, e)

        return Response(
            json.dumps(http.response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                     status.get('out'))), 200, mimetype="application/json")

    @route('/command', methods=['POST', 'PUT'])
    def execute_command(self):
        input_data = request.data.decode("UTF-8", "replace").strip()

        if not input_data:
            raise ApiExceptionKubectl(ApiCode.EMPTY_REQUEST_BODY_PROVIDED.value,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.EMPTY_REQUEST_BODY_PROVIDED.value),
                                      ErrorMessage.HTTP_CODE.get(ApiCode.EMPTY_REQUEST_BODY_PROVIDED.value))
        try:
            input_data_list = input_data.split("\n")
            input_data_list = list(map(lambda x: x.strip(), input_data_list))
            command_in_memory = CommandInMemory()
            response = command_in_memory.run_commands(input_data_list)
        except Exception as e:
            raise ApiExceptionKubectl(ApiCode.COMMAND_EXEC_FAILURE.value,
                                      ErrorMessage.HTTP_CODE.get(ApiCode.COMMAND_EXEC_FAILURE.value), e)

        return Response(
            json.dumps(
                HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                        response)), 200, mimetype="application/json")

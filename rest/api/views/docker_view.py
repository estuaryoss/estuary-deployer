import json
import os
import re
import traceback
from secrets import token_hex

import requests
from flask import request, Response
from flask_classful import FlaskView, route
from fluent import sender

from about import properties
from entities.render import Render
from rest.api.apiresponsehelpers.active_deployments_response import ActiveDeployment
from rest.api.apiresponsehelpers.error_codes import ErrorCodes
from rest.api.apiresponsehelpers.http_response import HttpResponse
from rest.api.constants.api_constants import ApiConstants
from rest.api.constants.env_constants import EnvConstants
from rest.api.definitions import unmodifiable_env_vars
from rest.api.docker_swagger import docker_swagger_file_content
from rest.api.logginghelpers.message_dumper import MessageDumper
from rest.api.views import app
from rest.utils.cmd_utils import CmdUtils
from rest.utils.docker_utils import DockerUtils
from rest.utils.env_startup import EnvStartup
from rest.utils.fluentd_utils import FluentdUtils
from rest.utils.io_utils import IOUtils


class DockerView(FlaskView):
    logger = \
        sender.FluentSender(tag=properties.get('name'),
                            host=EnvStartup.get_instance().get("fluentd_ip_port").split(":")[0],
                            port=int(EnvStartup.get_instance().get("fluentd_ip_port").split(":")[1])) \
            if EnvStartup.get_instance().get("fluentd_ip_port") else None
    fluentd_utils = FluentdUtils(logger)
    message_dumper = MessageDumper()

    def before_request(self, name, *args, **kwargs):
        ctx = app.app_context()
        ctx.g.xid = token_hex(8)
        http = HttpResponse()
        request_uri = request.environ.get("REQUEST_URI")
        # add here your custom header to be logged with fluentd
        self.message_dumper.set_header("X-Request-ID", request.headers.get('X-Request-ID') if request.headers.get(
            'X-Request-ID') else ctx.g.xid)
        self.message_dumper.set_header("Request-Uri", request_uri)

        response = self.fluentd_utils.emit(tag="api", msg=self.message_dumper.dump(request=request))
        app.logger.debug(response)
        if not str(request.headers.get("Token")) == str(EnvStartup.get_instance().get("http_auth_token")):
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

        response = self.fluentd_utils.emit(tag="api", msg=self.message_dumper.dump(http_response))
        app.logger.debug(f"{response}")

        return http_response

    def index(self):
        return "docker"

    @route('/swagger/swagger.yml')
    def swagger(self):
        return Response(docker_swagger_file_content, 200, mimetype="text/plain;charset=UTF-8")

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
            result = "Exception({})".format(e.__str__())
            response = Response(json.dumps(http.failure(ApiConstants.GET_CONTAINER_ENV_VAR_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.GET_CONTAINER_ENV_VAR_FAILURE) % f"{env_var}",
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
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

        os.environ['TEMPLATE'] = template.strip()
        os.environ['VARIABLES'] = variables.strip()

        try:
            rendered_content = Render(os.environ.get('TEMPLATE'), os.environ.get('VARIABLES')).rend_template()
        except Exception as e:
            return Response(json.dumps(http.failure(ApiConstants.JINJA2_RENDER_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(ApiConstants.JINJA2_RENDER_FAILURE),
                                                    "Exception({})".format(e.__str__()),
                                                    "Exception({})".format(e.__str__()))), 404,
                            mimetype="application/json")

        return Response(rendered_content, 200, mimetype="text/plain")

    @route('/deployments', methods=['GET'])
    def get_active_deployments(self):
        http = HttpResponse()
        docker_utils = DockerUtils()
        active_deployments = docker_utils.get_active_deployments()
        app.logger.debug({"msg": {"active_deployments": f"{len(active_deployments)}"}})

        return Response(
            json.dumps(
                http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), active_deployments)),
            200, mimetype="application/json")

    @route('/deployments', methods=['POST'])
    def deploy_start(self):
        http = HttpResponse()
        docker_utils = DockerUtils()
        token = token_hex(8)
        deploy_dir = f"{EnvConstants.DEPLOY_PATH}/{token}"
        file = f"{deploy_dir}/{token}"
        header_key = 'Eureka-Server'
        eureka_server_header = request.headers.get(f"{header_key}")

        status = CmdUtils.run_cmd(["docker", "ps"])
        if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
            return Response(json.dumps(http.failure(ApiConstants.DOCKER_DAEMON_NOT_RUNNING,
                                                    ErrorCodes.HTTP_CODE.get(ApiConstants.DOCKER_DAEMON_NOT_RUNNING),
                                                    status.get('err'),
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        if os.environ.get("MAX_DEPLOYMENTS"):
            active_deployments = docker_utils.get_active_deployments()
            if len(active_deployments) >= int(os.environ.get("MAX_DEPLOYMENTS")):
                return Response(json.dumps(http.failure(ApiConstants.MAX_DEPLOYMENTS_REACHED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.MAX_DEPLOYMENTS_REACHED) % os.environ.get(
                                                            "MAX_DEPLOYMENTS"), active_deployments,
                                                        f"Active deployments: {str(len(active_deployments))}")), 404,
                                mimetype="application/json")
        try:
            template_file_name = f"deployment_{token}.yml"
            input_data = request.data.decode('utf-8')
            template_file_path = f"{EnvConstants.TEMPLATES_PATH}/{template_file_name}"
            IOUtils.write_to_file(template_file_path)
            IOUtils.write_to_file(template_file_path, input_data)

            IOUtils.create_dir(deploy_dir)
            os.environ['TEMPLATE'] = f"{template_file_name}"
            r = Render(os.environ.get('TEMPLATE'), os.environ.get('VARIABLES'))
            if EnvStartup.get_instance().get("eureka_server") and EnvStartup.get_instance().get("app_ip_port"):
                # if {{app_ip_port}} and {{eureka_server}} then register that instance too
                if '{{app_ip_port}}' in input_data and '{{eureka_server}}' in input_data:
                    eureka_server = EnvStartup.get_instance().get("eureka_server")
                    # header value overwrite the eureka server
                    if eureka_server_header:
                        eureka_server = eureka_server_header
                    input_data = r.get_jinja2env().get_template(os.environ.get('TEMPLATE')).render(
                        {"deployment_id": f"{token}",
                         "eureka_server": eureka_server,
                         "app_ip_port": EnvStartup.get_instance().get("app_ip_port").split("/")[0]
                         }
                    )
            app.logger.debug({"msg": {"file_content": f"{input_data}"}})
            if os.path.exists(template_file_path):
                os.remove(template_file_path)
            IOUtils.write_to_file(file, input_data)
            CmdUtils.run_cmd_detached(rf'''docker-compose -f {file} pull && docker-compose -f {file} up -d''')
            response = Response(
                json.dumps(http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), token)),
                200,
                mimetype="application/json")
        except Exception as e:
            result = "Exception({})".format(e.__str__())
            status = docker_utils.down(file)
            app.logger.debug({"msg": status})
            response = Response(json.dumps(http.failure(ApiConstants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_START_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/deployments/<template>/<variables>', methods=['POST'])
    def deploy_start_env(self, template, variables):
        http = HttpResponse()
        docker_utils = DockerUtils()
        try:
            input_json = request.get_json(force=True)
            for key, value in input_json.items():
                if key not in unmodifiable_env_vars:
                    os.environ[str(key)] = str(value)
        except:
            pass

        os.environ['TEMPLATE'] = template.strip()
        os.environ['VARIABLES'] = variables.strip()
        app.logger.debug({"msg": {"template_file": os.environ.get('TEMPLATE')}})
        app.logger.debug({"msg": {"variables_file": os.environ.get('VARIABLES')}})
        token = token_hex(8)
        deploy_dir = f"{EnvConstants.DEPLOY_PATH}/{token}"
        file = f"{deploy_dir}/{token}"

        status = CmdUtils.run_cmd(["docker", "ps"])
        if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
            return Response(json.dumps(http.failure(ApiConstants.DOCKER_DAEMON_NOT_RUNNING,
                                                    ErrorCodes.HTTP_CODE.get(ApiConstants.DOCKER_DAEMON_NOT_RUNNING),
                                                    status.get('err'),
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        if os.environ.get("MAX_DEPLOYMENTS"):
            active_deployments = docker_utils.get_active_deployments()
            if len(active_deployments) >= int(os.environ.get("MAX_DEPLOYMENTS")):
                return Response(json.dumps(http.failure(ApiConstants.MAX_DEPLOYMENTS_REACHED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.MAX_DEPLOYMENTS_REACHED) % os.environ.get(
                                                            "MAX_DEPLOYMENTS"), active_deployments,
                                                        f"Active deployments: {str(len(active_deployments))}")), 404,
                                mimetype="application/json")
        try:
            r = Render(os.environ.get('TEMPLATE'), os.environ.get('VARIABLES'))
            IOUtils.create_dir(deploy_dir)
            IOUtils.write_to_file(file)
            IOUtils.write_to_file(file, r.rend_template())
            CmdUtils.run_cmd_detached(rf'''docker-compose -f {file} pull && docker-compose -f {file} up -d''')
            result = str(token)
            response = Response(
                json.dumps(http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), result)),
                200,
                mimetype="application/json")
        except Exception as e:
            result = "Exception({})".format(e.__str__())
            response = Response(json.dumps(http.failure(ApiConstants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_START_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/deployments/<env_id>', methods=['GET'])
    def deploy_status(self, env_id):
        http = HttpResponse()
        docker_utils = DockerUtils()
        env_id = env_id.strip()
        try:
            status = docker_utils.ps(env_id)
            if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
                return Response(json.dumps(http.failure(ApiConstants.DOCKER_DAEMON_NOT_RUNNING,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.DOCKER_DAEMON_NOT_RUNNING),
                                                        status.get('err'),
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
            result = status.get('out').split("\n")[1:-1]
            response = Response(
                json.dumps(http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                                        ActiveDeployment.docker_deployment(env_id, result))), 200,
                mimetype="application/json")
            app.logger.debug({"msg": status})
        except Exception as e:
            result = "Exception({})".format(e.__str__())
            response = Response(json.dumps(http.failure(ApiConstants.DEPLOY_STATUS_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_STATUS_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/deployments/<env_id>', methods=['DELETE'])
    def deploy_stop(self, env_id):
        http = HttpResponse()
        env_id = env_id.strip()
        docker_utils = DockerUtils()
        file = f"{EnvConstants.DEPLOY_PATH}/{env_id}/{env_id}"
        try:
            status = docker_utils.down(file)
            if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
                return Response(json.dumps(http.failure(ApiConstants.DOCKER_DAEMON_NOT_RUNNING,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.DOCKER_DAEMON_NOT_RUNNING),
                                                        status.get('err'),
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
            app.logger.debug({"msg": status})
            status = docker_utils.ps(env_id)
            result = status.get('out').split("\n")[1:-1]
            response = Response(
                json.dumps(http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), result)),
                200,
                mimetype="application/json")
        except Exception as e:
            result = "Exception({})".format(e.__str__())
            response = Response(json.dumps(http.failure(ApiConstants.DEPLOY_STOP_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_STOP_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

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
            file_content = IOUtils.read_file(file_path)
        except Exception as e:
            return Response(json.dumps(http.failure(ApiConstants.GET_FILE_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        ApiConstants.GET_FILE_FAILURE),
                                                    "Exception({})".format(e.__str__()),
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        return Response(file_content, 200, mimetype="text/plain")

    @route('/file', methods=['POST', 'PUT'])
    def upload_file(self):
        http = HttpResponse()
        io_utils = IOUtils()
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

            io_utils.write_to_file_binary(file_path, file_content)
        except Exception as e:
            exception = "Exception({})".format(e.__str__())
            return Response(json.dumps(http.failure(ApiConstants.UPLOAD_FILE_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(ApiConstants.UPLOAD_FILE_FAILURE),
                                                    exception,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")

        return Response(json.dumps(http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                                                ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS))),
                        200,
                        mimetype="application/json")

    @route('/deployments/logs/<env_id>', methods=['GET'])
    def deploy_logs(self, env_id):
        http = HttpResponse()
        docker_utils = DockerUtils()
        env_id = env_id.strip()
        env_id_dir = EnvConstants.DEPLOY_PATH + "/{}".format(env_id)
        file = f"{env_id_dir}/{env_id}"

        try:
            status = docker_utils.logs(file)
            app.logger.debug({"msg": status})
            if status.get('err'):
                return Response(json.dumps(http.failure(ApiConstants.GET_LOGS_FAILED,
                                                        ErrorCodes.HTTP_CODE.get(ApiConstants.GET_LOGS_FAILED) % env_id,
                                                        status.get('err'),
                                                        status.get('err'))), 404, mimetype="application/json")
        except Exception as e:
            exception = "Exception({})".format(e.__str__())
            return Response(json.dumps(http.failure(ApiConstants.GET_LOGS_FAILED,
                                                    ErrorCodes.HTTP_CODE.get(ApiConstants.GET_LOGS_FAILED) % env_id,
                                                    exception,
                                                    exception)), 404, mimetype="application/json")

        return Response(
            json.dumps(http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                                    status.get('out').split("\n"))),
            200, mimetype="application/json")

    # must connect the container to the deployer network to be able to send http req to the test runner which runs in a initial segregated net
    @route('/deployments/network/<env_id>', methods=['POST', 'PUT'])
    def container_docker_network_connect(self, env_id):
        http = HttpResponse()
        docker_utils = DockerUtils()
        service_name = "container"
        if request.args.get('service') is not None:
            service_name = request.args.get('service')
        container_id = f"{env_id}_{service_name}_1"
        try:
            # when creating deployer net, user must include 'deployer' in its name
            # otherwise this method should have docker net param regex through http header
            status = CmdUtils.run_cmd(["docker", "network", "ls", "--filter", "name={}".format("deployer")])
            app.logger.debug({"msg": status})
            if not status.get('out'):
                return Response(json.dumps(http.failure(ApiConstants.GET_DEPLOYER_NETWORK_FAILED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.GET_DEPLOYER_NETWORK_FAILED),
                                                        status.get('err'),
                                                        status.get('err'))), 404, mimetype="application/json")
            deployer_network = status.get('out').split("\n")[1].split(" ")[0].strip()
            status = docker_utils.network_connect(deployer_network, container_id)

            if "already exists in network".lower() in status.get('err').lower():
                return Response(json.dumps(http.success(ApiConstants.SUCCESS,
                                                        ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                                                        "Success, already connected: " + status.get('err'))), 200,
                                mimetype="application/json")

            if "Error response from daemon".lower() in status.get('err').lower():
                return Response(json.dumps(http.failure(ApiConstants.CONTAINER_DEPLOYER_NET_CONNECT_FAILED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.CONTAINER_DEPLOYER_NET_CONNECT_FAILED),
                                                        status.get('err'),
                                                        status.get('err'))), 404, mimetype="application/json")
        except Exception as e:
            exception = "Exception({})".format(e.__str__())
            return Response(json.dumps(http.failure(ApiConstants.CONTAINER_DEPLOYER_NET_CONNECT_FAILED,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        ApiConstants.CONTAINER_DEPLOYER_NET_CONNECT_FAILED),
                                                    exception,
                                                    exception)), 404, mimetype="application/json")
        return Response(
            json.dumps(
                http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), status.get('out'))),
            200, mimetype="application/json")

    @route('/deployments/network/<env_id>', methods=['DELETE'])
    def container_docker_network_disconnect(self, env_id):
        http = HttpResponse()
        docker_utils = DockerUtils()
        service_name = "container"
        if request.args.get('service') is not None:
            service_name = request.args.get('service')
        container_id = f"{env_id}_{service_name}_1"
        try:
            status = CmdUtils.run_cmd(["docker", "network", "ls", "--filter", "name={}".format("deployer")])
            app.logger.debug({"msg": status})
            if not status.get('out'):
                return Response(json.dumps(http.failure(ApiConstants.GET_DEPLOYER_NETWORK_FAILED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.GET_DEPLOYER_NETWORK_FAILED),
                                                        status.get('err'),
                                                        status.get('err'))), 404, mimetype="application/json")
            deployer_network = status.get('out').split("\n")[1].split(" ")[0].strip()
            status = docker_utils.network_disconnect(deployer_network, container_id)

            if "is not connected to network".lower() in status.get('err').lower():
                return Response(json.dumps(http.success(ApiConstants.SUCCESS,
                                                        ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                                                        "Success, already disconnected: " + status.get('err'))), 200,
                                mimetype="application/json")

            if "Error response from daemon".lower() in status.get('err').lower():
                return Response(json.dumps(http.failure(ApiConstants.CONTAINER_DEPLOYER_NET_DISCONNECT_FAILED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            ApiConstants.CONTAINER_DEPLOYER_NET_DISCONNECT_FAILED),
                                                        status.get('err'),
                                                        status.get('err'))), 404, mimetype="application/json")
        except Exception as e:
            exception = "Exception({})".format(e.__str__())
            return Response(json.dumps(http.failure(ApiConstants.CONTAINER_DEPLOYER_NET_DISCONNECT_FAILED,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        ApiConstants.CONTAINER_DEPLOYER_NET_DISCONNECT_FAILED),
                                                    exception,
                                                    exception)), 404, mimetype="application/json")
        return Response(
            json.dumps(
                http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), status.get('out'))),
            200, mimetype="application/json")

    # here the requests are redirected to any container
    # you can couple your own, just make sure the hostname is 'container'
    # url format: container/dockercomposeenvid/the_url?port=8080&service=container
    # E.g.1 /container/2a1c9aa0451add84/uploadtestconfig
    @route('/container/<env_id>/<path:text>',
           methods=['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH'])
    def container_request(self, env_id, text):
        http = HttpResponse()
        container_url = text.strip()
        headers = request.headers

        service_name = "container"
        if request.args.get('service') is not None:
            service_name = request.args.get('service')
        container_id = f"{env_id}_{service_name}_1"

        container_port = 8080
        if request.args.get('port') is not None:
            container_port = request.args.get('port')

        input_data = None
        try:
            input_data = request.get_data()
        except:
            pass

        complete_url = f"http://{container_id}:{container_port}/{container_url}"
        try:
            r = requests.request(url=complete_url, method=request.method, data=input_data, headers=headers, timeout=5)
        except Exception as e:
            exception = "Exception({})".format(e.__str__())
            return Response(json.dumps(http.failure(ApiConstants.CONTAINER_UNREACHABLE,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        ApiConstants.CONTAINER_UNREACHABLE) % (
                                                        service_name, service_name),
                                                    exception,
                                                    exception)), 404, mimetype="application/json")
        return Response(r.text, r.status_code)

    @route('/command', methods=['POST', 'PUT'])
    def execute_command(self):
        http = HttpResponse()
        io_utils = IOUtils()
        cmd_utils = CmdUtils()
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
            exception = "Exception({})".format(e.__str__())
            return Response(json.dumps(http.failure(ApiConstants.COMMAND_EXEC_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(ApiConstants.COMMAND_EXEC_FAILURE) % cmd[
                                                        0],
                                                    exception,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")

        return Response(
            json.dumps(http.success(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), info_init)),
            200,
            mimetype="application/json")

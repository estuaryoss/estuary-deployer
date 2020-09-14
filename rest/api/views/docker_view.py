import json
import os
from secrets import token_hex

import requests
from flask import request, Response
from flask_classful import FlaskView, route
from fluent import sender

from about import properties
from rest.api.constants.api_constants import ApiConstants
from rest.api.constants.env_constants import EnvConstants
from rest.api.constants.env_init import EnvInit
from rest.api.constants.header_constants import HeaderConstants
from rest.api.docker_swagger import docker_swagger_file_content
from rest.api.jinja2.render import Render
from rest.api.loghelpers.message_dumper import MessageDumper
from rest.api.responsehelpers.active_deployments_response import ActiveDeployment
from rest.api.responsehelpers.error_codes import ErrorCodes
from rest.api.responsehelpers.http_response import HttpResponse
from rest.api.views import app
from rest.environment.environment import EnvironmentSingleton
from rest.service.fluentd import Fluentd
from rest.utils.cmd_utils import CmdUtils
from rest.utils.command_in_memory import CommandInMemory
from rest.utils.docker_utils import DockerUtils
from rest.utils.env_startup import EnvStartupSingleton
from rest.utils.io_utils import IOUtils


class DockerView(FlaskView):
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
        app.logger.debug(response)
        if not str(request.headers.get(HeaderConstants.TOKEN)) == str(
                EnvStartupSingleton.get_instance().get_config_env_vars().get(EnvConstants.HTTP_AUTH_TOKEN)):
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
        return "docker"

    @route('/swagger/swagger.yml')
    def swagger(self):
        return Response(docker_swagger_file_content, 200, mimetype="text/plain;charset=UTF-8")

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

    @route('/env')
    def get_env_vars(self):
        http = HttpResponse()
        return Response(
            json.dumps(
                http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                              EnvironmentSingleton.get_instance().get_env_and_virtual_env())),
            200, mimetype="application/json")

    @route('/env/<env_var>', methods=['GET'])
    def get_env_var(self, env_var):
        http = HttpResponse()
        try:
            response = Response(json.dumps(
                http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                              EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(env_var))),
                200,
                mimetype="application/json")
        except Exception as e:
            result = "Exception({})".format(e.__str__())
            response = Response(
                json.dumps(http.response(ApiConstants.GET_CONTAINER_ENV_VAR_FAILURE,
                                         ErrorCodes.HTTP_CODE.get(ApiConstants.GET_CONTAINER_ENV_VAR_FAILURE) % env_var,
                                         result)), 404, mimetype="application/json")
        return response

    @route('/env', methods=['POST'])
    def set_env(self):
        http = HttpResponse()
        input_data = request.data.decode("UTF-8", "replace").strip()

        try:
            env_vars_attempted = json.loads(input_data)
        except Exception as e:
            return Response(json.dumps(http.response(code=ApiConstants.INVALID_JSON_PAYLOAD,
                                                     message=ErrorCodes.HTTP_CODE.get(
                                                         ApiConstants.INVALID_JSON_PAYLOAD) % str(
                                                         input_data),
                                                     description="Exception({0})".format(e.__str__()))), 404,
                            mimetype="application/json")

        try:
            for key, value in env_vars_attempted.items():
                EnvironmentSingleton.get_instance().set_env_var(key, value)

            env_vars_added = {key: value for key, value in env_vars_attempted.items() if
                              key in EnvironmentSingleton.get_instance().get_virtual_env()}
        except Exception as e:
            return Response(json.dumps(http.response(code=ApiConstants.SET_ENV_VAR_FAILURE,
                                                     message=ErrorCodes.HTTP_CODE.get(
                                                         ApiConstants.SET_ENV_VAR_FAILURE) % str(
                                                         input_data),
                                                     description="Exception({})".format(e.__str__()))), 404,
                            mimetype="application/json")
        return Response(
            json.dumps(
                http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                              env_vars_added)),
            200,
            mimetype="application/json")

    @route('/render/<template>/<variables>', methods=['GET', 'POST'])
    def get_content_with_env(self, template, variables):
        http = HttpResponse()
        try:
            input_json = request.get_json(force=True)
            for key, value in input_json.items():
                if key not in EnvironmentSingleton.get_instance().get_env():
                    EnvironmentSingleton.get_instance().set_env_var(str(key), str(value))
        except:
            pass

        EnvironmentSingleton.get_instance().set_env_var(EnvConstants.TEMPLATE, template.strip())
        EnvironmentSingleton.get_instance().set_env_var(EnvConstants.VARIABLES, variables.strip())

        try:
            rendered_content = Render(
                EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.TEMPLATE),
                EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
                    EnvConstants.VARIABLES)).rend_template()
        except Exception as e:
            return Response(json.dumps(http.response(ApiConstants.JINJA2_RENDER_FAILURE,
                                                     ErrorCodes.HTTP_CODE.get(ApiConstants.JINJA2_RENDER_FAILURE),
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
                http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                              active_deployments)),
            200, mimetype="application/json")

    @route('/deployments', methods=['POST'])
    def deploy_start(self):
        http = HttpResponse()
        docker_utils = DockerUtils()
        token = token_hex(8)
        deploy_dir = f"{EnvInit.DEPLOY_PATH}/{token}"
        file = f"{deploy_dir}/{token}"
        header_key = 'Eureka-Server'
        eureka_server_header = request.headers.get(f"{header_key}")

        status = CmdUtils.run_cmd_shell_false(["docker", "ps"])
        if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
            return Response(json.dumps(http.response(ApiConstants.DOCKER_DAEMON_NOT_RUNNING,
                                                     ErrorCodes.HTTP_CODE.get(ApiConstants.DOCKER_DAEMON_NOT_RUNNING),
                                                     status.get('err'))), 404, mimetype="application/json")
        if EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.MAX_DEPLOYMENTS):
            active_deployments = docker_utils.get_active_deployments()
            if len(active_deployments) >= int(
                    EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.MAX_DEPLOYMENTS)):
                return Response(json.dumps(http.response(ApiConstants.MAX_DEPLOYMENTS_REACHED,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.MAX_DEPLOYMENTS_REACHED) % EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
                                                             EnvConstants.MAX_DEPLOYMENTS), active_deployments)), 404,
                                mimetype="application/json")
        try:
            template_file_name = f"deployment_{token}.yml"
            input_data = request.data.decode('utf-8')
            template_file_path = f"{EnvInit.TEMPLATES_PATH}/{template_file_name}"
            IOUtils.write_to_file(template_file_path)
            IOUtils.write_to_file(template_file_path, input_data)

            IOUtils.create_dir(deploy_dir)
            EnvironmentSingleton.get_instance().set_env_var(EnvConstants.TEMPLATE, template_file_name)
            r = Render(EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.TEMPLATE),
                       EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.VARIABLES))
            if EnvStartupSingleton.get_instance().get_config_env_vars().get(
                    EnvConstants.EUREKA_SERVER) and EnvStartupSingleton.get_instance().get_config_env_vars().get(
                EnvConstants.APP_IP_PORT):
                # if {{app_ip_port}} and {{eureka_server}} then register that instance too
                if '{{app_ip_port}}' in input_data and '{{eureka_server}}' in input_data:
                    eureka_server = EnvStartupSingleton.get_instance().get_config_env_vars().get(
                        EnvConstants.EUREKA_SERVER)
                    # header value overwrite the eureka server
                    if eureka_server_header:
                        eureka_server = eureka_server_header
                    input_data = r.get_jinja2env().get_template(
                        EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
                            EnvConstants.TEMPLATE)).render(
                        {"deployment_id": f"{token}",
                         "eureka_server": eureka_server,
                         "app_ip_port": EnvStartupSingleton.get_instance().get_config_env_vars().get(
                             EnvConstants.APP_IP_PORT).split("/")[0]
                         }
                    )
            app.logger.debug({"msg": {"file_content": f"{input_data}"}})
            if os.path.exists(template_file_path):
                os.remove(template_file_path)
            IOUtils.write_to_file(file, input_data)
            CmdUtils.run_cmd_detached(rf'''docker-compose -f {file} pull && docker-compose -f {file} up -d''')
            response = Response(
                json.dumps(http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), token)),
                200,
                mimetype="application/json")
        except Exception as e:
            result = "Exception({})".format(e.__str__())
            status = docker_utils.down(file)
            app.logger.debug({"msg": status})
            response = Response(json.dumps(http.response(ApiConstants.DEPLOY_START_FAILURE,
                                                         ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_START_FAILURE),
                                                         result)), 404,
                                mimetype="application/json")

        return response

    @route('/deployments/<template>/<variables>', methods=['POST'])
    def deploy_start_env(self, template, variables):
        http = HttpResponse()
        docker_utils = DockerUtils()
        try:
            input_json = request.get_json(force=True)
            for key, value in input_json.items():
                if key not in EnvironmentSingleton.get_instance().get_env():
                    EnvironmentSingleton.get_instance().set_env_var(str(key), str(value))
        except:
            pass

        EnvironmentSingleton.get_instance().set_env_var(EnvConstants.TEMPLATE, template.strip())
        EnvironmentSingleton.get_instance().set_env_var(EnvConstants.VARIABLES, variables.strip())
        app.logger.debug({"msg": {
            "template_file": EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.TEMPLATE)}})
        app.logger.debug({"msg": {"variables_file": EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
            EnvConstants.VARIABLES)}})
        token = token_hex(8)
        deploy_dir = f"{EnvInit.DEPLOY_PATH}/{token}"
        file = f"{deploy_dir}/{token}"

        status = CmdUtils.run_cmd_shell_false(["docker", "ps"])
        if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
            return Response(json.dumps(http.response(ApiConstants.DOCKER_DAEMON_NOT_RUNNING,
                                                     ErrorCodes.HTTP_CODE.get(ApiConstants.DOCKER_DAEMON_NOT_RUNNING),
                                                     status.get('err'))), 404, mimetype="application/json")
        if EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.MAX_DEPLOYMENTS):
            active_deployments = docker_utils.get_active_deployments()
            if len(active_deployments) >= int(
                    EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.MAX_DEPLOYMENTS)):
                return Response(json.dumps(http.response(ApiConstants.MAX_DEPLOYMENTS_REACHED,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.MAX_DEPLOYMENTS_REACHED) % EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
                                                             EnvConstants.MAX_DEPLOYMENTS), active_deployments)), 404,
                                mimetype="application/json")
        try:
            r = Render(EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.TEMPLATE),
                       EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.VARIABLES))
            IOUtils.create_dir(deploy_dir)
            IOUtils.write_to_file(file)
            IOUtils.write_to_file(file, r.rend_template())
            CmdUtils.run_cmd_detached(rf'''docker-compose -f {file} pull && docker-compose -f {file} up -d''')
            result = str(token)
            response = Response(
                json.dumps(http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), result)),
                200,
                mimetype="application/json")
        except Exception as e:
            result = "Exception({})".format(e.__str__())
            response = Response(json.dumps(http.response(ApiConstants.DEPLOY_START_FAILURE,
                                                         ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_START_FAILURE),
                                                         result)), 404, mimetype="application/json")

        return response

    @route('/deployments/<env_id>', methods=['GET'])
    def deploy_status(self, env_id):
        http = HttpResponse()
        docker_utils = DockerUtils()
        env_id = env_id.strip()
        try:
            status = docker_utils.ps(env_id)
            if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
                return Response(json.dumps(http.response(ApiConstants.DOCKER_DAEMON_NOT_RUNNING,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.DOCKER_DAEMON_NOT_RUNNING),
                                                         status.get('err'))), 404, mimetype="application/json")
            result = status.get('out').split("\n")[1:-1]
            response = Response(
                json.dumps(http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                                         ActiveDeployment.docker_deployment(env_id, result))), 200,
                mimetype="application/json")
            app.logger.debug({"msg": status})
        except Exception as e:
            result = "Exception({})".format(e.__str__())
            response = Response(json.dumps(http.response(ApiConstants.DEPLOY_STATUS_FAILURE,
                                                         ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_STATUS_FAILURE),
                                                         result)), 404, mimetype="application/json")

        return response

    @route('/deployments/<env_id>', methods=['DELETE'])
    def deploy_stop(self, env_id):
        http = HttpResponse()
        env_id = env_id.strip()
        docker_utils = DockerUtils()
        file = f"{EnvInit.DEPLOY_PATH}/{env_id}/{env_id}"
        try:
            status = docker_utils.down(file)
            if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
                return Response(json.dumps(http.response(ApiConstants.DOCKER_DAEMON_NOT_RUNNING,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.DOCKER_DAEMON_NOT_RUNNING),
                                                         status.get('err'))), 404, mimetype="application/json")
            app.logger.debug({"msg": status})
            status = docker_utils.ps(env_id)
            result = status.get('out').split("\n")[1:-1]
            response = Response(
                json.dumps(http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), result)),
                200,
                mimetype="application/json")
        except Exception as e:
            result = "Exception({})".format(e.__str__())
            response = Response(json.dumps(http.response(ApiConstants.DEPLOY_STOP_FAILURE,
                                                         ErrorCodes.HTTP_CODE.get(ApiConstants.DEPLOY_STOP_FAILURE),
                                                         result)), 404, mimetype="application/json")

        return response

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
            exception = "Exception({})".format(e.__str__())
            return Response(json.dumps(http.response(ApiConstants.UPLOAD_FILE_FAILURE,
                                                     ErrorCodes.HTTP_CODE.get(ApiConstants.UPLOAD_FILE_FAILURE),
                                                     exception)), 404, mimetype="application/json")

        return Response(json.dumps(http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                                                 ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS))),
                        200,
                        mimetype="application/json")

    @route('/deployments/logs/<env_id>', methods=['GET'])
    def deploy_logs(self, env_id):
        http = HttpResponse()
        docker_utils = DockerUtils()
        env_id = env_id.strip()
        env_id_dir = EnvInit.DEPLOY_PATH + "/{}".format(env_id)
        file = f"{env_id_dir}/{env_id}"

        try:
            status = docker_utils.logs(file)
            app.logger.debug({"msg": status})
            if status.get('err'):
                return Response(json.dumps(http.response(ApiConstants.GET_LOGS_FAILED,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.GET_LOGS_FAILED) % env_id,
                                                         status.get('err'))), 404, mimetype="application/json")
        except Exception as e:
            exception = "Exception({})".format(e.__str__())
            return Response(json.dumps(http.response(ApiConstants.GET_LOGS_FAILED,
                                                     ErrorCodes.HTTP_CODE.get(ApiConstants.GET_LOGS_FAILED) % env_id,
                                                     exception)), 404, mimetype="application/json")

        return Response(
            json.dumps(http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                                     status.get('out').split("\n"))),
            200, mimetype="application/json")

    # must connect the container to the deployer network to be able to send http req to the test runner which runs in a initial segregated net
    @route('/deployments/network/<env_id>', methods=['POST', 'PUT'])
    def container_docker_network_connect(self, env_id):
        http = HttpResponse()
        docker_utils = DockerUtils()
        headers = request.headers
        service_name = "container"

        if request.args.get('service') is not None:
            service_name = request.args.get('service')
        container_id = f"{env_id}_{service_name}_1"
        try:
            # when creating deployer net, user must include 'deployer' in its name
            # otherwise this method should have docker net param regex through http header
            status = CmdUtils.run_cmd_shell_false(["docker", "network", "ls", "--filter", "name={}".format("deployer")])
            app.logger.debug({"msg": status})
            if not status.get('out'):
                return Response(json.dumps(http.response(ApiConstants.GET_DEPLOYER_NETWORK_FAILED,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.GET_DEPLOYER_NETWORK_FAILED),
                                                         status.get('err'))), 404, mimetype="application/json")
            deployer_network = status.get('out').split("\n")[1].split(" ")[0].strip()
            if headers.get("Docker-Network"):
                deployer_network = headers.get("Docker-Network")
            status = docker_utils.network_connect(deployer_network, container_id)

            if "already exists in network".lower() in status.get('err').lower():
                return Response(json.dumps(http.response(ApiConstants.SUCCESS,
                                                         ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                                                         "Success, already connected: " + status.get('err'))), 200,
                                mimetype="application/json")

            if "Error response from daemon".lower() in status.get('err').lower():
                return Response(json.dumps(http.response(ApiConstants.CONTAINER_DEPLOYER_NET_CONNECT_FAILED,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.CONTAINER_DEPLOYER_NET_CONNECT_FAILED),
                                                         status.get('err'))), 404, mimetype="application/json")
        except Exception as e:
            exception = "Exception({})".format(e.__str__())
            return Response(json.dumps(http.response(ApiConstants.CONTAINER_DEPLOYER_NET_CONNECT_FAILED,
                                                     ErrorCodes.HTTP_CODE.get(
                                                         ApiConstants.CONTAINER_DEPLOYER_NET_CONNECT_FAILED),
                                                     exception)), 404, mimetype="application/json")
        return Response(
            json.dumps(
                http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), status.get('out'))),
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
            status = CmdUtils.run_cmd_shell_false(["docker", "network", "ls", "--filter", "name={}".format("deployer")])
            app.logger.debug({"msg": status})
            if not status.get('out'):
                return Response(json.dumps(http.response(ApiConstants.GET_DEPLOYER_NETWORK_FAILED,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.GET_DEPLOYER_NETWORK_FAILED),
                                                         status.get('err'))), 404, mimetype="application/json")
            deployer_network = status.get('out').split("\n")[1].split(" ")[0].strip()
            status = docker_utils.network_disconnect(deployer_network, container_id)

            if "is not connected to network".lower() in status.get('err').lower():
                return Response(json.dumps(http.response(ApiConstants.SUCCESS,
                                                         ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS),
                                                         "Success, already disconnected: " + status.get('err'))), 200,
                                mimetype="application/json")

            if "Error response from daemon".lower() in status.get('err').lower():
                return Response(json.dumps(http.response(ApiConstants.CONTAINER_DEPLOYER_NET_DISCONNECT_FAILED,
                                                         ErrorCodes.HTTP_CODE.get(
                                                             ApiConstants.CONTAINER_DEPLOYER_NET_DISCONNECT_FAILED),
                                                         status.get('err'))), 404, mimetype="application/json")
        except Exception as e:
            exception = "Exception({})".format(e.__str__())
            return Response(json.dumps(http.response(ApiConstants.CONTAINER_DEPLOYER_NET_DISCONNECT_FAILED,
                                                     ErrorCodes.HTTP_CODE.get(
                                                         ApiConstants.CONTAINER_DEPLOYER_NET_DISCONNECT_FAILED),
                                                     exception)), 404, mimetype="application/json")
        return Response(
            json.dumps(
                http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), status.get('out'))),
            200, mimetype="application/json")

    # here the requests are redirected to any container
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
            return Response(json.dumps(http.response(ApiConstants.CONTAINER_UNREACHABLE,
                                                     ErrorCodes.HTTP_CODE.get(
                                                         ApiConstants.CONTAINER_UNREACHABLE) % (
                                                         service_name, service_name),
                                                     exception)), 404, mimetype="application/json")
        return Response(r.text, r.status_code)

    @route('/command', methods=['POST', 'PUT'])
    def execute_command(self):
        http = HttpResponse()
        input_data = request.data.decode("UTF-8", "replace").strip()

        if not input_data:
            return Response(json.dumps(http.response(ApiConstants.EMPTY_REQUEST_BODY_PROVIDED,
                                                     ErrorCodes.HTTP_CODE.get(
                                                         ApiConstants.EMPTY_REQUEST_BODY_PROVIDED),
                                                     ErrorCodes.HTTP_CODE.get(
                                                         ApiConstants.EMPTY_REQUEST_BODY_PROVIDED))), 404,
                            mimetype="application/json")
        try:
            input_data_list = input_data.split("\n")
            input_data_list = list(map(lambda x: x.strip(), input_data_list))
            command_in_memory = CommandInMemory()
            response = command_in_memory.run_commands(input_data_list)
        except Exception as e:
            exception = "Exception({})".format(e.__str__())
            return Response(json.dumps(http.response(ApiConstants.COMMAND_EXEC_FAILURE,
                                                     ErrorCodes.HTTP_CODE.get(ApiConstants.COMMAND_EXEC_FAILURE),
                                                     exception)), 404, mimetype="application/json")

        return Response(
            json.dumps(http.response(ApiConstants.SUCCESS, ErrorCodes.HTTP_CODE.get(ApiConstants.SUCCESS), response)),
            200,
            mimetype="application/json")

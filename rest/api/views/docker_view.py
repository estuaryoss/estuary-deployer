import json
import os
import shutil
from secrets import token_hex

import requests
from flask import request, Response, render_template, send_from_directory
from flask_classful import FlaskView, route
from fluent import sender

from about import properties, about_system
from rest.api.constants.api_code import ApiCode
from rest.api.constants.env_constants import EnvConstants
from rest.api.constants.env_init import EnvInit
from rest.api.constants.header_constants import HeaderConstants
from rest.api.exception.api_exception_docker import ApiExceptionDocker
from rest.api.jinja2.render import Render
from rest.api.loghelpers.message_dumper import MessageDumper
from rest.api.responsehelpers.active_deployments_response import ActiveDeployment
from rest.api.responsehelpers.error_message import ErrorMessage
from rest.api.responsehelpers.http_response import HttpResponse
from rest.api.views import app
from rest.environment.deployment_metadata import DeploymentMetadataSingleton
from rest.environment.environment import EnvironmentSingleton
from rest.model.deployment_reader import DeploymentReader
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
            if not ("/apidocs" in request_uri or "/swagger/swagger.json" in request_uri):  # exclude swagger
                headers = {
                    HeaderConstants.X_REQUEST_ID: self.message_dumper.get_header(HeaderConstants.X_REQUEST_ID)
                }
                return Response(json.dumps(http.response(ApiCode.UNAUTHORIZED.value,
                                                         ErrorMessage.HTTP_CODE.get(ApiCode.UNAUTHORIZED.value),
                                                         "Invalid Token")), 401, mimetype="application/json",
                                headers=headers)

    def after_request(self, name, http_response):
        http_response.headers[HeaderConstants.X_REQUEST_ID] = self.message_dumper.get_header(
            HeaderConstants.X_REQUEST_ID)

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
        http_response.headers[HeaderConstants.X_REQUEST_ID] = DockerView.message_dumper.get_header(
            HeaderConstants.X_REQUEST_ID)
        response = DockerView.fluentd.emit(tag="api", msg=DockerView.message_dumper.dump(http_response))
        app.logger.debug(f"{response}")
        return http_response

    def index(self):
        return render_template('index.html')

    @route('/apidocs')
    def send_swagger(self):
        return render_template('index.html')

    @route('/resources/<path:path>')
    def send_resources(self, path):
        return send_from_directory('swaggerui/resources', path)

    @route('/swagger/swagger.json')
    def swagger(self):
        return render_template('swagger.json')

    @route('/ping')
    def ping(self):
        return Response(
            json.dumps(HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                               "pong")), 200, mimetype="application/json")

    @route('/about')
    def about(self):
        return Response(
            json.dumps(HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                               about_system)), 200, mimetype="application/json")

    @route('/env', methods=['GET'])
    def get_env_vars(self):
        return Response(
            json.dumps(HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                               EnvironmentSingleton.get_instance().get_env_and_virtual_env())),
            200, mimetype="application/json")

    @route('/envinit', methods=['GET'])
    def get_init_env(self):
        return Response(
            json.dumps(HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                               EnvInit.init)),
            200, mimetype="application/json")

    @route('/env/<env_var>', methods=['GET'])
    def get_env_var(self, env_var):
        return Response(json.dumps(
            HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                    EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(env_var))),
            200, mimetype="application/json")

    @route('/env', methods=['POST'])
    def set_env(self):
        input_data = request.data.decode("UTF-8", "replace").strip()

        try:
            env_vars_attempted = json.loads(input_data)
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.INVALID_JSON_PAYLOAD.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.INVALID_JSON_PAYLOAD.value) % str(input_data),
                                     e)

        try:
            env_vars_added = EnvironmentSingleton.get_instance().set_env_vars(env_vars_attempted)
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.SET_ENV_VAR_FAILURE,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.SET_ENV_VAR_FAILURE) % str(input_data), e)
        return Response(
            json.dumps(
                HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                        env_vars_added)), 200, mimetype="application/json")

    @route('/render/<template>/<variables>', methods=['GET', 'POST'])
    def get_rendered_content_with_env(self, template, variables):
        try:
            input_json = request.get_json(force=True)
            for key, value in input_json.items():
                if key not in EnvironmentSingleton.get_instance().get_env():
                    EnvironmentSingleton.get_instance().set_env_var(str(key), str(value))
        except Exception as e:
            app.logger.debug({"msg": f"Could not load the body from the request as JSON: {e.__str__()}"})

        EnvironmentSingleton.get_instance().set_env_var(EnvConstants.TEMPLATE, template.strip())
        EnvironmentSingleton.get_instance().set_env_var(EnvConstants.VARIABLES, variables.strip())

        try:
            env_vars = EnvironmentSingleton.get_instance().get_env_and_virtual_env()
            rendered_content = Render(
                env_vars.get(EnvConstants.TEMPLATE),
                env_vars.get(
                    EnvConstants.VARIABLES)).rend_template()
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.JINJA2_RENDER_FAILURE.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.JINJA2_RENDER_FAILURE.value), e)

        return Response(rendered_content, 200, mimetype="text/plain")

    @route('/deployments', methods=['GET'])
    def get_active_deployments(self):
        docker_utils = DockerUtils()
        active_deployments = docker_utils.get_active_deployments()
        app.logger.debug({"msg": {"active_deployments": f"{len(active_deployments)}"}})

        return Response(
            json.dumps(HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                               active_deployments)), 200, mimetype="application/json")

    @route('/deployments/prepare', methods=['PUT'])
    def receive_prepared_deployment_and_unpack(self):
        token = token_hex(8)
        io_utils = IOUtils()
        deployment_id = request.headers.get("Deployment-Id").lower() if request.headers.get("Deployment-Id") else token
        deploy_dir = f"{EnvInit.init.get(EnvConstants.DEPLOY_PATH)}/{deployment_id}"
        file_path = f"{deploy_dir}/archive.zip"
        file_content = request.get_data()
        # send here the complete env. The deployment template can be overridden at deploy start
        if not file_content:
            raise ApiExceptionDocker(ApiCode.EMPTY_REQUEST_BODY_PROVIDED.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.EMPTY_REQUEST_BODY_PROVIDED.value),
                                     ErrorMessage.HTTP_CODE.get(ApiCode.EMPTY_REQUEST_BODY_PROVIDED.value))

        try:
            io_utils.create_dir(deploy_dir)
            io_utils.write_to_file_binary(file_path, file_content)
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.UPLOAD_FILE_FAILURE.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.UPLOAD_FILE_FAILURE.value), e)
        try:
            shutil.unpack_archive(file_path, deploy_dir)
            io_utils.remove_file(file_path)
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.FOLDER_UNZIP_FAILURE.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.FOLDER_UNZIP_FAILURE.value), e)

        return Response(
            json.dumps(HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                               deployment_id)), 200, mimetype="application/json")

    @route('/deployments/cleanup', methods=['DELETE'])
    def cleanup_inactive_deployments(self):
        """ ! can be executed only after /deployments DELETE ! """
        try:
            deleted_folders = DockerUtils.folder_clean_up()
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.DEPLOYMENTS_FOLDER_CLEANUP_FAILURE.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.DEPLOYMENTS_FOLDER_CLEANUP_FAILURE.value), e)

        return Response(
            json.dumps(HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                               deleted_folders)), 200, mimetype="application/json")

    @route('/deployments', methods=['POST'])
    def start_deployment(self):
        docker_utils = DockerUtils()
        token = token_hex(8)
        deployment_id = request.headers.get("Deployment-Id").lower() if request.headers.get("Deployment-Id") else token
        deploy_dir = f"{EnvInit.init.get(EnvConstants.DEPLOY_PATH)}/{deployment_id}"
        file = f"{deploy_dir}/docker-compose.yml"
        header_key = 'Eureka-Server'
        eureka_server_header = request.headers.get(f"{header_key}")
        config_env_vars = EnvStartupSingleton.get_instance().get_config_env_vars()
        input_data = request.data.decode('UTF-8').strip()

        status = CmdUtils.run_cmd_shell_false(["docker", "ps"])
        if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
            raise ApiExceptionDocker(ApiCode.DOCKER_DAEMON_NOT_RUNNING.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.DOCKER_DAEMON_NOT_RUNNING.value),
                                     status.get('err'))

        active_deployments = docker_utils.get_active_deployments()
        if len(active_deployments) >= EnvInit.init.get(EnvConstants.MAX_DEPLOYMENTS):
            raise ApiExceptionDocker(ApiCode.MAX_DEPLOYMENTS_REACHED.value,
                                     ErrorMessage.HTTP_CODE.get(
                                         ApiCode.MAX_DEPLOYMENTS_REACHED.value) % str(EnvInit.init.get(EnvConstants.MAX_DEPLOYMENTS)),
                                     active_deployments)
        try:
            template_file_name = f"deployment_{deployment_id}.yml"
            template_file_path = f"{EnvInit.init.get(EnvConstants.TEMPLATES_DIR)}/{template_file_name}"
            app.logger.debug({"msg": {"file": template_file_path, "file_content": f"{input_data}"}})
            IOUtils.write_to_file(template_file_path, input_data)

            IOUtils.create_dir(deploy_dir)
            EnvironmentSingleton.get_instance().set_env_var(EnvConstants.TEMPLATE, template_file_name)
            env_vars = EnvironmentSingleton.get_instance().get_env_and_virtual_env()
            render = Render(env_vars.get(EnvConstants.TEMPLATE), env_vars.get(EnvConstants.VARIABLES))
            if config_env_vars.get(EnvConstants.EUREKA_SERVER) and config_env_vars.get(EnvConstants.APP_IP_PORT):
                # if {{app_ip_port}} and {{eureka_server}} then register that instance too
                if '{{app_ip_port}}' in input_data and '{{eureka_server}}' in input_data:
                    eureka_server = config_env_vars.get(EnvConstants.EUREKA_SERVER)
                    # header value overwrite the eureka server
                    if eureka_server_header:
                        eureka_server = eureka_server_header
                    input_data = render.get_jinja2env().get_template(env_vars.get(EnvConstants.TEMPLATE)).render({
                        "deployment_id": f"{deployment_id}",
                        "eureka_server": eureka_server,
                        "app_ip_port": config_env_vars.get(EnvConstants.APP_IP_PORT).split("/")[0]
                    })
            os.remove(template_file_path) if os.path.exists(template_file_path) else None
            app.logger.debug({"msg": {"file": file, "file_content": f"{input_data}"}})
            IOUtils.write_to_file(file, input_data) if input_data else None
            CmdUtils.run_cmd_detached(rf'''docker-compose -f {file} pull && docker-compose -f {file} up -d''')
        except Exception as e:
            app.logger.debug({"msg": docker_utils.down(file)})
            raise ApiExceptionDocker(ApiCode.DEPLOY_START_FAILURE.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.DEPLOY_START_FAILURE.value), e)

        DeploymentMetadataSingleton.get_instance() \
            .delete_metadata_for_inactive_deployments(DockerUtils.get_active_deployments())
        metadata = DeploymentReader.get_metadata_for_deployment(IOUtils.read_file(file=file))
        IOUtils.write_to_file_dict(f"{deploy_dir}/metadata.json", metadata)
        DeploymentMetadataSingleton.get_instance().set_metadata_for_deployment(deployment_id, metadata)

        return Response(
            json.dumps(HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                               deployment_id)), 200, mimetype="application/json")

    @route('/deployments/<template>/<variables>', methods=['POST'])
    def start_deployment_with_templates(self, template, variables):
        http = HttpResponse()
        docker_utils = DockerUtils()
        token = token_hex(8)
        deployment_id = request.headers.get("Deployment-Id").lower() if request.headers.get("Deployment-Id") else token
        deploy_dir = f"{EnvInit.init.get(EnvConstants.DEPLOY_PATH)}/{deployment_id}"
        file = f"{deploy_dir}/docker-compose.yml"

        try:
            input_json = request.get_json(force=True)
            for key, value in input_json.items():
                if key not in EnvironmentSingleton.get_instance().get_env():
                    EnvironmentSingleton.get_instance().set_env_var(str(key), str(value))
        except Exception as e:
            app.logger.debug(f"Could not parse the input from the request as JSON: {e.__str__()}")

        EnvironmentSingleton.get_instance().set_env_var(EnvConstants.TEMPLATE, template.strip())
        EnvironmentSingleton.get_instance().set_env_var(EnvConstants.VARIABLES, variables.strip())
        env_vars = EnvironmentSingleton.get_instance().get_env_and_virtual_env()
        app.logger.debug({"msg": {"template_file": env_vars.get(EnvConstants.TEMPLATE)}})
        app.logger.debug({"msg": {"variables_file": env_vars.get(EnvConstants.VARIABLES)}})

        status = CmdUtils.run_cmd_shell_false(["docker", "ps"])
        if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
            raise ApiExceptionDocker(ApiCode.DOCKER_DAEMON_NOT_RUNNING.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.DOCKER_DAEMON_NOT_RUNNING.value),
                                     status.get('err'))

        active_deployments = docker_utils.get_active_deployments()
        if len(active_deployments) >= EnvInit.init.get(EnvConstants.MAX_DEPLOYMENTS):
            raise ApiExceptionDocker(ApiCode.MAX_DEPLOYMENTS_REACHED.value,
                                     ErrorMessage.HTTP_CODE.get(
                                         ApiCode.MAX_DEPLOYMENTS_REACHED.value) % str(EnvInit.init.get(EnvConstants.MAX_DEPLOYMENTS)),
                                     active_deployments)
        try:
            r = Render(env_vars.get(EnvConstants.TEMPLATE),
                       env_vars.get(EnvConstants.VARIABLES))
            IOUtils.create_dir(deploy_dir)
            IOUtils.write_to_file(file, r.rend_template())
            CmdUtils.run_cmd_detached(rf'''docker-compose -f {file} pull && docker-compose -f {file} up -d''')
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.DEPLOY_START_FAILURE.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.DEPLOY_START_FAILURE.value), e)

        DeploymentMetadataSingleton.get_instance() \
            .delete_metadata_for_inactive_deployments(DockerUtils.get_active_deployments())
        metadata = DeploymentReader.get_metadata_for_deployment(IOUtils.read_file(file=file))
        IOUtils.write_to_file_dict(f"{deploy_dir}/metadata.json", metadata)
        DeploymentMetadataSingleton.get_instance().set_metadata_for_deployment(deployment_id, metadata)

        return Response(
            json.dumps(
                http.response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value), deployment_id)),
            200, mimetype="application/json")

    @route('/deployments/<env_id>', methods=['GET'])
    def get_deployment_status(self, env_id):
        env_id = env_id.lower()
        docker_utils = DockerUtils()
        env_id = env_id.strip()

        try:
            status = docker_utils.ps(env_id)
            if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
                raise Exception(status.get('err'))
            result = status.get('out').split("\n")[1:]
            app.logger.debug({"msg": status})
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.DEPLOY_STATUS_FAILURE.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.DEPLOY_STATUS_FAILURE.value), e)

        return Response(
            json.dumps(HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                               ActiveDeployment.docker_deployment(env_id, result))), 200,
            mimetype="application/json")

    @route('/deployments/<depl_id>', methods=['DELETE'])
    def delete_deployment_id(self, depl_id):
        depl_id = depl_id.strip()
        docker_utils = DockerUtils()
        depl_folder = f"{EnvInit.init.get(EnvConstants.DEPLOY_PATH)}/{depl_id}"
        file = f"{depl_folder}/docker-compose.yml"
        try:
            status = docker_utils.down(file)
            if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
                raise Exception(status.get('err'))
            app.logger.debug({"msg": status})
            status = docker_utils.ps(depl_id)
            result = status.get('out').split("\n")[1:]
            DeploymentMetadataSingleton.get_instance().delete_metadata_for_deployment(depl_id)
            IOUtils.remove_directory(f"{depl_folder}")
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.DEPLOY_STOP_FAILURE.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.DEPLOY_STOP_FAILURE.value), e)

        return Response(
            json.dumps(
                HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                        result)), 200, mimetype="application/json")

    @route('/deployments', methods=['DELETE'])
    def delete_all_deployments(self):
        docker_utils = DockerUtils()
        try:
            active_deployments = docker_utils.get_active_deployments()
            for deployment in active_deployments:
                depl_id = deployment.get('id')
                depl_folder = f"{EnvInit.init.get(EnvConstants.DEPLOY_PATH)}/{depl_id}"
                status = docker_utils.down(f"{depl_folder}/docker-compose.yml")
                if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
                    raise Exception(status.get('err'))
                app.logger.debug({"msg": status})
                DeploymentMetadataSingleton.get_instance().delete_metadata_for_deployment(depl_id)

            DockerUtils.folder_clean_up()
            result = docker_utils.get_active_deployments()
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.DEPLOY_STOP_FAILURE.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.DEPLOY_STOP_FAILURE.value), e)

        return Response(
            json.dumps(
                HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                        result)), 200, mimetype="application/json")

    @route('/file', methods=['GET'])
    def get_file(self):
        header_key = 'File-Path'

        file_path = request.headers.get(f"{header_key}")
        if not file_path:
            raise ApiExceptionDocker(ApiCode.HTTP_HEADER_NOT_PROVIDED.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % header_key,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % header_key)

        try:
            file_content = IOUtils.read_file(file_path)
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.GET_FILE_FAILURE.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.GET_FILE_FAILURE.value), e)
        return Response(file_content, 200, mimetype="text/plain")

    @route('/file', methods=['POST', 'PUT'])
    def upload_file(self):
        http = HttpResponse()
        io_utils = IOUtils()
        header_key = 'File-Path'
        file_content = request.get_data()
        file_path = request.headers.get(f"{header_key}")

        if not file_path:
            raise ApiExceptionDocker(ApiCode.HTTP_HEADER_NOT_PROVIDED.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % header_key,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % header_key)
        if not file_content:
            raise ApiExceptionDocker(ApiCode.EMPTY_REQUEST_BODY_PROVIDED.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.EMPTY_REQUEST_BODY_PROVIDED.value),
                                     ErrorMessage.HTTP_CODE.get(ApiCode.EMPTY_REQUEST_BODY_PROVIDED.value))

        try:
            io_utils.write_to_file_binary(file_path, file_content)
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.UPLOAD_FILE_FAILURE.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.UPLOAD_FILE_FAILURE.value), e)

        return Response(
            json.dumps(http.response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                     ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))), 200,
            mimetype="application/json")

    @route('/deployments/logs/<env_id>', methods=['GET'])
    def deploy_logs(self, env_id):
        env_id = env_id.lower()
        http = HttpResponse()
        docker_utils = DockerUtils()
        env_id = env_id.strip()
        env_id_dir = EnvInit.init.get(EnvConstants.DEPLOY_PATH) + f"/{env_id}"
        file = f"{env_id_dir}/docker-compose.yml"

        try:
            status = docker_utils.logs(file)
            app.logger.debug({"msg": status})
            if status.get('err'):
                raise Exception(status.get('err'))
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.GET_LOGS_FAILED.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.GET_LOGS_FAILED.value) % env_id, e)

        return Response(
            json.dumps(http.response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                     status.get('out'))), 200, mimetype="application/json")

    # must connect the container to the deployer network to be able to send http request
    @route('/deployments/network/<env_id>', methods=['POST', 'PUT'])
    def container_docker_network_connect(self, env_id):
        env_id = env_id.lower()
        http = HttpResponse()
        docker_utils = DockerUtils()
        headers = request.headers
        service_name = "container"

        if request.args.get('service') is not None:
            service_name = request.args.get('service')
        container_id = f"{env_id}_{service_name}_1"

        try:
            status = CmdUtils.run_cmd_shell_false(["docker", "network", "ls", "--filter", "name={}".format("deployer")])
            app.logger.debug({"msg": status})
            if not status.get('out'):
                raise Exception(status.get('err'))
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.GET_DEPLOYER_NETWORK_FAILED.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.GET_DEPLOYER_NETWORK_FAILED.value), e)

        try:
            deployer_network = status.get('out').split("\n")[1].split(" ")[0].strip()
            if headers.get("Docker-Network"):
                deployer_network = headers.get("Docker-Network")
            status = docker_utils.network_connect(deployer_network, container_id)

            if "already exists in network".lower() in status.get('err').lower():
                return Response(json.dumps(http.response(ApiCode.SUCCESS.value,
                                                         ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                                         "Success, already connected: " + status.get('err'))), 200,
                                mimetype="application/json")

            if "Error response from daemon".lower() in status.get('err').lower():
                raise Exception(status.get('err'))
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.CONTAINER_NET_CONNECT_FAILED.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.CONTAINER_NET_CONNECT_FAILED.value), e)
        return Response(
            json.dumps(
                http.response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                              status.get('out'))), 200, mimetype="application/json")

    @route('/deployments/network/<env_id>', methods=['DELETE'])
    def container_docker_network_disconnect(self, env_id):
        env_id = env_id.lower()
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
                raise Exception(status.get('err'))
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.GET_DEPLOYER_NETWORK_FAILED.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.GET_DEPLOYER_NETWORK_FAILED.value), e)

        try:
            deployer_network = status.get('out').split("\n")[1].split(" ")[0].strip()
            status = docker_utils.network_disconnect(deployer_network, container_id)

            if "is not connected to network".lower() in status.get('err').lower():
                return Response(json.dumps(http.response(ApiCode.SUCCESS.value,
                                                         ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                                         "Success, already disconnected: " + status.get('err'))), 200,
                                mimetype="application/json")

            if "Error response from daemon".lower() in status.get('err').lower():
                raise Exception(status.get('err'))
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.CONTAINER_NET_DISCONNECT_FAILED.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.CONTAINER_NET_DISCONNECT_FAILED.value), e)
        return Response(
            json.dumps(
                http.response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                              status.get('out'))), 200, mimetype="application/json")

    # here the requests are redirected to any container
    # url format: container/ENV_ID/the_url?port=8080&service=container
    # E.g.1 /container/2a1c9aa0451add84/uploadtestconfig
    @route('/container/<env_id>/<path:text>',
           methods=['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH'])
    def container_request(self, env_id, text):
        env_id = env_id.lower()
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
        except Exception as e:
            app.logger.debug(f"Could not get data from the request: {e.__str__}")

        complete_url = f"http://{container_id}:{container_port}/{container_url}"
        try:
            r = requests.request(url=complete_url, method=request.method, data=input_data, headers=headers, timeout=5)
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.CONTAINER_UNREACHABLE.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.CONTAINER_UNREACHABLE.value) % (
                                         service_name, service_name), e)
        return Response(r.text, r.status_code)

    @route('/command', methods=['POST', 'PUT'])
    def execute_command(self):
        input_data = request.data.decode("UTF-8", "replace").strip()

        if not input_data:
            raise ApiExceptionDocker(ApiCode.EMPTY_REQUEST_BODY_PROVIDED.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.EMPTY_REQUEST_BODY_PROVIDED.value),
                                     ErrorMessage.HTTP_CODE.get(ApiCode.EMPTY_REQUEST_BODY_PROVIDED.value))
        try:
            input_data_list = input_data.split("\n")
            input_data_list = list(map(lambda x: x.strip(), input_data_list))
            command_in_memory = CommandInMemory()
            response = command_in_memory.run_commands(input_data_list)
        except Exception as e:
            raise ApiExceptionDocker(ApiCode.COMMAND_EXEC_FAILURE.value,
                                     ErrorMessage.HTTP_CODE.get(ApiCode.COMMAND_EXEC_FAILURE.value), e)
        return Response(
            json.dumps(
                HttpResponse().response(ApiCode.SUCCESS.value, ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value),
                                        response)), 200, mimetype="application/json")

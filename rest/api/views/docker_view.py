import json
import logging
import os
import re
import sys
import traceback
from secrets import token_hex

import requests
from flask import request, Response, Flask
from flask_classful import FlaskView, route
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from fluent import sender

from about import properties
from entities.render import Render
from rest.api.apiresponsehelpers.active_deployments_response import ActiveDeployment
from rest.api.apiresponsehelpers.constants import Constants
from rest.api.apiresponsehelpers.error_codes import ErrorCodes
from rest.api.apiresponsehelpers.http_response import HttpResponse
from rest.api.definitions import unmodifiable_env_vars, docker_swagger_file_content
from rest.api.flask_config import Config
from rest.api.logginghelpers.message_dumper import MessageDumper
from rest.utils.cmd_utils import CmdUtils
from rest.utils.docker_utils import DockerUtils
from rest.utils.fluentd_utils import FluentdUtils
from rest.utils.io_utils import IOUtils


class DockerView(FlaskView):

    def __init__(self):
        self.app = Flask(__name__, instance_relative_config=False)
        self.app.config.from_object(Config)
        CORS(self.app)
        self.app.register_blueprint(self.get_swagger_blueprint(), url_prefix='/docker/api/docs')
        self.app.logger.setLevel(logging.DEBUG)
        self.logger = sender.FluentSender(properties.get('name'), host=properties["fluentd_ip"],
                                          port=int(properties["fluentd_port"]))
        self.fluentd_utils = FluentdUtils(self.logger)
        self.message_dumper = MessageDumper()

    def before_request(self, name, *args, **kwargs):
        ctx = self.app.app_context()
        ctx.g.cid = token_hex(8)
        self.message_dumper.set_correlation_id(ctx.g.cid)

        response = self.fluentd_utils.debug(tag="api", msg=self.message_dumper.dump(request=request))
        self.app.logger.debug(f"{response}")

    def after_request(self, name, http_response):
        headers = dict(http_response.headers)
        headers['Correlation-Id'] = self.message_dumper.get_correlation_id()
        http_response.headers = headers

        response = self.fluentd_utils.debug(tag="api", msg=self.message_dumper.dump(http_response))
        self.app.logger.debug(f"{response}")

        return http_response

    def get_swagger_blueprint(self):
        return get_swaggerui_blueprint(
            base_url='/docker/api/docs',
            api_url='/docker/swagger/swagger.yml',
            config={
                'app_name': "estuary-deployer"
            },
        )

    def index(self):
        return "docker"

    def get_view_fluentd_utils(self):
        return self.fluentd_utils

    def get_view_logger(self):
        return self.logger

    def get_view_app(self):
        return self.app

    @route('/swagger/swagger.yml')
    def swagger(self):
        return Response(docker_swagger_file_content, 200, mimetype="text/plain;charset=UTF-8")

    @route('/env')
    def get_env_vars(self):
        http = HttpResponse()
        return Response(
            json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), dict(os.environ))),
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

    @route('/env/<env_var>', methods=['GET'])
    def get_env_var(self, env_var):
        env_var = env_var.upper().strip()
        http = HttpResponse()
        try:
            response = Response(json.dumps(
                http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), os.environ[env_var])),
                200,
                mimetype="application/json")
        except Exception as e:
            result = "Exception({0})".format(e.__str__())
            response = Response(json.dumps(http.failure(Constants.GET_CONTAINER_ENV_VAR_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.GET_CONTAINER_ENV_VAR_FAILURE) % f"{env_var}",
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
            response = Response(json.dumps(http.failure(Constants.JINJA2_RENDER_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.JINJA2_RENDER_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/deployments', methods=['GET'])
    def get_active_deployments(self):
        docker_utils = DockerUtils()
        http = HttpResponse()
        active_deployments = docker_utils.get_active_deployments()
        self.app.logger.debug({"msg": {"active_deployments": f"{len(active_deployments)}"}})

        return Response(
            json.dumps(
                http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), active_deployments)),
            200, mimetype="application/json")

    @route('/deployments', methods=['POST'])
    def deploy_start(self):
        docker_utils = DockerUtils()
        http = HttpResponse()
        token = token_hex(8)
        dir = f"{Constants.DEPLOY_FOLDER_PATH}{token}"
        file = f"{dir}/{token}"
        header_key = 'Eureka-Server'
        eureka_server_header = request.headers.get(f"{header_key}")

        status = CmdUtils.run_cmd(["docker", "ps"])
        if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
            return Response(json.dumps(http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                                    ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING),
                                                    status.get('err'),
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        if os.environ.get("MAX_DEPLOYMENTS"):
            active_deployments = docker_utils.get_active_deployments()
            if len(active_deployments) >= int(os.environ.get("MAX_DEPLOYMENTS")):
                return Response(json.dumps(http.failure(Constants.MAX_DEPLOYMENTS_REACHED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.MAX_DEPLOYMENTS_REACHED) % os.environ.get(
                                                            "MAX_DEPLOYMENTS"), active_deployments,
                                                        f"Active deployments: {str(len(active_deployments))}")), 404,
                                mimetype="application/json")
        try:
            template_file_name = f"deployment_{token}.yml"
            input_data = request.data.decode('utf-8')
            template_file_path = f"{os.environ.get('TEMPLATES_DIR')}/{template_file_name}"
            IOUtils.write_to_file(template_file_path)
            IOUtils.write_to_file(template_file_path, input_data)

            IOUtils.create_dir(dir)
            os.environ['TEMPLATE'] = f"{template_file_name}"
            r = Render(os.environ.get('TEMPLATE'), os.environ.get('VARIABLES'))
            if os.environ.get('EUREKA_SERVER') and os.environ.get('APP_IP_PORT'):
                # if {{app_ip_port}} and {{eureka_server}} then register that instance too
                if '{{app_ip_port}}' in input_data and '{{eureka_server}}' in input_data:
                    eureka_server = os.environ.get('EUREKA_SERVER')
                    # header value overwrite the eureka server
                    if eureka_server_header:
                        eureka_server = eureka_server_header
                    input_data = r.get_jinja2env().get_template(os.environ.get('TEMPLATE')).render(
                        {"deployment_id": f"{token}",
                         "eureka_server": eureka_server,
                         "app_ip_port": os.environ.get('APP_IP_PORT').split("/")[0]
                         }
                    )
            self.app.logger.debug({"msg": {"file_content": f"{input_data}"}})
            if os.path.exists(template_file_path):
                os.remove(template_file_path)
            IOUtils.write_to_file(file, input_data)
            CmdUtils.run_cmd_detached(rf'''docker-compose -f {file} pull && docker-compose -f {file} up -d''')
            response = Response(
                json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), token)), 200,
                mimetype="application/json")
        except OSError  as e:
            result = "Exception({0})".format(e.__str__())
            response = Response(json.dumps(http.failure(Constants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
        except:
            result = "Exception({0})".format(sys.exc_info()[0])
            status = docker_utils.down(file)
            self.app.logger.debug({"msg": status})
            response = Response(json.dumps(http.failure(Constants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/deployments/<template>/<variables>', methods=['POST'])
    def deploy_start_env(self, template, variables):
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
        self.app.logger.debug({"msg": {"template_file": os.environ.get('TEMPLATE')}})
        self.app.logger.debug({"msg": {"variables_file": os.environ.get('VARIABLES')}})
        token = token_hex(8)
        dir = f"{Constants.DEPLOY_FOLDER_PATH}{token}"
        file = f"{dir}/{token}"
        http = HttpResponse()

        status = CmdUtils.run_cmd(["docker", "ps"])
        if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
            return Response(json.dumps(http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                                    ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING),
                                                    status.get('err'),
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        if os.environ.get("MAX_DEPLOYMENTS"):
            active_deployments = docker_utils.get_active_deployments()
            if len(active_deployments) >= int(os.environ.get("MAX_DEPLOYMENTS")):
                return Response(json.dumps(http.failure(Constants.MAX_DEPLOYMENTS_REACHED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.MAX_DEPLOYMENTS_REACHED) % os.environ.get(
                                                            "MAX_DEPLOYMENTS"), active_deployments,
                                                        f"Active deployments: {str(len(active_deployments))}")), 404,
                                mimetype="application/json")
        try:
            r = Render(os.environ.get('TEMPLATE'), os.environ.get('VARIABLES'))
            IOUtils.create_dir(dir)
            IOUtils.write_to_file(file)
            IOUtils.write_to_file(file, r.rend_template())
            CmdUtils.run_cmd_detached(rf'''docker-compose -f {file} pull && docker-compose -f {file} up -d''')
            result = str(token)
            response = Response(
                json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result)), 200,
                mimetype="application/json")
        except OSError as e:
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

    @route('/deployments/<env_id>', methods=['GET'])
    def deploy_status(self, env_id):
        env_id = env_id.strip()
        docker_utils = DockerUtils()
        http = HttpResponse()
        try:
            status = docker_utils.ps(env_id)
            if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
                return Response(json.dumps(http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING),
                                                        status.get('err'),
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
            result = status.get('out').split("\n")[1:-1]
            response = Response(
                json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS),
                                        ActiveDeployment.docker_deployment(env_id, result))), 200,
                mimetype="application/json")
            self.app.logger.debug({"msg": status})
        except OSError as e:
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

    @route('/deployments/<env_id>', methods=['DELETE'])
    def deploy_stop(self, env_id):
        env_id = env_id.strip()
        docker_utils = DockerUtils()
        file = f"{Constants.DEPLOY_FOLDER_PATH}{env_id}/{env_id}"
        http = HttpResponse()
        try:
            status = docker_utils.down(file)
            if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
                return Response(json.dumps(http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING),
                                                        status.get('err'),
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
            self.app.logger.debug({"msg": status})
            status = docker_utils.ps(env_id)
            result = status.get('out').split("\n")[1:-1]
            response = Response(
                json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result)), 200,
                mimetype="application/json")
        except OSError as e:
            result = "Exception({0})".format(e.__str__())
            response = Response(json.dumps(http.failure(Constants.DEPLOY_STOP_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_STOP_FAILURE), result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
        except:
            result = "Exception({0})".format(sys.exc_info()[0])
            response = Response(json.dumps(http.failure(Constants.DEPLOY_STOP_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_STOP_FAILURE), result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/file', methods=['GET'])
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

    @route('/file', methods=['POST', 'PUT'])
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

    @route('/deployments/logs/<env_id>', methods=['GET'])
    def deploy_logs(self, env_id):
        env_id = env_id.strip()
        env_id_dir = Constants.DEPLOY_FOLDER_PATH + env_id
        file = f"{env_id_dir}/{env_id}"
        docker_utils = DockerUtils()
        http = HttpResponse()

        try:
            status = docker_utils.logs(file)
            self.app.logger.debug({"msg": status})
            if status.get('err'):
                return Response(json.dumps(http.failure(Constants.GET_LOGS_FAILED,
                                                        ErrorCodes.HTTP_CODE.get(Constants.GET_LOGS_FAILED) % env_id,
                                                        status.get('err'),
                                                        status.get('err'))), 404, mimetype="application/json")
        except:
            exception = "Exception({0})".format(sys.exc_info()[0])
            return Response(json.dumps(http.failure(Constants.GET_LOGS_FAILED,
                                                    ErrorCodes.HTTP_CODE.get(Constants.GET_LOGS_FAILED) % env_id,
                                                    exception,
                                                    exception)), 404, mimetype="application/json")

        return Response(
            json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS),
                                    status.get('out').split("\n"))),
            200, mimetype="application/json")

    # must connect the container to the deployer network to be able to send http req to the test runner which runs in a initial segregated net
    @route('/deployments/network/<env_id>', methods=['POST', 'PUT'])
    def container_docker_network_connect(self, env_id):
        docker_utils = DockerUtils()
        http = HttpResponse()
        service_name = "container"
        container_id = f"{env_id}_{service_name}_1"
        try:
            # when creating deployer net, user must include 'deployer' in its name
            # otherwise this method should have docker net param regex through http header
            status = CmdUtils.run_cmd(["docker", "network", "ls", "--filter", "name={}".format("deployer")])
            self.app.logger.debug({"msg": status})
            if not status.get('out'):
                return Response(json.dumps(http.failure(Constants.GET_DEPLOYER_NETWORK_FAILED,
                                                        ErrorCodes.HTTP_CODE.get(Constants.GET_DEPLOYER_NETWORK_FAILED),
                                                        status.get('err'),
                                                        status.get('err'))), 404, mimetype="application/json")
            deployer_network = status.get('out').split("\n")[1].split(" ")[0].strip()
            status = docker_utils.network_connect(deployer_network, container_id)

            if "already exists in network".lower() in status.get('err').lower():
                return Response(json.dumps(http.success(Constants.SUCCESS,
                                                        ErrorCodes.HTTP_CODE.get(Constants.SUCCESS),
                                                        "Success, already connected: " + status.get('err'))), 200,
                                mimetype="application/json")

            if "Error response from daemon".lower() in status.get('err').lower():
                return Response(json.dumps(http.failure(Constants.CONTAINER_DEPLOYER_NET_CONNECT_FAILED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.CONTAINER_DEPLOYER_NET_CONNECT_FAILED),
                                                        status.get('err'),
                                                        status.get('err'))), 404, mimetype="application/json")
        except Exception as e:
            exception = "Exception({0})".format(sys.exc_info()[0])
            return Response(json.dumps(http.failure(Constants.CONTAINER_DEPLOYER_NET_CONNECT_FAILED,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        Constants.CONTAINER_DEPLOYER_NET_CONNECT_FAILED),
                                                    exception,
                                                    exception)), 404, mimetype="application/json")
        return Response(
            json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), status.get('out'))),
            200, mimetype="application/json")

    @route('/deployments/network/<env_id>', methods=['DELETE'])
    def container_docker_network_disconnect(self, env_id):
        docker_utils = DockerUtils()
        http = HttpResponse()
        service_name = "container"
        container_id = f"{env_id}_{service_name}_1"
        try:
            status = CmdUtils.run_cmd(["docker", "network", "ls", "--filter", "name={}".format("deployer")])
            self.app.logger.debug({"msg": status})
            if not status.get('out'):
                return Response(json.dumps(http.failure(Constants.GET_DEPLOYER_NETWORK_FAILED,
                                                        ErrorCodes.HTTP_CODE.get(Constants.GET_DEPLOYER_NETWORK_FAILED),
                                                        status.get('err'),
                                                        status.get('err'))), 404, mimetype="application/json")
            deployer_network = status.get('out').split("\n")[1].split(" ")[0].strip()
            status = docker_utils.network_disconnect(deployer_network, container_id)

            if "is not connected to network".lower() in status.get('err').lower():
                return Response(json.dumps(http.success(Constants.SUCCESS,
                                                        ErrorCodes.HTTP_CODE.get(Constants.SUCCESS),
                                                        "Success, already disconnected: " + status.get('err'))), 200,
                                mimetype="application/json")

            if "Error response from daemon".lower() in status.get('err').lower():
                return Response(json.dumps(http.failure(Constants.CONTAINER_DEPLOYER_NET_DISCONNECT_FAILED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.CONTAINER_DEPLOYER_NET_DISCONNECT_FAILED),
                                                        status.get('err'),
                                                        status.get('err'))), 404, mimetype="application/json")
        except Exception as e:
            exception = "Exception({0})".format(sys.exc_info()[0])
            return Response(json.dumps(http.failure(Constants.CONTAINER_DEPLOYER_NET_DISCONNECT_FAILED,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        Constants.CONTAINER_DEPLOYER_NET_DISCONNECT_FAILED),
                                                    exception,
                                                    exception)), 404, mimetype="application/json")
        return Response(
            json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), status.get('out'))),
            200, mimetype="application/json")

    # here the requests are redirected to any container
    # you can couple your own, just make sure the hostname is 'container'
    # url format: container/dockercomposeenvid/the_url
    # E.g1 /container/2a1c9aa0451add84/uploadtestconfig
    @route('/container/<env_id>/<path:text>', methods=['GET', 'POST', 'PUT', 'DELETE'])
    def container_request(self, env_id, text):
        http = HttpResponse()
        elements = text.strip().split("/")
        service_name = "container"
        container_id = f"{env_id}_{service_name}_1"
        input_data = ""
        headers = request.headers
        try:
            input_data = request.get_data()
        except:
            pass

        try:
            self.app.logger.debug(
                {"msg": {"uri": f'http://{container_id}:8080/{"/".join(elements)}', "method": request.method}})
            if request.method == 'GET':
                r = requests.get(f'http://{container_id}:8080/{"/".join(elements)}', headers=headers, timeout=5)
            elif request.method == 'POST':
                r = requests.post(f'http://{container_id}:8080/{"/".join(elements)}', data=input_data,
                                  headers=headers, timeout=5)
            elif request.method == 'PUT':
                r = requests.put(f'http://{container_id}:8080/{"/".join(elements)}', data=input_data,
                                 headers=headers, timeout=5)
            elif request.method == 'DELETE':
                r = requests.delete(f'http://{container_id}:8080/{"/".join(elements)}', headers=headers, timeout=5)
            else:
                pass

            response = Response(r.text, r.status_code, mimetype="application/json")

        except Exception as e:
            exception = "Exception({0})".format(sys.exc_info()[0])
            response = Response(json.dumps(http.failure(Constants.CONTAINER_UNREACHABLE,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.CONTAINER_UNREACHABLE) % (
                                                            service_name, service_name),
                                                        exception,
                                                        exception)), 404, mimetype="application/json")
        return response

    @route('/command', methods=['POST', 'PUT'])
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
            cmd = io_utils.get_filtered_list_regex(input_data.split("\n"), re.compile(
                r'(\s+|[^a-z]|^)rm\s+.*$'))[0:1]  # supports only one command at a time
            if not cmd:
                return Response(json.dumps(http.failure(Constants.EXEC_COMMAND_NOT_ALLOWED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.EXEC_COMMAND_NOT_ALLOWED) % input_data,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.EXEC_COMMAND_NOT_ALLOWED) % input_data,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
            command_dict = dict.fromkeys(cmd, {"details": {}})
            info_init["command"] = command_dict
            status = cmd_utils.run_cmd_shell_true(cmd[0].strip())
            info_init["command"][cmd[0].strip()]["details"] = json.loads(json.dumps(status))
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

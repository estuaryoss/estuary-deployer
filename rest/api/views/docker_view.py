import json
import logging
import os
import re
import sys
import traceback
from secrets import token_hex

import flask
import requests
from flask import request, Response, Flask
from flask_classful import FlaskView, route
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from fluent import sender

from about import properties
from entities.render import Render
from rest.api.apiresponsehelpers.active_deployments_response import ActiveDeployments
from rest.api.apiresponsehelpers.constants import Constants
from rest.api.apiresponsehelpers.error_codes import ErrorCodes
from rest.api.apiresponsehelpers.http_response import HttpResponse
from rest.api.definitions import env_vars, docker_swagger_file_content
from rest.api.flask_config import Config
from rest.api.logginghelpers.request_dumper import RequestDumper
from rest.api.views.routes_abc import Routes
from rest.utils.cmd_utils import CmdUtils
from rest.utils.docker_utils import DockerUtils
from rest.utils.fluentd_utils import FluentdUtils
from rest.utils.io_utils import IOUtils


class DockerView(FlaskView, Routes):

    def __init__(self):
        self.app = Flask(__name__, instance_relative_config=False)
        self.app.config.from_object(Config)
        CORS(self.app)
        self.app.register_blueprint(self.get_swagger_blueprint(), url_prefix='/docker/api/docs')
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
        return Response(docker_swagger_file_content, 200, mimetype="application/json")

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
                http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), os.environ[f"{envvar}"])),
                200,
                mimetype="application/json")
        except Exception as e:
            result = "Exception({0})".format(e.__str__())
            response = Response(json.dumps(http.failure(Constants.GET_CONTAINER_ENV_VAR_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.GET_CONTAINER_ENV_VAR_FAILURE) % f"{envvar}",
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
        docker_utils = DockerUtils()
        http = HttpResponse()
        active_deployments = docker_utils.get_active_deployments()
        # self.app.logger.debug('List of deployments: %s', json.dumps(IOUtils.get_list_dir(Constants.DEPLOY_FOLDER_PATH)))
        # for item in IOUtils().get_list_dir(Constants.DEPLOY_FOLDER_PATH):
        #     self.app.logger.debug('Containers list: %s', json.dumps(DockerUtils.ps(item).get('out').split("\n")[1]))
        self.app.logger.debug('Active deployments: %s', len(active_deployments))

        return Response(
            json.dumps(
                http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), active_deployments)),
            200, mimetype="application/json")

    @route('/deploystart', methods=['POST'])
    def deploy_start(self):
        docker_utils = DockerUtils()
        http = HttpResponse()

        token = token_hex(8)
        dir = f"{Constants.DEPLOY_FOLDER_PATH}{token}"
        file = f"{dir}/{token}"

        [out, err] = docker_utils.stats(r"""| awk -F ' ' '{sum+=$7} END {print sum}'""")
        self.app.logger.debug('Max memory out: %s', out)
        self.app.logger.debug('Max memory err: %s', err)
        if "Cannot connect to the Docker daemon".lower() in err.lower():
            return Response(json.dumps(http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                                    ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")

        if os.environ.get("MAX_DEPLOY_MEMORY"):
            if int(float(out)) >= int(os.environ.get("MAX_DEPLOY_MEMORY")):
                return Response(json.dumps(http.failure(Constants.MAX_DEPLOY_MEMORY_REACHED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.MAX_DEPLOY_MEMORY_REACHED) % os.environ.get(
                                                            "MAX_DEPLOY_MEMORY"),
                                                        "Used memory: " + out.strip() + " percent",
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
            # for testrunner deployed with deployer, other deployments will remain unchanged
            if 'testrunner' in input_data and os.environ.get('EUREKA_SERVER') is not None:
                if '{{app_ip_port}}' in input_data and '{{eureka_server}}' in input_data:
                    input_data = r.get_jinja2env().get_template(os.environ.get('TEMPLATE')).render(
                        {"deployment_id": f"{token}",
                         "app_ip_port": os.environ.get('APP_IP_PORT').split("/")[0],
                         "eureka_server": os.environ.get('EUREKA_SERVER')
                         }
                    )
            self.app.logger.debug('File content: %s', input_data)
            CmdUtils.run_cmd(["rm", "-rf", f"{template_file_path}"])
            IOUtils.write_to_file(file, input_data)
            CmdUtils.run_cmd_detached(rf'''docker-compose -f {file} pull && docker-compose -f {file} up -d''')
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
            status = docker_utils.down(file)
            self.app.logger.debug('Output: %s', status.get('out'))
            self.app.logger.debug('Error: %s', status.get('err'))
            response = Response(json.dumps(http.failure(Constants.DEPLOY_START_FAILURE,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE),
                                                        result,
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")

        return response

    @route('/deploystartenv/<template>/<variables>', methods=['POST'])
    def deploy_start_env(self, template, variables):
        docker_utils = DockerUtils()
        try:
            input_json = request.get_json(force=True)
            for key, value in input_json.items():
                if key not in env_vars:
                    os.environ[str(key)] = str(value)
        except:
            pass

        os.environ['TEMPLATE'] = template.strip()
        os.environ['VARIABLES'] = variables.strip()
        self.app.logger.debug("Templates: " + os.environ.get('TEMPLATE'))
        self.app.logger.debug("Variables: " + os.environ.get('VARIABLES'))
        token = token_hex(8)
        dir = f"{Constants.DEPLOY_FOLDER_PATH}{token}"
        file = f"{dir}/{token}"
        http = HttpResponse()

        [out, err] = docker_utils.stats(r"""| awk -F ' ' '{sum+=$7} END {print sum}'""")
        self.app.logger.debug('Max memory out: %s', out)
        self.app.logger.debug('Max memory err: %s', err)
        if "Cannot connect to the Docker daemon".lower() in err.lower():
            return Response(json.dumps(http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                                    ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        if int(float(out)) >= int(os.environ.get('MAX_DEPLOY_MEMORY')):
            return Response(json.dumps(http.failure(Constants.MAX_DEPLOY_MEMORY_REACHED,
                                                    ErrorCodes.HTTP_CODE.get(Constants.MAX_DEPLOY_MEMORY_REACHED) % int(
                                                        os.environ.get('MAX_DEPLOY_MEMORY')),
                                                    "Used memory: " + out.strip() + " percent",
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
            # [out, err] = docker_utils.docker_up(file)
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
        docker_utils = DockerUtils()
        http = HttpResponse()
        os.environ['TEMPLATE'] = template.strip()
        os.environ['VARIABLES'] = variables.strip()
        self.app.logger.debug("Templates: " + os.environ.get('TEMPLATE'))
        self.app.logger.debug("Variables: " + os.environ.get('VARIABLES'))
        token = token_hex(8)
        dir = f"{Constants.DEPLOY_FOLDER_PATH}{token}"
        file = f"{dir}/{token}"

        [out, err] = docker_utils.stats(r"""| awk -F ' ' '{sum+=$7} END {print sum}'""")
        self.app.logger.debug('Max memory out: %s', out)
        self.app.logger.debug('Max memory err: %s', err)
        if "Cannot connect to the Docker daemon".lower() in err.lower():
            return Response(json.dumps(http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                                    ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        if int(float(out)) >= int(os.environ.get("MAX_DEPLOY_MEMORY")):
            return Response(json.dumps(http.failure(Constants.MAX_DEPLOY_MEMORY_REACHED,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        Constants.MAX_DEPLOY_MEMORY_REACHED) % os.environ.get(
                                                        "MAX_DEPLOY_MEMORY"),
                                                    "Used memory: " + out.strip() + " percent",
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
            # [out, err] = docker_utils.docker_up(file)
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
        docker_utils = DockerUtils()
        http = HttpResponse()
        try:
            status = docker_utils.ps(id)
            if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
                return Response(json.dumps(http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING),
                                                        status.get('err'),
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
            result = status.get('out').split("\n")[1:-1]
            response = Response(
                json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS),
                                        ActiveDeployments.docker_deployment(id, result))), 200,
                mimetype="application/json")
            self.app.logger.debug('Output: %s', status.get('out'))
            self.app.logger.debug('Error: %s', status.get('err'))
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

    @route('/deploystop/<id>', methods=['GET'])
    def deploy_stop(self, id):
        id = id.strip()
        docker_utils = DockerUtils()
        file = f"{Constants.DEPLOY_FOLDER_PATH}{id}/{id}"
        http = HttpResponse()
        try:
            status = docker_utils.down(file)
            if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
                return Response(json.dumps(http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                                        ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING),
                                                        status.get('err'),
                                                        str(traceback.format_exc()))), 404, mimetype="application/json")
            self.app.logger.debug('Output: %s', status.get('out'))
            self.app.logger.debug('Error: %s', status.get('err'))
            status = docker_utils.ps(id)
            result = status.get('out').split("\n")[1:-1]
            response = Response(
                json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result)), 200,
                mimetype="application/json")
        except FileNotFoundError as e:
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

    @route('/getcontainerfile/<id>/<container_service_name>', methods=['GET', 'POST'])
    def get_file_from_container(self, id, container_service_name):
        id = id.strip()
        container_service_name = container_service_name.strip()
        docker_utils = DockerUtils()
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
        container_id = id + "_" + container_service_name + "_1"
        self.app.logger.debug('cid: %s', container_id)
        status = docker_utils.exec(container_id, ["sh", "-c", f"cat {file_path}"])
        # [out, err] = docker_utils.docker_cp(id, framework_container_service_name, file)
        self.app.logger.debug('Output: %s', status.get('out'))
        self.app.logger.debug('Error: %s', status.get('err'))
        if "Cannot connect to the Docker daemon".lower() in status.get('err').lower():
            return Response(json.dumps(http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                                    ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING),
                                                    status.get('err'),
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        if "No such container".lower() in status.get('err').lower():
            return Response(json.dumps(http.failure(Constants.GET_CONTAINER_FILE_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                                                        file_path, container_id),
                                                    ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                                                        file_path, container_id),
                                                    status.get('err'))), 404, mimetype="application/json")
        elif "No such file".lower() in status.get('err').lower():
            return Response(json.dumps(http.failure(Constants.GET_CONTAINER_FILE_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                                                        file_path, container_id),
                                                    ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                                                        file_path, container_id),
                                                    status.get('err'))), 404, mimetype="application/json")
        elif "Is a directory".lower() in status.get('err').lower():
            return Response(json.dumps(http.failure(Constants.GET_CONTAINER_FILE_FAILURE_IS_DIR,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        Constants.GET_CONTAINER_FILE_FAILURE_IS_DIR) % (
                                                        file_path, container_id),
                                                    ErrorCodes.HTTP_CODE.get(
                                                        Constants.GET_CONTAINER_FILE_FAILURE_IS_DIR) % (
                                                        file_path, container_id),
                                                    status.get('err'))), 404, mimetype="application/json")
        else:
            pass

        return Response(status.get('out'), 200, mimetype="text/plain")

    @route('/getcontainerfolder/<id>/<container_service_name>', methods=['GET', 'POST'])
    def get_folder_from_container(self, id, container_service_name):
        id = id.strip()
        container_service_name = container_service_name.strip()
        docker_utils = DockerUtils()
        http = HttpResponse()
        header_key = 'Folder-Path'

        folder_path = request.headers.get(f"{header_key}")
        if not folder_path:
            return Response(json.dumps(http.failure(Constants.HTTP_HEADER_NOT_PROVIDED,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        Constants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        Constants.HTTP_HEADER_NOT_PROVIDED) % header_key,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        container_id = id + "_" + container_service_name + "_1"
        self.app.logger.debug('cid: %s', container_id)
        [out, err] = docker_utils.cp(id, container_service_name, folder_path)
        self.app.logger.debug('Output: %s', out)
        self.app.logger.debug('Error: %s', err)
        if "Cannot connect to the Docker daemon".lower() in err.lower():
            return Response(json.dumps(http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                                    ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        if "No such container".lower() in err.lower():
            docker_utils.exec(container_id, f" rm -rf {id}")
            return Response(json.dumps(http.failure(Constants.GET_CONTAINER_FILE_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                                                        folder_path, container_id),
                                                    ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                                                        folder_path, container_id),
                                                    err)), 404, mimetype="application/json")
        elif "No such file".lower() in err.lower():
            return Response(json.dumps(http.failure(Constants.GET_CONTAINER_FILE_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                                                        folder_path, container_id),
                                                    ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                                                        folder_path, container_id),
                                                    err)), 404, mimetype="application/json")
        else:
            self.app.logger.debug('Out: %s', out)

        try:
            path = f"/tmp/{id}/" + folder_path.split("/")[-1]
            IOUtils.zip_file(id, path)
        except FileNotFoundError as e:
            result = "Exception({0})".format(e.__str__())
            return Response(json.dumps(http.failure(Constants.GET_FILE_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        Constants.GET_FILE_FAILURE), result,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        except:
            result = "Exception({0})".format(sys.exc_info()[0])
            return Response(json.dumps(http.failure(Constants.FOLDER_ZIP_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(Constants.FOLDER_ZIP_FAILURE), result,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        return flask.send_file(
            f"/tmp/{id}.zip",
            mimetype='application/zip',
            as_attachment=True), 200

    @route('/deploylogs/<id>', methods=['GET'])
    def deploy_logs(self, id):
        id = id.strip()
        dir = f"{Constants.DEPLOY_FOLDER_PATH}{id}"
        file = f"{dir}/{id}"
        docker_utils = DockerUtils()
        http = HttpResponse()

        try:
            status = docker_utils.logs(file)
            self.app.logger.debug('Output: %s', status.get('out'))
            self.app.logger.debug('Error: %s', status.get('err'))
            if status.get('err'):
                return Response(json.dumps(http.failure(Constants.GET_LOGS_FAILED,
                                                        ErrorCodes.HTTP_CODE.get(Constants.GET_LOGS_FAILED) % id,
                                                        status.get('err'),
                                                        status.get('err'))), 404, mimetype="application/json")
        except:
            exception = "Exception({0})".format(sys.exc_info()[0])
            return Response(json.dumps(http.failure(Constants.GET_LOGS_FAILED,
                                                    ErrorCodes.HTTP_CODE.get(Constants.GET_LOGS_FAILED) % id, exception,
                                                    exception)), 404, mimetype="application/json")

        return Response(
            json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS),
                                    status.get('out').split("\n"))),
            200, mimetype="application/json")

    # must connect the test runner to the deployer network to be able to send http req to the test runner which runs in a initial segregated net
    @route('/testrunnernetconnect/<id>', methods=['GET'])
    def testrunner_docker_network_connect(self, id):
        docker_utils = DockerUtils()
        http = HttpResponse()
        container_id = f"{id}_testrunner_1"
        try:
            status = CmdUtils.run_cmd(["bash", "-c",
                                       r'''docker network ls | grep deployer | awk '{print $2}' | head -1'''])
            self.app.logger.debug("Out: " + status.get('out'))
            self.app.logger.debug("Err: " + status.get('err'))
            if not status.get('out'):
                return Response(json.dumps(http.failure(Constants.GET_DEPLOYER_NETWORK_FAILED,
                                                        ErrorCodes.HTTP_CODE.get(Constants.GET_DEPLOYER_NETWORK_FAILED),
                                                        status.get('err'),
                                                        status.get('err'))), 404, mimetype="application/json")
            deployer_network = status.get('out').strip()
            [out, err] = docker_utils.network_connect(deployer_network, container_id)

            if "already exists in network".lower() in err.lower():
                return Response(json.dumps(http.success(Constants.SUCCESS,
                                                        ErrorCodes.HTTP_CODE.get(Constants.SUCCESS),
                                                        "Success, already connected: " + err)), 200,
                                mimetype="application/json")

            if "Error response from daemon".lower() in err.lower():
                return Response(json.dumps(http.failure(Constants.TESTRUNNER_CONNECT_TO_DEPLOYER_NETWORK_FAILED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.TESTRUNNER_CONNECT_TO_DEPLOYER_NETWORK_FAILED),
                                                        err,
                                                        err)), 404, mimetype="application/json")
        except Exception as e:
            exception = "Exception({0})".format(sys.exc_info()[0])
            return Response(json.dumps(http.failure(Constants.TESTRUNNER_CONNECT_TO_DEPLOYER_NETWORK_FAILED,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        Constants.TESTRUNNER_CONNECT_TO_DEPLOYER_NETWORK_FAILED),
                                                    exception,
                                                    exception)), 404, mimetype="application/json")
        return Response(json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), out)),
                        200, mimetype="application/json")

    @route('/testrunnernetdisconnect/<id>', methods=['GET'])
    def testrunner_docker_network_disconnect(self, id):
        docker_utils = DockerUtils()
        http = HttpResponse()
        container_id = f"{id}_estuary-testrunner_1"
        try:
            status = CmdUtils.run_cmd(["bash", "-c",
                                       r'''docker network ls | grep deployer | awk '{print $2}' | head -1'''])
            self.app.logger.debug("Out: " + status.get('out'))
            self.app.logger.debug("Err: " + status.get('err'))
            if not status.get('out'):
                return Response(json.dumps(http.failure(Constants.GET_DEPLOYER_NETWORK_FAILED,
                                                        ErrorCodes.HTTP_CODE.get(Constants.GET_DEPLOYER_NETWORK_FAILED),
                                                        status.get('err'),
                                                        status.get('err'))), 404, mimetype="application/json")
            deployer_network = status.get('out').strip()
            [out, err] = docker_utils.network_disconnect(deployer_network, container_id)

            if "is not connected to network".lower() in err.lower():
                return Response(json.dumps(http.success(Constants.SUCCESS,
                                                        ErrorCodes.HTTP_CODE.get(Constants.SUCCESS),
                                                        "Success, already disconnected: " + err)), 200,
                                mimetype="application/json")

            if "Error response from daemon".lower() in err.lower():
                return Response(json.dumps(http.failure(Constants.TESTRUNNER_DISCONNECT_TO_DEPLOYER_NETWORK_FAILED,
                                                        ErrorCodes.HTTP_CODE.get(
                                                            Constants.TESTRUNNER_DISCONNECT_TO_DEPLOYER_NETWORK_FAILED),
                                                        err,
                                                        err)), 404, mimetype="application/json")
        except Exception as e:
            exception = "Exception({0})".format(sys.exc_info()[0])
            return Response(json.dumps(http.failure(Constants.TESTRUNNER_DISCONNECT_TO_DEPLOYER_NETWORK_FAILED,
                                                    ErrorCodes.HTTP_CODE.get(
                                                        Constants.TESTRUNNER_DISCONNECT_TO_DEPLOYER_NETWORK_FAILED),
                                                    exception,
                                                    exception)), 404, mimetype="application/json")
        return Response(json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), out)),
                        200, mimetype="application/json")

    # here the requests are redirected to the testrunner container
    # you can couple your own
    # url format: yourservicenameindockercompose/dockercomposeenvid/the_url
    # E.g1 /testrunner/2a1c9aa0451add84/uploadtestconfig
    # E.g2 /testrunner/yourcustomtestrunnerservice/yourownaction
    @route('/testrunner/<id>/<path:text>', methods=['GET', 'POST'])
    def testrunner_request(self, id, text):
        http = HttpResponse()
        elements = text.strip().split("/")
        container_id = f"{id}_testrunner_1"
        input_data = ""
        headers = {'Content-type': 'application/json'}
        try:
            input_data = request.get_data()
            headers = request.headers
        except:
            pass

        try:
            self.app.logger.debug(f'http://{container_id}:8080/{"/".join(elements)}, Method={request.method}')
            if request.method == 'GET':
                r = requests.get(f'http://{container_id}:8080/{"/".join(elements)}', timeout=5)
            elif request.method == 'POST':
                r = requests.post(f'http://{container_id}:8080/{"/".join(elements)}', data=input_data,
                                  headers=headers, timeout=5)
            else:
                pass

            response = Response(r.text, r.status_code, mimetype="application/json")

        except Exception as e:
            exception = "Exception({0})".format(sys.exc_info()[0])
            response = Response(json.dumps(http.failure(Constants.TESTRUNNER_TIMEOUT,
                                                        ErrorCodes.HTTP_CODE.get(Constants.TESTRUNNER_TIMEOUT),
                                                        exception,
                                                        exception)), 404, mimetype="application/json")
        return response

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

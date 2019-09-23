import json
import os
import sys
import traceback
from secrets import token_hex

import flask
import requests
from flask import request, Response

from about import properties
from entities.render import Render
from rest.api import create_app
from rest.api.apiresponsehelpers.active_deployments_response import ActiveDeployments
from rest.api.apiresponsehelpers.constants import Constants
from rest.api.apiresponsehelpers.error_codes import ErrorCodes
from rest.api.apiresponsehelpers.http_response import HttpResponse
from rest.api.definitions import env_vars
from rest.utils.cmd_utils import CmdUtils
from rest.utils.docker_utils import DockerUtils
from rest.utils.io_utils import IOUtils

app = create_app()


@app.route('/swagger/swagger.yml')
def get_swagger():
    return app.send_static_file("swagger.yml")


@app.route('/env')
def get_vars():
    http = HttpResponse()
    return Response(json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), env_vars)),
                    200, mimetype="application/json")


@app.route('/ping')
def ping():
    http = HttpResponse()
    return Response(json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), "pong")),
                    200, mimetype="application/json")


@app.route('/about')
def about():
    http = HttpResponse()
    return Response(
        json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), properties["name"])),
        200, mimetype="application/json")


@app.route('/rend/<template>/<variables>', methods=['GET'])
def get_content(template, variables):
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
                                                    ErrorCodes.HTTP_CODE.get(Constants.JINJA2_RENDER_FAILURE), result,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")

    return response


@app.route('/rendwithenv/<template>/<variables>', methods=['POST'])
def get_content_with_env(template, variables):
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
                                                    ErrorCodes.HTTP_CODE.get(Constants.JINJA2_RENDER_FAILURE), result,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")

    return response


@app.route('/getdeploymentinfo', methods=['GET'])
def get_active_deployments():
    docker_utils = DockerUtils()
    http = HttpResponse()
    active_deployments = docker_utils.get_active_deployments()
    app.logger.debug('Active deployments: %s', len(active_deployments))

    return Response(
        json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), active_deployments)),
        200, mimetype="application/json")


@app.route('/deploystart', methods=['POST'])
def deploy_start_file_from_client():
    docker_utils = DockerUtils()
    http = HttpResponse()

    token = token_hex(8)
    dir = f"{Constants.DOCKER_PATH}{token}"
    file = f"{dir}/{token}"

    [out, err] = docker_utils.docker_stats(r"""| awk -F ' ' '{sum+=$7} END {print sum}'""")
    app.logger.debug('Max memory out: %s', out)
    app.logger.debug('Max memory err: %s', err)
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
        app.logger.debug('File content: %s', input_data)
        CmdUtils.run_cmd(["rm", "-rf", f"{template_file_path}"])
        IOUtils.write_to_file(file, input_data)
        CmdUtils.run_cmd_detached(rf'''docker-compose -f {file} pull && docker-compose -f {file} up -d''')
        response = Response(
            json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), token)), 200,
            mimetype="application/json")
    except FileNotFoundError as e:
        result = "Exception({0})".format(e.__str__())
        response = Response(json.dumps(http.failure(Constants.DEPLOY_START_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE), result,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
    except:
        result = "Exception({0})".format(sys.exc_info()[0])
        [out, err] = docker_utils.docker_down(file)
        app.logger.debug('Output: %s', out)
        app.logger.debug('Error: %s', err)
        response = Response(json.dumps(http.failure(Constants.DEPLOY_START_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE), result,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")

    return response


@app.route('/deploystartenv/<template>/<variables>', methods=['POST'])
def deploy_with_env_file_from_server(template, variables):
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
    app.logger.debug("Templates: " + os.environ.get('TEMPLATE'))
    app.logger.debug("Variables: " + os.environ.get('VARIABLES'))
    token = token_hex(8)
    dir = f"{Constants.DOCKER_PATH}{token}"
    file = f"{dir}/{token}"
    http = HttpResponse()

    [out, err] = docker_utils.docker_stats(r"""| awk -F ' ' '{sum+=$7} END {print sum}'""")
    app.logger.debug('Max memory out: %s', out)
    app.logger.debug('Max memory err: %s', err)
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
                                                    ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE), result,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
    except:
        result = "Exception({0})".format(sys.exc_info()[0])
        response = Response(json.dumps(http.failure(Constants.DEPLOY_START_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE), result,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")

    return response


@app.route('/deploystart/<template>/<variables>', methods=['GET'])
def deploy_start_file_from_server(template, variables):
    docker_utils = DockerUtils()
    http = HttpResponse()
    os.environ['TEMPLATE'] = template.strip()
    os.environ['VARIABLES'] = variables.strip()
    app.logger.debug("Templates: " + os.environ.get('TEMPLATE'))
    app.logger.debug("Variables: " + os.environ.get('VARIABLES'))
    token = token_hex(8)
    dir = f"{Constants.DOCKER_PATH}{token}"
    file = f"{dir}/{token}"

    [out, err] = docker_utils.docker_stats(r"""| awk -F ' ' '{sum+=$7} END {print sum}'""")
    app.logger.debug('Max memory out: %s', out)
    app.logger.debug('Max memory err: %s', err)
    if "Cannot connect to the Docker daemon".lower() in err.lower():
        return Response(json.dumps(http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                                ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                                                str(traceback.format_exc()))), 404, mimetype="application/json")
    if int(float(out)) >= int(os.environ.get("MAX_DEPLOY_MEMORY")):
        return Response(json.dumps(http.failure(Constants.MAX_DEPLOY_MEMORY_REACHED,
                                                ErrorCodes.HTTP_CODE.get(
                                                    Constants.MAX_DEPLOY_MEMORY_REACHED) % os.environ.get(
                                                    "MAX_DEPLOY_MEMORY"), "Used memory: " + out.strip() + " percent",
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
                                                    ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE), result,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
    except:
        result = "Exception({0})".format(sys.exc_info()[0])
        response = Response(json.dumps(http.failure(Constants.DEPLOY_START_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE), result,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")

    return response


@app.route('/deploystatus/<id>', methods=['GET'])
def deploy_status(id):
    id = id.strip()
    docker_utils = DockerUtils()
    http = HttpResponse()
    try:
        [out, err] = docker_utils.docker_ps(id)
        if "Cannot connect to the Docker daemon".lower() in err.lower():
            return Response(json.dumps(http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                                    ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        result = out.split("\n")[1:-1]
        response = Response(
            json.dumps(http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS),
                                    ActiveDeployments.active_deployment(id, result))), 200,
            mimetype="application/json")
        app.logger.debug('Output: %s', out)
        app.logger.debug('Error: %s', err)
    except FileNotFoundError as e:
        result = "Exception({0})".format(e.__str__())
        response = Response(json.dumps(http.failure(Constants.DEPLOY_STATUS_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_STATUS_FAILURE), result,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
    except:
        result = "Exception({0})".format(sys.exc_info()[0])
        response = Response(json.dumps(http.failure(Constants.DEPLOY_STATUS_FAILURE,
                                                    ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_STATUS_FAILURE), result,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")

    return response


@app.route('/deploystop/<id>', methods=['GET'])
def deploy_stop(id):
    id = id.strip()
    docker_utils = DockerUtils()
    file = f"{Constants.DOCKER_PATH}{id}/{id}"
    http = HttpResponse()
    try:
        [out, err] = docker_utils.docker_down(file)
        if "Cannot connect to the Docker daemon".lower() in err.lower():
            return Response(json.dumps(http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                                    ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                                                    str(traceback.format_exc()))), 404, mimetype="application/json")
        app.logger.debug('Output: %s', out)
        app.logger.debug('Error: %s', err)
        [out, err] = docker_utils.docker_ps(id)
        result = out.split("\n")[1:-1]
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


@app.route('/getdeployerfile', methods=['POST'])
def get_deployer_file():
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
                                                  ErrorCodes.HTTP_CODE.get(Constants.GET_ESTUARY_DEPLOYER_FILE_FAILURE),
                                                  exception,
                                                  str(traceback.format_exc()))), 404, mimetype="application/json")
    return result


@app.route('/getcontainerfile/<id>/<container_service_name>', methods=['POST'])
def get_results_file(id, container_service_name):
    id = id.strip()
    container_service_name = container_service_name.strip()
    docker_utils = DockerUtils()
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
    container_id = id + "_" + container_service_name + "_1"
    app.logger.debug('cid: %s', container_id)
    [out, err] = docker_utils.docker_exec(container_id, ["sh", "-c", f"cat {file}"])
    # [out, err] = docker_utils.docker_cp(id, framework_container_service_name, file)
    app.logger.debug('Output: %s', out)
    app.logger.debug('Error: %s', err)
    if "Cannot connect to the Docker daemon".lower() in err.lower():
        return Response(json.dumps(http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                                ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                                                str(traceback.format_exc()))), 404, mimetype="application/json")
    if "No such container".lower() in err.lower():
        return Response(json.dumps(http.failure(Constants.GET_CONTAINER_FILE_FAILURE,
                                                ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                                                    file, container_id),
                                                ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                                                    file, container_id),
                                                err)), 404, mimetype="application/json")
    elif "No such file".lower() in err.lower():
        return Response(json.dumps(http.failure(Constants.GET_CONTAINER_FILE_FAILURE,
                                                ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                                                    file, container_id),
                                                ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                                                    file, container_id),
                                                err)), 404, mimetype="application/json")
    elif "Is a directory".lower() in err.lower():
        return Response(json.dumps(http.failure(Constants.GET_CONTAINER_FILE_FAILURE_IS_DIR,
                                                ErrorCodes.HTTP_CODE.get(
                                                    Constants.GET_CONTAINER_FILE_FAILURE_IS_DIR) % (
                                                    file, container_id),
                                                ErrorCodes.HTTP_CODE.get(
                                                    Constants.GET_CONTAINER_FILE_FAILURE_IS_DIR) % (
                                                    file, container_id),
                                                err)), 404, mimetype="application/json")
    else:
        pass

    return Response(out, 200, mimetype="text/plain")


@app.route('/getcontainerfolder/<id>/<container_service_name>', methods=['POST'])
def get_container_folder(id, container_service_name):
    id = id.strip()
    container_service_name = container_service_name.strip()
    docker_utils = DockerUtils()
    http = HttpResponse()
    try:
        input_json = request.get_json(force=True)
        folder = input_json["folder"]
    except Exception as e:
        exception = "Exception({0})".format(sys.exc_info()[0])
        return Response(json.dumps(http.failure(Constants.MISSING_PARAMETER_POST,
                                                ErrorCodes.HTTP_CODE.get(
                                                    Constants.MISSING_PARAMETER_POST) % "folder", exception,
                                                str(traceback.format_exc()))), 404, mimetype="application/json")
    container_id = id + "_" + container_service_name + "_1"
    app.logger.debug('cid: %s', container_id)
    [out, err] = docker_utils.docker_cp(id, container_service_name, folder)
    app.logger.debug('Output: %s', out)
    app.logger.debug('Error: %s', err)
    if "Cannot connect to the Docker daemon".lower() in err.lower():
        return Response(json.dumps(http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                                ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                                                str(traceback.format_exc()))), 404, mimetype="application/json")
    if "No such container".lower() in err.lower():
        docker_utils.docker_exec(container_id, f" rm -rf {id}")
        return Response(json.dumps(http.failure(Constants.GET_CONTAINER_FILE_FAILURE,
                                                ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                                                    folder, container_id),
                                                ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                                                    folder, container_id),
                                                err)), 404, mimetype="application/json")
    elif "No such file".lower() in err.lower():
        return Response(json.dumps(http.failure(Constants.GET_CONTAINER_FILE_FAILURE,
                                                ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                                                    folder, container_id),
                                                ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                                                    folder, container_id),
                                                err)), 404, mimetype="application/json")
    else:
        app.logger.debug('Out: %s', out)

    try:
        path = f"/tmp/{id}/" + folder.split("/")[-1]
        IOUtils.zip_file(id, path)
    except FileNotFoundError as e:
        result = "Exception({0})".format(e.__str__())
        return Response(json.dumps(http.failure(Constants.GET_ESTUARY_DEPLOYER_FILE_FAILURE,
                                                ErrorCodes.HTTP_CODE.get(
                                                    Constants.GET_ESTUARY_DEPLOYER_FILE_FAILURE), result,
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


@app.route('/deploylogs/<id>', methods=['GET'])
def deploy_logs(id):
    id = id.strip()
    dir = f"{Constants.DOCKER_PATH}{id}"
    file = f"{dir}/{id}"
    docker_utils = DockerUtils()
    http = HttpResponse()

    try:
        [out, err] = docker_utils.docker_logs(file)
        app.logger.debug('Output: %s', out)
        app.logger.debug('Error: %s', err)
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


# must connect the test runner to the deployer network to be able to send http req to the test runner which runs in a initial segregated net
@app.route('/testrunnernetconnect/<id>', methods=['GET'])
def testrunner_docker_network_connect(id):
    docker_utils = DockerUtils()
    http = HttpResponse()
    container_id = f"{id}_testrunner_1"
    try:
        [out, err] = CmdUtils.run_cmd(["bash", "-c",
                                       r'''docker network ls | grep deployer | awk '{print $2}' | head -1'''])
        app.logger.debug("Out: " + out)
        app.logger.debug("Err: " + err)
        if not out:
            return Response(json.dumps(http.failure(Constants.GET_DEPLOYER_NETWORK_FAILED,
                                                    ErrorCodes.HTTP_CODE.get(Constants.GET_DEPLOYER_NETWORK_FAILED),
                                                    err,
                                                    err)), 404, mimetype="application/json")
        deployer_network = out.strip()
        [out, err] = docker_utils.docker_network_connect(deployer_network, container_id)

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


@app.route('/testrunnernetdisconnect/<id>', methods=['GET'])
def testrunner_docker_network_disconnect(id):
    docker_utils = DockerUtils()
    http = HttpResponse()
    container_id = f"{id}_estuary-testrunner_1"
    try:
        [out, err] = CmdUtils.run_cmd(["bash", "-c",
                                       r'''docker network ls | grep deployer | awk '{print $2}' | head -1'''])
        app.logger.debug("Out: " + out)
        app.logger.debug("Err: " + err)
        if not out:
            return Response(json.dumps(http.failure(Constants.GET_DEPLOYER_NETWORK_FAILED,
                                                    ErrorCodes.HTTP_CODE.get(Constants.GET_DEPLOYER_NETWORK_FAILED),
                                                    err,
                                                    err)), 404, mimetype="application/json")
        deployer_network = out.strip()
        [out, err] = docker_utils.docker_network_disconnect(deployer_network, container_id)

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
@app.route('/testrunner/<id>/<path:text>', methods=['GET', 'POST'])
def testrunner_request(id, text):
    http = HttpResponse()
    elements = text.strip().split("/")
    container_id = f"{id}_testrunner_1"
    input_data = ""
    headers = {'Content-type': 'application/json'}
    try:
        input_data = request.data.decode('utf-8').strip()
    except:
        pass

    try:
        app.logger.debug(f'http://{container_id}:8080/{"/".join(elements)}, Method={request.method}')
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

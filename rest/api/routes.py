import os
import sys
import time
import traceback
from logging.handlers import logging

import flask
from flask import request
from flask_cors import CORS

from about import properties
from entities.render import Render
from rest.api import create_app
from rest.api.definitions import env_vars, swaggerui_blueprint, SWAGGER_URL
from rest.utils.constants import Constants
from rest.utils.error_codes import ErrorCodes
from rest.utils.http_response import HttpResponse
from rest.utils.utils import Utils

app = create_app()
CORS(app)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

app.logger.setLevel(logging.DEBUG)


@app.route('/swagger/swagger.yml')
def get_swagger():
    return app.send_static_file("swagger.yml")


@app.route('/env')
def get_vars():
    http = HttpResponse()
    return http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), env_vars), 200


@app.route('/ping')
def ping():
    http = HttpResponse()
    return http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), "pong"), 200


@app.route('/about')
def about():
    http = HttpResponse()
    return http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), properties["name"]), 200


@app.route('/rend/<template>/<variables>', methods=['GET'])
def get_content(template, variables):
    os.environ['TEMPLATE'] = template.strip()
    os.environ['VARIABLES'] = variables.strip()
    http = HttpResponse()
    try:
        r = Render(os.environ['TEMPLATE'], os.environ['VARIABLES'])
        response = r.rend_template("dummy"), 200
        # response = http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result), 200
    except Exception as e:
        result = "Exception({0})".format(e.__str__())
        response = http.failure(Constants.JINJA2_RENDER_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.JINJA2_RENDER_FAILURE), result,
                                str(traceback.format_exc())), 404

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
        r = Render(os.environ['TEMPLATE'], os.environ['VARIABLES'])
        response = r.rend_template("dummy"), 200
        # response = http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result), 200
    except Exception as e:
        result = "Exception({0})".format(e.__str__())
        response = http.failure(Constants.JINJA2_RENDER_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.JINJA2_RENDER_FAILURE), result,
                                str(traceback.format_exc())), 404

    return response


@app.route('/deploystart', methods=['POST'])
def deploy_start_file_from_client():
    utils = Utils()

    input_data = request.data.decode('utf-8')
    timestamp = int(time.time())
    dir = f"{Constants.DOCKER_PATH}{timestamp}"
    file = f"{dir}/{timestamp}"
    http = HttpResponse()

    [out, err] = utils.docker_stats(r"""| awk -F ' ' '{sum+=$7} END {print sum}'""")
    app.logger.debug('Max memory out: %s', out)
    app.logger.debug('Max memory err: %s', err)
    if "Cannot connect to the Docker daemon".lower() in err.lower():
        return http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                            ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                            str(traceback.format_exc())), 404

    if int(float(out)) >= int(os.environ.get("MAX_DEPLOY_MEMORY")):
        return http.failure(Constants.MAX_DEPLOY_MEMORY_REACHED,
                            ErrorCodes.HTTP_CODE.get(Constants.MAX_DEPLOY_MEMORY_REACHED) % os.environ.get(
                                "MAX_DEPLOY_MEMORY"), "Used memory: " + out.strip() + " percent",
                            str(traceback.format_exc())), 404

    try:
        utils.create_dir(dir)
        utils.write_to_file(file, input_data)
        [out, err] = utils.docker_up(file)
        app.logger.debug('Output: %s', out)
        app.logger.debug('Error: %s', err)
        result = str(timestamp)
        if len(utils.docker_ps(result)[0].split("\n")[1:-1]) > 0:
            response = http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result), 200
        else:
            response = http.failure(Constants.DEPLOY_START_FAILURE,
                                    ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE), err,
                                    str(traceback.format_exc())), 404
    except FileNotFoundError as e:
        result = "Exception({0})".format(e.__str__())
        response = http.failure(Constants.DEPLOY_START_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE), result,
                                str(traceback.format_exc())), 404
    except:
        result = "Exception({0})".format(sys.exc_info()[0])
        [out, err] = utils.docker_down(file)
        app.logger.debug('Output: %s', out)
        app.logger.debug('Error: %s', err)
        response = http.failure(Constants.DEPLOY_START_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE), result,
                                str(traceback.format_exc())), 404

    return response


@app.route('/deploystartenv/<template>/<variables>', methods=['POST'])
def deploy_with_env_file_from_server(template, variables):
    utils = Utils()
    try:
        input_json = request.get_json(force=True)
        for key, value in input_json.items():
            if key not in env_vars:
                os.environ[str(key)] = str(value)
    except:
        pass

    os.environ['TEMPLATE'] = template.strip()
    os.environ['VARIABLES'] = variables.strip()
    timestamp = int(time.time())
    dir = f"{Constants.DOCKER_PATH}{timestamp}"
    file = f"{dir}/{timestamp}"
    http = HttpResponse()

    [out, err] = utils.docker_stats(r"""| awk -F ' ' '{sum+=$7} END {print sum}'""")
    app.logger.debug('Max memory out: %s', out)
    app.logger.debug('Max memory err: %s', err)
    if "Cannot connect to the Docker daemon".lower() in err.lower():
        return http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                            ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                            str(traceback.format_exc())), 404
    if int(float(out)) >= int(os.environ['MAX_DEPLOY_MEMORY']):
        return http.failure(Constants.MAX_DEPLOY_MEMORY_REACHED,
                            ErrorCodes.HTTP_CODE.get(Constants.MAX_DEPLOY_MEMORY_REACHED) % int(os.environ['MAX_DEPLOY_MEMORY']), "Used memory: " + out.strip() + " percent",
                            str(traceback.format_exc())), 404

    try:
        r = Render(os.environ['TEMPLATE'], os.environ['VARIABLES'])
        utils.create_dir(dir)
        utils.write_to_file(file, r.rend_template("dummy"))
        [out, err] = utils.docker_up(file)
        app.logger.debug('Output: %s', out)
        app.logger.debug('Error: %s', err)
        result = str(timestamp)
        if len(utils.docker_ps(result)[0].split("\n")[1:-1]) > 0:
            response = http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result), 200
        else:
            response = http.failure(Constants.DEPLOY_START_FAILURE,
                                    ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE), err,
                                    str(traceback.format_exc())), 404
    except FileNotFoundError as e:
        result = "Exception({0})".format(e.__str__())
        response = http.failure(Constants.DEPLOY_START_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE), result,
                                str(traceback.format_exc())), 404
    except:
        result = "Exception({0})".format(sys.exc_info()[0])
        response = http.failure(Constants.DEPLOY_START_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE), result,
                                str(traceback.format_exc())), 404

    return response


@app.route('/deploystart/<template>/<variables>', methods=['GET'])
def deploy_start_file_from_server(template, variables):
    utils = Utils()
    os.environ['TEMPLATE'] = template.strip()
    os.environ['VARIABLES'] = variables.strip()
    timestamp = int(time.time())
    dir = f"{Constants.DOCKER_PATH}{timestamp}"
    file = f"{dir}/{timestamp}"
    http = HttpResponse()

    [out, err] = utils.docker_stats(r"""| awk -F ' ' '{sum+=$7} END {print sum}'""")
    app.logger.debug('Max memory out: %s', out)
    app.logger.debug('Max memory err: %s', err)
    if "Cannot connect to the Docker daemon".lower() in err.lower():
        return http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                            ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                            str(traceback.format_exc())), 404
    if int(float(out)) >= int(os.environ.get("MAX_DEPLOY_MEMORY")):
        return http.failure(Constants.MAX_DEPLOY_MEMORY_REACHED,
                            ErrorCodes.HTTP_CODE.get(Constants.MAX_DEPLOY_MEMORY_REACHED) % os.environ.get(
                                "MAX_DEPLOY_MEMORY"), "Used memory: " + out.strip() + " percent",
                            str(traceback.format_exc())), 404

    try:
        r = Render(os.environ['TEMPLATE'], os.environ['VARIABLES'])
        utils.create_dir(dir)
        utils.write_to_file(file, r.rend_template("dummy"))
        [out, err] = utils.docker_up(file)
        app.logger.debug('Output: %s', out)
        app.logger.debug('Error: %s', err)
        result = str(timestamp)
        if len(utils.docker_ps(result)[0].split("\n")[1:-1]) > 0:
            response = http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result), 200
        else:
            response = http.failure(Constants.DEPLOY_START_FAILURE,
                                    ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE), err,
                                    str(traceback.format_exc())), 404
    except FileNotFoundError as e:
        result = "Exception({0})".format(e.__str__())
        response = http.failure(Constants.DEPLOY_START_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE), result,
                                str(traceback.format_exc())), 404
    except:
        result = "Exception({0})".format(sys.exc_info()[0])
        response = http.failure(Constants.DEPLOY_START_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE), result,
                                str(traceback.format_exc())), 404

    return response


@app.route('/deployreplay/<id>', methods=['GET'])
def replay_file_from_server(id):
    id = id.strip()
    utils = Utils()
    http = HttpResponse()
    dir = f"{Constants.DOCKER_PATH}{id}"
    file = f"{dir}/{id}"

    try:
        [out, err] = utils.docker_ps(id)
        if "Cannot connect to the Docker daemon".lower() in err.lower():
            return http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                                str(traceback.format_exc())), 404
        result = out.split("\n")[1:-1]
        if len(result) > 0:
            return http.failure(Constants.DEPLOY_REPLAY_FAILURE_STILL_ACTIVE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_REPLAY_FAILURE_STILL_ACTIVE) % f"{id}",
                                result,
                                out), 404
            app.logger.debug('Output: %s', out)
            app.logger.debug('Error: %s', err)
    except FileNotFoundError as e:
        result = "Exception({0})".format(e.__str__())
        return http.failure(Constants.DEPLOY_REPLAY_FAILURE,
                            ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_REPLAY_FAILURE), result,
                            str(traceback.format_exc())), 404
    except:
        result = "Exception({0})".format(sys.exc_info()[0])
        return http.failure(Constants.DEPLOY_REPLAY_FAILURE,
                            ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_REPLAY_FAILURE) % f"{id}", result,
                            str(traceback.format_exc())), 404

    try:
        [out, err] = utils.docker_up(file)
        app.logger.debug('Output: %s', out)
        app.logger.debug('Error: %s', err)
        response = http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), id), 200
    except:
        result = "Exception({0})".format(sys.exc_info()[0])
        response = http.failure(Constants.DEPLOY_REPLAY_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_REPLAY_FAILURE), result,
                                str(traceback.format_exc())), 404

    return response


@app.route('/deploystatus/<id>', methods=['GET'])
def deploy_status(id):
    id = id.strip()
    utils = Utils()
    file = f"{Constants.DOCKER_PATH}{id}/{id}"
    http = HttpResponse()
    try:
        [out, err] = utils.docker_ps(id)
        if "Cannot connect to the Docker daemon".lower() in err.lower():
            return http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                                str(traceback.format_exc())), 404
        result = out.split("\n")[1:-1]
        response = http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result), 200
        app.logger.debug('Output: %s', out)
        app.logger.debug('Error: %s', err)
    except FileNotFoundError as e:
        result = "Exception({0})".format(e.__str__())
        response = http.failure(Constants.DEPLOY_STATUS_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_STATUS_FAILURE), result,
                                str(traceback.format_exc())), 404
    except:
        result = "Exception({0})".format(sys.exc_info()[0])
        response = http.failure(Constants.DEPLOY_STATUS_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_STATUS_FAILURE), result,
                                str(traceback.format_exc())), 404

    return response


@app.route('/deploystop/<id>', methods=['GET'])
def deploy_stop(id):
    id = id.strip()
    utils = Utils()
    file = f"{Constants.DOCKER_PATH}{id}/{id}"
    http = HttpResponse()
    try:
        [out, err] = utils.docker_down(file)
        if "Cannot connect to the Docker daemon".lower() in err.lower():
            return http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                                ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                                str(traceback.format_exc())), 404
        app.logger.debug('Output: %s', out)
        app.logger.debug('Error: %s', err)
        [out, err] = utils.docker_ps(id)
        result = out.split("\n")[1:-1]
        response = http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result), 200
    except FileNotFoundError as e:
        result = "Exception({0})".format(e.__str__())
        response = http.failure(Constants.DEPLOY_STOP_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_STOP_FAILURE), result,
                                str(traceback.format_exc())), 404
    except:
        result = "Exception({0})".format(sys.exc_info()[0])
        response = http.failure(Constants.DEPLOY_STOP_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_STOP_FAILURE), result,
                                str(traceback.format_exc())), 404

    return response


@app.route('/getdeployerfile', methods=['POST'])
def get_deployer_file():
    utils = Utils()
    http = HttpResponse()
    try:
        input_json = request.get_json(force=True)
        file = input_json["file"]
    except Exception as e:
        exception = "Exception({0})".format(sys.exc_info()[0])
        return http.failure(Constants.MISSING_PARAMETER_POST,
                            ErrorCodes.HTTP_CODE.get(Constants.MISSING_PARAMETER_POST) % "file", exception,
                            str(traceback.format_exc())), 404

    try:
        result = utils.read_file(file), 200
    except:
        exception = "Exception({0})".format(sys.exc_info()[0])
        result = http.failure(Constants.GET_ESTUARY_DEPLOYER_FILE_FAILURE,
                              ErrorCodes.HTTP_CODE.get(Constants.GET_ESTUARY_DEPLOYER_FILE_FAILURE), exception,
                              str(traceback.format_exc())), 404

    return result


@app.route('/istestfinished/<id>/<framework_container_service_name>/<keyword>', methods=['GET'])
def is_test_finished_default_file(id, framework_container_service_name, keyword):
    id = id.strip()
    framework_container_service_name = framework_container_service_name.strip()
    keyword = keyword.strip()
    utils = Utils()
    http = HttpResponse()
    file = Constants.DOCKER_PATH + "is_test_finished"
    finished = False
    container_id = id.strip() + "_" + framework_container_service_name.strip() + "_1"

    [out, err] = utils.docker_exec(container_id, ["sh", "-c", f"cat {file}"])
    app.logger.debug('Output: %s', out)
    app.logger.debug('Error: %s', err)
    if "Cannot connect to the Docker daemon".lower() in err.lower():
        return http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                            ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                            str(traceback.format_exc())), 404
    if "No such container".lower() in err.lower():
        response = http.failure(Constants.GET_CONTAINER_FILE_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (file, container_id),
                                finished,
                                err), 404
    elif keyword.strip().lower() in out.lower():
        finished = True
        response = http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), finished), 200
    else:
        response = http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), finished), 200

    return response


@app.route('/istestfinished/<id>/<framework_container_service_name>/<keyword>', methods=['POST'])
def is_test_finished_specific_file(id, framework_container_service_name, keyword):
    id = id.strip()
    framework_container_service_name = framework_container_service_name.strip()
    keyword = keyword.strip()
    utils = Utils()
    http = HttpResponse()
    try:
        input_json = request.get_json(force=True)
        file = input_json["file"]
    except Exception as e:
        exception = "Exception({0})".format(sys.exc_info()[0])
        return http.failure(Constants.MISSING_PARAMETER_POST,
                            ErrorCodes.HTTP_CODE.get(Constants.MISSING_PARAMETER_POST) % "file", exception,
                            str(traceback.format_exc())), 404
    finished = False
    container_id = id.strip() + "_" + framework_container_service_name.strip() + "_1"
    app.logger.debug('cid: %s', container_id)
    [out, err] = utils.docker_exec(container_id, ["sh", "-c", f"cat {file}"])
    app.logger.debug('Output: %s', out)
    app.logger.debug('Error: %s', err)
    if "Cannot connect to the Docker daemon".lower() in err.lower():
        return http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                            ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                            str(traceback.format_exc())), 404
    if "No such container".lower() in err.lower():
        response = http.failure(Constants.GET_CONTAINER_FILE_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (file, container_id),
                                finished,
                                err), 404
    elif keyword.strip().lower() in out.lower():
        finished = True
        response = http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), finished), 200
    else:
        response = http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), finished), 200

    return response


@app.route('/getcontainerfile/<id>/<container_service_name>', methods=['POST'])
def get_results_file(id, container_service_name):
    id = id.strip()
    container_service_name = container_service_name.strip()
    utils = Utils()
    http = HttpResponse()
    try:
        input_json = request.get_json(force=True)
        file = input_json["file"]
    except Exception as e:
        exception = "Exception({0})".format(sys.exc_info()[0])
        return http.failure(Constants.MISSING_PARAMETER_POST,
                            ErrorCodes.HTTP_CODE.get(Constants.MISSING_PARAMETER_POST) % "file", exception,
                            str(traceback.format_exc())), 404
    container_id = id + "_" + container_service_name + "_1"
    app.logger.debug('cid: %s', container_id)
    [out, err] = utils.docker_exec(container_id, ["sh", "-c", f"cat {file}"])
    # [out, err] = utils.docker_cp(id, framework_container_service_name, file)
    app.logger.debug('Output: %s', out)
    app.logger.debug('Error: %s', err)
    if "Cannot connect to the Docker daemon".lower() in err.lower():
        return http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                            ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                            str(traceback.format_exc())), 404
    if "No such container".lower() in err.lower():
        response = http.failure(Constants.GET_CONTAINER_FILE_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (file, container_id),
                                ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (file, container_id),
                                err), 404
    elif "No such file".lower() in err.lower():
        response = http.failure(Constants.GET_CONTAINER_FILE_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (file, container_id),
                                ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (file, container_id),
                                err), 404
    elif "Is a directory".lower() in err.lower():
        response = http.failure(Constants.GET_CONTAINER_FILE_FAILURE_IS_DIR,
                                ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE_IS_DIR) % (
                                    file, container_id),
                                ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE_IS_DIR) % (
                                    file, container_id),
                                err), 404
    else:
        response = out, 200

    return response


@app.route('/getcontainerfolder/<id>/<container_service_name>', methods=['POST'])
def get_container_folder(id, container_service_name):
    id = id.strip()
    container_service_name = container_service_name.strip()
    utils = Utils()
    http = HttpResponse()
    try:
        input_json = request.get_json(force=True)
        folder = input_json["folder"]
    except Exception as e:
        exception = "Exception({0})".format(sys.exc_info()[0])
        return http.failure(Constants.MISSING_PARAMETER_POST,
                            ErrorCodes.HTTP_CODE.get(Constants.MISSING_PARAMETER_POST) % "folder", exception,
                            str(traceback.format_exc())), 404
    container_id = id + "_" + container_service_name + "_1"
    app.logger.debug('cid: %s', container_id)
    [out, err] = utils.docker_cp(id, container_service_name, folder)
    app.logger.debug('Output: %s', out)
    app.logger.debug('Error: %s', err)
    if "Cannot connect to the Docker daemon".lower() in err.lower():
        return http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                            ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                            str(traceback.format_exc())), 404
    if "No such container".lower() in err.lower():
        return http.failure(Constants.GET_CONTAINER_FILE_FAILURE,
                            ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (folder, container_id),
                            ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (folder, container_id),
                            err), 404
    elif "No such file".lower() in err.lower():
        return http.failure(Constants.GET_CONTAINER_FILE_FAILURE,
                            ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (folder, container_id),
                            ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (folder, container_id),
                            err), 404
    else:
        app.logger.debug('Out: %s', out)

    try:
        path = f"/tmp/{id}/" + folder.split("/")[-1]
        utils.zip_file(id, path)
    except FileNotFoundError as e:
        result = "Exception({0})".format(e.__str__())
        return http.failure(Constants.GET_ESTUARY_DEPLOYER_FILE_FAILURE,
                            ErrorCodes.HTTP_CODE.get(Constants.GET_ESTUARY_DEPLOYER_FILE_FAILURE), result,
                            str(traceback.format_exc())), 404
    except:
        result = "Exception({0})".format(sys.exc_info()[0])
        return http.failure(Constants.FOLDER_ZIP_FAILURE,
                            ErrorCodes.HTTP_CODE.get(Constants.FOLDER_ZIP_FAILURE), result,
                            str(traceback.format_exc())), 404
    return flask.send_file(
        f"/tmp/{id}.zip",
        mimetype='application/zip',
        as_attachment=True), 200


@app.route('/teststart/<id>/<framework_container_service_name>', methods=['POST'])
def test_start(id, framework_container_service_name):
    id = id.strip()
    framework_container_service_name = framework_container_service_name.strip()
    utils = Utils()
    http = HttpResponse()
    input_data = request.data.decode('utf-8')
    file = Constants.DOCKER_PATH + "start.sh"
    container_id = id.strip() + "_" + framework_container_service_name.strip() + "_1"
    started = False

    [out, err] = utils.docker_exec(container_id, ["sh", "-c", f"echo  '{input_data}' > {file}"])
    app.logger.debug('Output: %s', out)
    app.logger.debug('Error: %s', err)
    if "Cannot connect to the Docker daemon".lower() in err.lower():
        return http.failure(Constants.DOCKER_DAEMON_NOT_RUNNING,
                            ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING), err,
                            str(traceback.format_exc())), 404
    if err:
        return http.failure(Constants.TEST_START_FAILURE,
                            ErrorCodes.HTTP_CODE.get(Constants.TEST_START_FAILURE) % (file, container_id), started,
                            err), 404

    [out, err] = utils.docker_exec(container_id, ["sh", "-c", f"chmod +x {file}"])
    app.logger.debug('Output: %s', out)
    app.logger.debug('Error: %s', err)
    if err:
        return http.failure(Constants.TEST_START_FAILURE,
                            ErrorCodes.HTTP_CODE.get(Constants.TEST_START_FAILURE) % (file, container_id), started,
                            err), 404

    [out, err] = utils.docker_exec_detached(container_id, ["sh", "-c", f"{file}"])
    app.logger.debug('Output: %s', out)
    app.logger.debug('Error: %s', err)
    if err:
        return http.failure(Constants.TEST_START_FAILURE,
                            ErrorCodes.HTTP_CODE.get(Constants.TEST_START_FAILURE) % (file, container_id), started,
                            err), 404

    return http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), True), 200


@app.route('/deploylogs/<id>', methods=['GET'])
def deploy_logs(id):
    id = id.strip()
    dir = f"{Constants.DOCKER_PATH}{id}"
    file = f"{dir}/{id}"
    utils = Utils()
    http = HttpResponse()

    try:
        [out, err] = utils.docker_logs(file)
        app.logger.debug('Output: %s', out)
        app.logger.debug('Error: %s', err)
        if err:
            return http.failure(Constants.GET_LOGS_FAILED,
                                ErrorCodes.HTTP_CODE.get(Constants.GET_LOGS_FAILED) % (id), err,
                                err), 404
    except:
        exception = "Exception({0})".format(sys.exc_info()[0])
        return http.failure(Constants.GET_LOGS_FAILED,
                            ErrorCodes.HTTP_CODE.get(Constants.GET_LOGS_FAILED) % (id), exception,
                            exception), 404

    return http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), out.split("\n")), 200

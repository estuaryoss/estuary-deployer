import os
import sys
import time
import traceback

from flask import request

from about import properties
from entities.render import Render
from rest.api import create_app
from rest.api.definitions import env_vars, swaggerui_blueprint, SWAGGER_URL
from rest.utils.constants import Constants
from rest.utils.error_codes import ErrorCodes
from rest.utils.http_response import HttpResponse
from rest.utils.utils import Utils

app = create_app()
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)


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
    os.environ['TEMPLATE'] = template
    os.environ['VARIABLES'] = variables
    r = Render(os.environ['TEMPLATE'], os.environ['VARIABLES'])
    http = HttpResponse()
    try:
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
                os.environ[key] = value
    except:
        pass

    os.environ['TEMPLATE'] = template
    os.environ['VARIABLES'] = variables

    r = Render(os.environ['TEMPLATE'], os.environ['VARIABLES'])
    http = HttpResponse()
    try:
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
    try:
        utils.create_dir(dir)
        utils.write_to_file(file, input_data)
        [out, err] = utils.docker_up(file)
        app.logger.info('Output: %s', out)
        app.logger.info('Error: %s', err)
        result = str(timestamp)
        response = http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result), 200
    except FileNotFoundError as e:
        result = "Exception({0})".format(e.__str__())
        response = http.failure(Constants.DEPLOY_START_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE), result,
                                str(traceback.format_exc())), 404
    except:
        result = "Exception({0})".format(sys.exc_info()[0])
        [out, err] = utils.docker_down(file)
        app.logger.info('Output: %s', out)
        app.logger.info('Error: %s', err)
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
                os.environ[key] = value
    except:
        pass

    os.environ['TEMPLATE'] = template
    os.environ['VARIABLES'] = variables
    timestamp = int(time.time())
    dir = f"{Constants.DOCKER_PATH}{timestamp}"
    file = f"{dir}/{timestamp}"

    r = Render(os.environ['TEMPLATE'], os.environ['VARIABLES'])
    http = HttpResponse()
    try:
        utils.create_dir(dir)
        utils.write_to_file(file, r.rend_template("dummy"))
        [out, err] = utils.docker_up(file)
        app.logger.info('Output: %s', out)
        app.logger.info('Error: %s', err)
        result = str(timestamp)
        response = http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result), 200
    except FileNotFoundError as e:
        result = "Exception({0})".format(e.__str__())
        [out, err] = utils.docker_down(file)
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
    os.environ['TEMPLATE'] = template
    os.environ['VARIABLES'] = variables
    timestamp = int(time.time())
    dir = f"{Constants.DOCKER_PATH}{timestamp}"
    file = f"{dir}/{timestamp}"

    r = Render(os.environ['TEMPLATE'], os.environ['VARIABLES'])
    http = HttpResponse()
    try:
        utils.create_dir(dir)
        utils.write_to_file(file, r.rend_template("dummy"))
        [out, err] = utils.docker_up(file)
        app.logger.info('Output: %s', out)
        app.logger.info('Error: %s', err)
        result = str(timestamp)
        response = http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result), 200
    except FileNotFoundError as e:
        result = "Exception({0})".format(e.__str__())
        [out, err] = utils.docker_down(file)
        response = http.failure(Constants.DEPLOY_START_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE), result,
                                str(traceback.format_exc())), 404
    except:
        result = "Exception({0})".format(sys.exc_info()[0])
        response = http.failure(Constants.DEPLOY_START_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE), result,
                                str(traceback.format_exc())), 404

    return response


@app.route('/replay/<file>', methods=['GET'])
def replay_file_from_server(file):
    utils = Utils()
    dir = f"{Constants.DOCKER_PATH}{file}"
    file = f"{dir}/{file}"

    r = Render(os.environ['TEMPLATE'], os.environ['VARIABLES'])
    http = HttpResponse()
    try:
        [out, err] = utils.docker_up(file)
        app.logger.info('Output: %s', out)
        app.logger.info('Error: %s', err)
        response = http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), out), 200
    except FileNotFoundError as e:
        result = "Exception({0})".format(e.__str__())
        [out, err] = utils.docker_down(file)
        response = http.failure(Constants.DEPLOY_REPLAY_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_REPLAY_FAILURE), result,
                                str(traceback.format_exc())), 404
    except:
        result = "Exception({0})".format(sys.exc_info()[0])
        response = http.failure(Constants.DEPLOY_REPLAY_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_REPLAY_FAILURE), result,
                                str(traceback.format_exc())), 404

    return response


@app.route('/deploystatus/<file>', methods=['GET'])
def deploy_status(file):
    utils = Utils()
    file = f"{Constants.DOCKER_PATH}{file}/{file}"
    http = HttpResponse()
    try:
        [out, err] = utils.docker_ps(file)
        result = out
        response = http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result), 200
        app.logger.info('Output: %s', out)
        app.logger.info('Error: %s', err)
    except Exception as e:
        result = "Exception({0})".format(e.__str__())
        response = http.failure(Constants.DEPLOY_STATUS_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_STATUS_FAILURE), result,
                                str(traceback.format_exc())), 404
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


@app.route('/deploystop/<file>', methods=['GET'])
def deploy_stop(file):
    utils = Utils()
    file = f"{Constants.DOCKER_PATH}{file}/{file}"
    http = HttpResponse()
    try:
        [out, err] = utils.docker_down(file)
        app.logger.info('Output: %s', out)
        app.logger.info('Error: %s', err)
        result = out
        response = http.success(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), result), 200
    except Exception as e:
        result = "Exception({0})".format(e.__str__())
        response = http.failure(Constants.DEPLOY_STOP_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_STOP_FAILURE), result,
                                str(traceback.format_exc())), 404
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


@app.route('/getresultsfile', methods=['POST'])
def get_results():
    utils = Utils()
    http = HttpResponse()
    input_json = request.get_json(force=True)
    file = input_json["file"]

    try:
        result = utils.read_file(file), 200
    except:
        result = "Exception({0})".format(sys.exc_info()[0])
        result = http.failure(Constants.GET_RESULTS_FILE_FAILURE,
                                ErrorCodes.HTTP_CODE.get(Constants.GET_RESULTS_FILE_FAILURE), result,
                                str(traceback.format_exc())), 404

    return result

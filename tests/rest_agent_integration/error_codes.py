from tests.rest_agent_integration.constants import Constants


class ErrorCodes:
    HTTP_CODE = {
        Constants.SUCCESS: "Success",
        Constants.JINJA2_RENDER_FAILURE: "Jinja2 render failed",
        Constants.GET_FILE_FAILURE: "Getting file or folder from the estuary agent service container failed",
        Constants.TEST_START_FAILURE: "Starting test id %s failed",
        Constants.TEST_STOP_FAILURE: "Stopping running test %s failed",
        Constants.GET_FILE_FAILURE_IS_DIR: "Getting %s from the container %s failed. It is a directory, not a file.",
        Constants.GET_ENV_VAR_FAILURE: "Getting env var %s from the container failed.",
        Constants.MISSING_PARAMETER_POST: "Body parameter \"%s\" sent in request missing. "
                                          "Please include parameter. E.g. {\"parameter\": \"value\"}",
        Constants.GET_TEST_INFO_FAILURE: "Failed to get test info.",
        Constants.FOLDER_ZIP_FAILURE: "Failed to zip folder %s.",
        Constants.EMPTY_REQUEST_BODY_PROVIDED: "Empty request body provided.",
        Constants.UPLOAD_TEST_CONFIG_FAILURE: "Failed to upload test configuration.",
        Constants.HTTP_HEADER_NOT_PROVIDED: "Http header value not provided: '%s'",
        Constants.COMMAND_EXEC_FAILURE: "Starting command(s) failed",
        Constants.EXEC_COMMAND_NOT_ALLOWED: "'rm' commands are filtered. Command '%s' was not executed.",
        Constants.UNAUTHORIZED: "Unauthorized",
        Constants.SET_ENV_VAR_FAILURE: "Failed to set env vars \"%s\"",
        Constants.INVALID_JSON_PAYLOAD: "Invalid json body \"%s\"",
    }

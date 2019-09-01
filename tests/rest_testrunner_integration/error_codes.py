from tests.rest_testrunner_integration.constants import Constants


class ErrorCodes:
    HTTP_CODE = {
        Constants.SUCCESS: "success",
        Constants.JINJA2_RENDER_FAILURE: "jinja2 render failed",
        Constants.GET_ESTUARY_TESTRUNNER_FILE_FAILURE: "Getting file or folder from the estuary testrunner service container failed",
        Constants.TEST_START_FAILURE: "Starting test id %s failed",
        Constants.TEST_STOP_FAILURE: "Stopping running test %s failed",
        Constants.GET_CONTAINER_FILE_FAILURE: "Getting %s from the container %s failed",
        Constants.GET_CONTAINER_FILE_FAILURE_IS_DIR: "Getting file or folder %s failed. It is a directory, not a file.",
        Constants.GET_CONTAINER_ENV_VAR_FAILURE: "Getting env var %s from the container failed.",
        Constants.MISSING_PARAMETER_POST: "Body parameter \"%s\" sent in request missing. Please include parameter. E.g. {\"parameter\": \"value\"}",
        Constants.GET_CONTAINER_TEST_INFO_FAILURE: "Failed to get test info.",
        Constants.FOLDER_ZIP_FAILURE: "Failed to zip folder %s.",
        Constants.EMPTY_REQUEST_BODY_PROVIDED: "Empty request body provided.",
        Constants.UPLOAD_TEST_CONFIG_FAILURE: "Failed to upload test configuration."
    }

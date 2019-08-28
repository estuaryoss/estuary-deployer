from rest.utils.constants import Constants


class ErrorCodes:
    HTTP_CODE = {
        Constants.SUCCESS: "success",
        Constants.JINJA2_RENDER_FAILURE: "jinja2 render failed",
        Constants.DEPLOY_START_FAILURE: "deploy start action failed",
        Constants.DEPLOY_STOP_FAILURE: "deploy stop action failed",
        Constants.DEPLOY_STATUS_FAILURE: "deploy status action failed",
        Constants.DEPLOY_REPLAY_FAILURE: "deploy replay action failed",
        Constants.GET_ESTUARY_DEPLOYER_FILE_FAILURE: "Getting file from the estuary deployer service container failed",
        Constants.TEST_START_FAILURE: "Starting %s from the container %s failed",
        Constants.GET_CONTAINER_FILE_FAILURE: "Getting %s from the container %s failed",
        Constants.GET_CONTAINER_FILE_FAILURE_IS_DIR: "Getting %s from the container %s failed. It is directory, not file.",
        Constants.DEPLOY_REPLAY_FAILURE_STILL_ACTIVE: "Starting environment id %s failed. Environment it is active.",
        Constants.MAX_DEPLOY_MEMORY_REACHED: "Maximum memory %s percent allowed on the host reached. Tune this env var if needed: MAX_DEPLOY_MEMORY",
        Constants.DOCKER_DAEMON_NOT_RUNNING: "Docker daemon is not running. You must start it.",
        Constants.MISSING_PARAMETER_POST: "Body parameter '%s' sent in request missing. Please include parameter. E.g. {\"parameter\": \"value\"}",
        Constants.GET_LOGS_FAILED: "Getting logs for %s failed.",
        Constants.MAX_DEPLOYMENTS_REACHED: "Maximum deployments %s reached. Please stop some deployments, before starting new ones."
    }

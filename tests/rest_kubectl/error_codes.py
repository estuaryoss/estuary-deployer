from tests.rest_kubectl.constants import Constants


class ErrorCodes:
    HTTP_CODE = {
        Constants.SUCCESS: "success",
        Constants.JINJA2_RENDER_FAILURE: "jinja2 render failed",
        Constants.DEPLOY_START_FAILURE: "deploy start action failed",
        Constants.DEPLOY_STOP_FAILURE: "deploy stop action failed",
        Constants.DEPLOY_STATUS_FAILURE: "deploy status action failed",
        Constants.DEPLOY_REPLAY_FAILURE: "deploy replay action failed",
        Constants.GET_FILE_FAILURE: "Getting file from the estuary deployer service container failed",
        Constants.COMMAND_EXEC_FAILURE: "Starting command '%s' failed",
        Constants.GET_CONTAINER_FILE_FAILURE: "Getting %s from the container %s failed",
        Constants.DEPLOY_REPLAY_FAILURE_STILL_ACTIVE: "Starting environment id %s failed. Environment it is active.",
        Constants.DOCKER_DAEMON_NOT_RUNNING: "Docker daemon is not running. You must start it.",
        Constants.MISSING_PARAMETER_POST: "Body parameter '%s' sent in request missing. Please include parameter. E.g. {\"parameter\": \"value\"}",
        Constants.GET_LOGS_FAILED: "Getting logs for %s failed.",
        Constants.MAX_DEPLOYMENTS_REACHED: "Maximum deployments %s reached. Please stop some deployments, before starting new ones.",
        Constants.CONTAINER_UNREACHABLE: "Could not reach %s container. Did you started it? Is the service name in docker-compose.yml defined as '%s'?",
        Constants.GET_DEPLOYER_NETWORK_FAILED: "Failed to get the docker network associated with the estuary-deployer service.",
        Constants.CONTAINER_DEPLOYER_NET_CONNECT_FAILED: "Failed to connect the container to the docker net associated with the deployer service.",
        Constants.CONTAINER_DEPLOYER_NET_DISCONNECT_FAILED: "Failed to disconnect the container to the docker net associated with the deployer service.",
        Constants.GET_CONTAINER_ENV_VAR_FAILURE: "Getting env var %s from the container failed.",
        Constants.EMPTY_REQUEST_BODY_PROVIDED: "Empty request body provided.",
        Constants.UPLOAD_FILE_FAILURE: "Failed to upload file content.",
        Constants.HTTP_HEADER_NOT_PROVIDED: "Http header value not provided: '%s'",
        Constants.EXEC_COMMAND_NOT_ALLOWED: "'rm' commands are filtered. Command '%s' was not executed.",
        Constants.KUBERNETES_SERVER_ERROR: "Error response from server: '%s'"
    }

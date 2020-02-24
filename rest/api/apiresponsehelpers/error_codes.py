from rest.api.constants.api_constants import ApiConstants


class ErrorCodes:
    HTTP_CODE = {
        ApiConstants.SUCCESS: "success",
        ApiConstants.JINJA2_RENDER_FAILURE: "jinja2 render failed",
        ApiConstants.DEPLOY_START_FAILURE: "deploy start action failed",
        ApiConstants.DEPLOY_STOP_FAILURE: "deploy stop action failed",
        ApiConstants.DEPLOY_STATUS_FAILURE: "deploy status action failed",
        ApiConstants.DEPLOY_REPLAY_FAILURE: "deploy replay action failed",
        ApiConstants.GET_FILE_FAILURE: "Getting file from the estuary deployer service failed",
        ApiConstants.COMMAND_EXEC_FAILURE: "Starting command '%s' failed",
        ApiConstants.GET_CONTAINER_FILE_FAILURE: "Getting %s from the container %s failed",
        ApiConstants.DEPLOY_REPLAY_FAILURE_STILL_ACTIVE: "Starting environment id %s failed. Environment it is active.",
        ApiConstants.DOCKER_DAEMON_NOT_RUNNING: "Docker daemon is not running. You must start it.",
        ApiConstants.MISSING_PARAMETER_POST: "Body parameter '%s' sent in request missing. Please include parameter. E.g. {\"parameter\": \"value\"}",
        ApiConstants.GET_LOGS_FAILED: "Getting logs for %s failed.",
        ApiConstants.MAX_DEPLOYMENTS_REACHED: "Maximum deployments %s reached. Please stop some deployments, before starting new ones.",
        ApiConstants.CONTAINER_UNREACHABLE: "Could not reach %s container. Did you started it? Is the service name in docker-compose.yml defined as '%s'?",
        ApiConstants.GET_DEPLOYER_NETWORK_FAILED: "Failed to get the docker network associated with the estuary-deployer service.",
        ApiConstants.CONTAINER_DEPLOYER_NET_CONNECT_FAILED: "Failed to connect the container to the docker net associated with the deployer service.",
        ApiConstants.CONTAINER_DEPLOYER_NET_DISCONNECT_FAILED: "Failed to disconnect the container to the docker net associated with the deployer service.",
        ApiConstants.GET_CONTAINER_ENV_VAR_FAILURE: "Getting env var %s from the container failed.",
        ApiConstants.EMPTY_REQUEST_BODY_PROVIDED: "Empty request body provided.",
        ApiConstants.UPLOAD_FILE_FAILURE: "Failed to upload file content.",
        ApiConstants.HTTP_HEADER_NOT_PROVIDED: "Http header value not provided: '%s'",
        ApiConstants.EXEC_COMMAND_NOT_ALLOWED: "'rm' commands are filtered. Command '%s' was not executed.",
        ApiConstants.KUBERNETES_SERVER_ERROR: "Error response from server: '%s'",
        ApiConstants.UNAUTHORIZED: "Unauthorized"
    }

from rest.api.constants.api_code import ApiCode


class ErrorMessage:
    HTTP_CODE = {
        ApiCode.SUCCESS.value: "Success",
        ApiCode.JINJA2_RENDER_FAILURE.value: "Jinja2 render failed",
        ApiCode.DEPLOY_START_FAILURE.value: "Deploy start action failed",
        ApiCode.DEPLOY_STOP_FAILURE.value: "Deploy stop action failed",
        ApiCode.DEPLOY_STATUS_FAILURE.value: "Deploy status action failed",
        ApiCode.DEPLOY_REPLAY_FAILURE.value: "Deploy replay action failed",
        ApiCode.GET_FILE_FAILURE.value: "Getting file from the estuary deployer service failed",
        ApiCode.COMMAND_EXEC_FAILURE.value: "Starting commands failed",
        ApiCode.GET_CONTAINER_FILE_FAILURE.value: "Getting %s from the container %s failed",
        ApiCode.DEPLOY_REPLAY_FAILURE_STILL_ACTIVE.value: "Starting the environment with id %s failed. "
                                                          "The Environment it is already active.",
        ApiCode.DOCKER_DAEMON_NOT_RUNNING.value: "Docker daemon is not running. You must start it.",
        ApiCode.MISSING_PARAMETER_POST.value: "Body parameter '%s' sent in the request missing. "
                                              "Please include the parameter. E.g. {\"parameter\".value: \"value\"}",
        ApiCode.GET_LOGS_FAILED.value: "Getting logs for %s failed.",
        ApiCode.MAX_DEPLOYMENTS_REACHED.value: "Maximum deployments %s reached. "
                                               "Please stop some deployments, before starting new ones.",
        ApiCode.CONTAINER_UNREACHABLE.value: "Could not reach %s container. "
                                             "Did you started it? Is the service name in docker-compose.yml defined as '%s'?",
        ApiCode.GET_DEPLOYER_NETWORK_FAILED.value: "Failed to get the docker network associated with the estuary-deployer service.",
        ApiCode.CONTAINER_NET_CONNECT_FAILED.value: "Failed to connect the container from the docker net associated with the deployer service.",
        ApiCode.CONTAINER_NET_DISCONNECT_FAILED.value: "Failed to disconnect the container from the docker net associated with the deployer service.",
        ApiCode.GET_ENV_VAR_FAILURE.value: "Getting the env var %s from the container failed.",
        ApiCode.EMPTY_REQUEST_BODY_PROVIDED.value: "Empty request body provided.",
        ApiCode.UPLOAD_FILE_FAILURE.value: "Failed to upload file content.",
        ApiCode.HTTP_HEADER_NOT_PROVIDED.value: "Http header value not provided.value: '%s'",
        ApiCode.KUBERNETES_SERVER_ERROR.value: "Error response from server.value: '%s'",
        ApiCode.UNAUTHORIZED.value: "Unauthorized",
        ApiCode.INVALID_JSON_PAYLOAD.value: "Invalid JSON payload '%s'",
        ApiCode.SET_ENV_VAR_FAILURE.value: "Could not set env vars '%s'",
        ApiCode.FOLDER_UNZIP_FAILURE.value: "Could not unzip file '%'",
        ApiCode.GENERAL.value: "General error occurred."
    }

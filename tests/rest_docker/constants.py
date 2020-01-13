class Constants:
    DOCKER_PATH = "/tmp/"
    DOCKER_LOGS_LINES = 200

    SUCCESS = "1000"
    JINJA2_RENDER_FAILURE = "1001"
    DEPLOY_START_FAILURE = "1002"
    DEPLOY_STOP_FAILURE = "1003"
    DEPLOY_STATUS_FAILURE = "1004"
    DEPLOY_REPLAY_FAILURE = "1005"
    GET_FILE_FAILURE = "1006"
    GET_CONTAINER_FILE_FAILURE = "1007"
    COMMAND_EXEC_FAILURE = "1008"
    DEPLOY_REPLAY_FAILURE_STILL_ACTIVE = "1009"
    FOLDER_ZIP_FAILURE = "1010"
    DOCKER_DAEMON_NOT_RUNNING = "1011"
    MISSING_PARAMETER_POST = "1012"
    GET_LOGS_FAILED = "1013"
    MAX_DEPLOYMENTS_REACHED = "1014"
    CONTAINER_UNREACHABLE = "1015"
    GET_DEPLOYER_NETWORK_FAILED = "1016"
    CONTAINER_DEPLOYER_NET_CONNECT_FAILED = "1017"
    CONTAINER_DEPLOYER_NET_DISCONNECT_FAILED = "1018"
    GET_CONTAINER_ENV_VAR_FAILURE = "1019"
    EMPTY_REQUEST_BODY_PROVIDED = "1020"
    UPLOAD_FILE_FAILURE = "1021"
    HTTP_HEADER_NOT_PROVIDED = "1022"
    EXEC_COMMAND_NOT_ALLOWED = "1023"
    KUBERNETES_SERVER_ERROR = "1024"
    UNAUTHORIZED = "1025"

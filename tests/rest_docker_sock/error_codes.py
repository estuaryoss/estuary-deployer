from tests.rest_docker_sock.constants import Constants


class ErrorCodes:
    HTTP_CODE = {
        Constants.DOCKER_DAEMON_NOT_RUNNING: "Docker daemon is not running. You must start it."
    }

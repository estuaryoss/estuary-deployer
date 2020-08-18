import os

from rest.api.constants.env_constants import EnvConstants


class EnvStartup:
    __instance = None

    @staticmethod
    def get_instance():
        if EnvStartup.__instance is None:
            EnvStartup()
        return EnvStartup.__instance

    def __init__(self):
        EnvStartup.__instance = {
            EnvConstants.APP_APPEND_ID: os.environ.get(EnvConstants.APP_APPEND_ID).lower() if os.environ.get(
                EnvConstants.APP_APPEND_ID) else "",
            EnvConstants.ENV_EXPIRE_IN: int(os.environ.get(EnvConstants.ENV_EXPIRE_IN)) if os.environ.get(
                EnvConstants.ENV_EXPIRE_IN) else 1440,
            EnvConstants.APP_IP_PORT: os.environ.get(EnvConstants.APP_IP_PORT).strip().lower() if os.environ.get(
                EnvConstants.APP_IP_PORT) else None,
            EnvConstants.PORT: int(os.environ.get(EnvConstants.PORT).strip()) if os.environ.get(
                EnvConstants.PORT) is not None else 8080,
            EnvConstants.EUREKA_SERVER: os.environ.get(EnvConstants.EUREKA_SERVER).strip() if os.environ.get(
                EnvConstants.EUREKA_SERVER) else None,
            EnvConstants.FLUENTD_IP_PORT: os.environ.get(EnvConstants.FLUENTD_IP_PORT).strip() if os.environ.get(
                EnvConstants.FLUENTD_IP_PORT) else None,
            EnvConstants.HTTP_AUTH_TOKEN: os.environ.get(EnvConstants.HTTP_AUTH_TOKEN).strip() if os.environ.get(
                EnvConstants.HTTP_AUTH_TOKEN) else "None"
        }

from rest.api.constants.env_constants import EnvConstants
from rest.environment.environment import EnvironmentSingleton


class EnvStartupSingleton:
    __instance = None
    __env = EnvironmentSingleton.get_instance()

    @staticmethod
    def get_instance():
        if EnvStartupSingleton.__instance is None:
            EnvStartupSingleton()
        return EnvStartupSingleton.__instance

    def __init__(self):
        if EnvStartupSingleton.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            EnvStartupSingleton.__instance = self

    def get_config_env_vars(self):
        return {
            EnvConstants.APP_APPEND_LABEL: self.__env.get_env().get(
                EnvConstants.APP_APPEND_LABEL).lower() if self.__env.get_env().get(
                EnvConstants.APP_APPEND_LABEL) else "",
            EnvConstants.ENV_EXPIRE_IN: int(self.__env.get_env().get(
                EnvConstants.ENV_EXPIRE_IN)) if self.__env.get_env().get(
                EnvConstants.ENV_EXPIRE_IN) else 1440,
            EnvConstants.SCHEDULER_POLL_INTERVAL: int(self.__env.get_env().get(
                EnvConstants.SCHEDULER_POLL_INTERVAL)) if self.__env.get_env().get(
                EnvConstants.SCHEDULER_POLL_INTERVAL) else 1200,
            EnvConstants.APP_IP_PORT: self.__env.get_env().get(
                EnvConstants.APP_IP_PORT).strip().lower() if self.__env.get_env().get(
                EnvConstants.APP_IP_PORT) else None,
            EnvConstants.PORT: int(self.__env.get_env().get(
                EnvConstants.PORT).strip()) if self.__env.get_env().get(
                EnvConstants.PORT) is not None else 8080,
            EnvConstants.EUREKA_SERVER: self.__env.get_env().get(
                EnvConstants.EUREKA_SERVER).strip() if self.__env.get_env().get(
                EnvConstants.EUREKA_SERVER) else None,
            EnvConstants.FLUENTD_IP_PORT: self.__env.get_env().get(
                EnvConstants.FLUENTD_IP_PORT).strip() if self.__env.get_env().get(
                EnvConstants.FLUENTD_IP_PORT) else None,
            EnvConstants.HTTP_AUTH_TOKEN: self.__env.get_env().get(
                EnvConstants.HTTP_AUTH_TOKEN).strip() if self.__env.get_env().get(
                EnvConstants.HTTP_AUTH_TOKEN) else "None",
            EnvConstants.HTTPS_ENABLE: bool(self.__env.get_env().get(
                EnvConstants.HTTPS_ENABLE).strip()) if self.__env.get_env().get(
                EnvConstants.HTTPS_ENABLE) else False,
            EnvConstants.HTTPS_CERT: self.__env.get_env().get(
                EnvConstants.HTTPS_CERT).strip() if self.__env.get_env().get(
                EnvConstants.HTTPS_CERT) else "https/cert.pem",
            EnvConstants.HTTPS_KEY: self.__env.get_env().get(
                EnvConstants.HTTPS_KEY).strip() if self.__env.get_env().get(
                EnvConstants.HTTPS_KEY) else "https/key.pem"
        }

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
            EnvConstants.APP_IP_PORT: self.__env.get_env_and_virtual_env().get(
                EnvConstants.APP_IP_PORT).strip().lower() if self.__env.get_env_and_virtual_env().get(
                EnvConstants.APP_IP_PORT) else None,
            EnvConstants.PORT: int(self.__env.get_env_and_virtual_env().get(
                EnvConstants.PORT).strip()) if self.__env.get_env_and_virtual_env().get(
                EnvConstants.PORT) is not None else 8080,
            EnvConstants.EUREKA_SERVER: self.__env.get_env_and_virtual_env().get(
                EnvConstants.EUREKA_SERVER).strip() if self.__env.get_env_and_virtual_env().get(
                EnvConstants.EUREKA_SERVER) else None,
            EnvConstants.FLUENTD_IP_PORT: self.__env.get_env_and_virtual_env().get(
                EnvConstants.FLUENTD_IP_PORT).strip() if self.__env.get_env_and_virtual_env().get(
                EnvConstants.FLUENTD_IP_PORT) else None,
            EnvConstants.HTTP_AUTH_TOKEN: self.__env.get_env_and_virtual_env().get(
                EnvConstants.HTTP_AUTH_TOKEN).strip() if self.__env.get_env_and_virtual_env().get(
                EnvConstants.HTTP_AUTH_TOKEN) else "None"
        }

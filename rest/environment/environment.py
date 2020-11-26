import os

from jproperties import Properties

from rest.api.views import AppCreatorSingleton


class EnvironmentSingleton:
    VIRTUAL_ENV_MAX_SIZE = 100

    __file = "environment.properties"
    __instance = None
    __env = os.environ.copy()
    __virtual_env = {}
    __app = AppCreatorSingleton.get_instance().get_app()

    @staticmethod
    def get_instance():
        if EnvironmentSingleton.__instance is None:
            EnvironmentSingleton()
        return EnvironmentSingleton.__instance

    def __init__(self):
        """
        The constructor. This class keeps system env vars plus the virtual env vars set by the user.
        These env vars are then passed to the subprocess call.
        """
        self.__set_env_vars_from_properties()

        if EnvironmentSingleton.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            EnvironmentSingleton.__instance = self

    def __set_env_vars_from_properties(self):
        configs = Properties()
        try:
            with open(self.__file, 'rb') as config_file:
                configs.load(config_file)
        except Exception as e:
            self.__app.logger.debug({
                "msg": f"Skipping env vars loading from file '{self.__file}' because it doesn't exist. " +
                       "Exception({})".format(e.__str__())})

        for key in configs:
            self.set_env_var(key, configs[key][0])

    def set_env_var(self, key, value):
        if key in self.get_env():
            return False
        if key in self.get_virtual_env():
            self.__virtual_env[key] = value
            return True
        if len(self.get_virtual_env()) <= self.VIRTUAL_ENV_MAX_SIZE:
            self.__virtual_env[key] = value
            return True

        return False

    def set_env_var(self, env_vars):
        env_vars_set = {}
        for key, value in env_vars.items():
            if self.set_env_var(key, value):
                env_vars_set[key] = value

        return env_vars_set

    def get_env(self):
        return self.__env

    def get_virtual_env(self):
        return self.__virtual_env

    def get_env_and_virtual_env(self):
        return {**self.__env, **self.__virtual_env}

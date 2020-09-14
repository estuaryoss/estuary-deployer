from rest.api.constants.env_constants import EnvConstants
from rest.api.views import AppCreatorSingleton
from rest.environment.environment import EnvironmentSingleton


class EnvInit:
    # env constants
    WORKSPACE = "tmp"
    app = AppCreatorSingleton.get_instance().get_app()

    if EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.WORKSPACE):
        WORKSPACE = EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.WORKSPACE)
    # take paths from env if they exists
    TEMPLATES_PATH = EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
        EnvConstants.TEMPLATES_DIR) if EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
        EnvConstants.TEMPLATES_DIR) else WORKSPACE + "/templates"
    VARIABLES_PATH = EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
        EnvConstants.VARS_DIR) if EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
        EnvConstants.VARS_DIR) else WORKSPACE + "/variables"
    DEPLOY_PATH = WORKSPACE + "/deployments"

    if not EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.VARS_DIR):
        EnvironmentSingleton.get_instance().get_env_and_virtual_env()[EnvConstants.VARS_DIR] = VARIABLES_PATH
        app.logger.debug(f"{EnvConstants.VARS_DIR} env var not set, defaulting to : " + str(
            EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
                EnvConstants.VARS_DIR)))

    if not EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.TEMPLATES_DIR):
        EnvironmentSingleton.get_instance().get_env_and_virtual_env()[EnvConstants.TEMPLATES_DIR] = TEMPLATES_PATH
        app.logger.debug(f"{EnvConstants.TEMPLATES_DIR} env var not set, defaulting to : " + str(
            EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
                EnvConstants.TEMPLATES_DIR)))

    app.logger.debug("WORKSPACE : " + WORKSPACE)
    app.logger.debug("DEPLOY_PATH : " + DEPLOY_PATH)
    app.logger.debug("TEMPLATES_PATH : " + TEMPLATES_PATH)
    app.logger.debug("VARIABLES_PATH : " + VARIABLES_PATH)

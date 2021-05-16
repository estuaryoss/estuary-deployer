from rest.api.constants.env_constants import EnvConstants
from rest.api.views import AppCreatorSingleton
from rest.environment.environment import EnvironmentSingleton


class EnvInit:
    # env constants
    init = {}
    WORKSPACE = "tmp"
    init[EnvConstants.WORKSPACE] = WORKSPACE
    app = AppCreatorSingleton.get_instance().get_app()

    if EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.WORKSPACE):
        init[EnvConstants.WORKSPACE] = EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
            EnvConstants.WORKSPACE)
    # take paths from env if they exists
    init[EnvConstants.TEMPLATES_DIR] = EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
        EnvConstants.TEMPLATES_DIR) if EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
        EnvConstants.TEMPLATES_DIR) else init.get(EnvConstants.WORKSPACE) + "/templates"
    init[EnvConstants.DEPLOY_WITH] = EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
        EnvConstants.DEPLOY_WITH) if EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
        EnvConstants.DEPLOY_WITH) else "docker"
    init[EnvConstants.VARS_DIR] = EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
        EnvConstants.VARS_DIR) if EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
        EnvConstants.VARS_DIR) else init.get(EnvConstants.WORKSPACE) + "/variables"
    init[EnvConstants.MAX_DEPLOYMENTS] = int(EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
        EnvConstants.MAX_DEPLOYMENTS)) if EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
        EnvConstants.MAX_DEPLOYMENTS) else 10
    init[EnvConstants.DEPLOY_PATH] = init.get(EnvConstants.WORKSPACE) + "/deployments"

    if not EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.VARS_DIR):
        EnvironmentSingleton.get_instance().get_env_and_virtual_env()[EnvConstants.VARS_DIR] = init.get(
            EnvConstants.VARS_DIR)
        app.logger.debug(f"{EnvConstants.VARS_DIR} env var not set, defaulting to : " + str(
            EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
                EnvConstants.VARS_DIR)))

    if not EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.TEMPLATES_DIR):
        EnvironmentSingleton.get_instance().get_env_and_virtual_env()[EnvConstants.TEMPLATES_DIR] = init.get(
            EnvConstants.TEMPLATES_DIR)
        app.logger.debug(f"{EnvConstants.TEMPLATES_DIR} env var not set, defaulting to : " + str(
            EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
                EnvConstants.TEMPLATES_DIR)))

    app.logger.debug("WORKSPACE : " + init.get(EnvConstants.WORKSPACE))
    app.logger.debug("DEPLOY_PATH : " + init.get(EnvConstants.DEPLOY_PATH))
    app.logger.debug("DEPLOY_WITH : " + init.get(EnvConstants.DEPLOY_WITH))
    app.logger.debug("MAX_DEPLOYMENTS : " + str(init.get(EnvConstants.MAX_DEPLOYMENTS)))
    app.logger.debug("TEMPLATES_PATH : " + init.get(EnvConstants.TEMPLATES_DIR))
    app.logger.debug("VARIABLES_PATH : " + init.get(EnvConstants.VARS_DIR))

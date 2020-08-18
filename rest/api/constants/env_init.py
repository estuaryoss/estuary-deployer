import os

from rest.api.constants.env_constants import EnvConstants


class EnvInit:
    # env constants
    WORKSPACE = "tmp"
    if os.environ.get(EnvConstants.WORKSPACE):
        WORKSPACE = os.environ.get(EnvConstants.WORKSPACE)
    # take paths from env if they exists
    TEMPLATES_PATH = os.environ.get(EnvConstants.TEMPLATES_DIR) if os.environ.get(
        EnvConstants.TEMPLATES_DIR) else WORKSPACE + "/templates"
    VARIABLES_PATH = os.environ.get(EnvConstants.VARS_DIR) if os.environ.get(
        EnvConstants.VARS_DIR) else WORKSPACE + "/variables"
    DEPLOY_PATH = WORKSPACE + "/deployments"

    if not os.environ.get(EnvConstants.VARS_DIR):
        os.environ[EnvConstants.VARS_DIR] = VARIABLES_PATH
        print(f"{EnvConstants.VARS_DIR} env var not set, defaulting to : " + os.environ.get(EnvConstants.VARS_DIR))

    if not os.environ.get(EnvConstants.TEMPLATES_DIR):
        os.environ[EnvConstants.TEMPLATES_DIR] = TEMPLATES_PATH
        print(f"{EnvConstants.TEMPLATES_DIR} env var not set, defaulting to : " + os.environ.get(
            EnvConstants.TEMPLATES_DIR))

    print("WORKSPACE : " + WORKSPACE)
    print("DEPLOY_PATH : " + DEPLOY_PATH)
    print("TEMPLATES_PATH : " + TEMPLATES_PATH)
    print("VARIABLES_PATH : " + VARIABLES_PATH)

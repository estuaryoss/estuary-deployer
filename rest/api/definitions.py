import os

from rest.api.constants.env_constants import EnvConstants

unmodifiable_env_vars = {
    EnvConstants.TEMPLATES_DIR: os.environ.get(EnvConstants.TEMPLATES_DIR),
    EnvConstants.VARS_DIR: os.environ.get(EnvConstants.VARS_DIR),
    EnvConstants.PORT: os.environ.get(EnvConstants.PORT)
}

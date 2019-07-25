import os

from flask_swagger_ui import get_swaggerui_blueprint

env_vars = {
    "TEMPLATES_DIR": os.environ.get('TEMPLATES_DIR'),
    "VARS_DIR": os.environ.get('VARS_DIR'),
    "TEMPLATE": os.environ.get('TEMPLATE'),
    "VARIABLES": os.environ.get('VARIABLES'),
    "TEMPLATES_DIR_FILES": os.listdir(os.environ.get('TEMPLATES_DIR')),
    "VARS_DIR_FILES": os.listdir(os.environ.get('VARS_DIR')),
    "PATH": os.environ.get('PATH')
}

SWAGGER_URL = '/api/docs'
API_URL = '/swagger/swagger.yml'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Jinja2Docker"
    },
)

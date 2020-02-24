import os


class EnvConstants:
    # env constants
    WORKSPACE = "tmp"
    if os.environ.get('WORKSPACE'):
        WORKSPACE = os.environ.get('WORKSPACE')
    # take paths from env if they exists
    TEMPLATES_PATH = os.environ.get('TEMPLATES_DIR') if os.environ.get('TEMPLATES_DIR') else WORKSPACE + "/templates"
    VARIABLES_PATH = os.environ.get('VARS_DIR') if os.environ.get('VARS_DIR') else WORKSPACE + "/variables"
    DEPLOY_PATH = WORKSPACE + "/deployments"

    if not os.environ.get('VARS_DIR'):
        os.environ['VARS_DIR'] = VARIABLES_PATH
        print("VARS_DIR env var not set, defaulting to : " + os.environ.get('VARS_DIR'))

    if not os.environ.get('TEMPLATES_DIR'):
        os.environ['TEMPLATES_DIR'] = TEMPLATES_PATH
        print("TEMPLATES_DIR env var not set, defaulting to : " + os.environ.get('TEMPLATES_DIR'))

    print("WORKSPACE : " + WORKSPACE)
    print("DEPLOY_PATH : " + DEPLOY_PATH)
    print("TEMPLATES_PATH : " + TEMPLATES_PATH)
    print("VARIABLES_PATH : " + VARIABLES_PATH)

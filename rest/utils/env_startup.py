import os


class EnvStartup:
    __instance = None

    @staticmethod
    def get_instance():
        if EnvStartup.__instance is None:
            EnvStartup()
        return EnvStartup.__instance

    def __init__(self):
        EnvStartup.__instance = {
            "deploy_on": os.environ.get('DEPLOY_ON').lower() if os.environ.get('DEPLOY_ON') else "docker",
            "app_append_id": os.environ.get('APP_APPEND_ID').lower() if os.environ.get('APP_APPEND_ID') else "",
            "env_expire_in": int(os.environ.get('ENV_EXPIRE_IN')) if os.environ.get('ENV_EXPIRE_IN') else 1440,
            "app_ip_port": os.environ.get('APP_IP_PORT').strip().lower() if os.environ.get('APP_IP_PORT') else None,
            "port": int(os.environ.get('PORT').strip()) if os.environ.get('PORT') is not None else 8080,
            "eureka_server": os.environ.get('EUREKA_SERVER').strip() if os.environ.get('EUREKA_SERVER') else None,
            "fluentd_ip_port": int(os.environ.get('FLUENTD_IP_PORT').strip()) if os.environ.get(
                'FLUENTD_IP_PORT') else None,
            "http_auth_token": os.environ.get('HTTP_AUTH_TOKEN').strip() if os.environ.get(
                'HTTP_AUTH_TOKEN') else "None"
        }

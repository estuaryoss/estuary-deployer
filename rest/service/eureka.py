import py_eureka_client.eureka_client as eureka_client

from about import properties
from rest.api.constants.env_constants import EnvConstants
from rest.api.constants.env_init import EnvInit
from rest.utils.env_startup import EnvStartupSingleton


class Eureka:

    def __init__(self, host):
        self.host = host

    def register_app(self, app_ip_port, app_append_label):
        app_ip = app_ip_port.split(":")[0]
        app_port = int(app_ip_port.split(":")[1])
        print("Starting eureka register on eureka server " + self.host + ".\n")
        print(properties['name'] + " registering with: ip=" + app_ip + ",  port=" + str(app_port) + "... \n")

        protocol = "https" if EnvStartupSingleton.get_instance().get_config_env_vars().get(EnvConstants.HTTPS_ENABLE) \
            else "http"

        eureka_client.init(eureka_server=f"{self.host}",
                           app_name=f"{properties['name']}{app_append_label}",
                           instance_port=app_port,
                           instance_secure_port=app_port,
                           instance_ip=app_ip,
                           home_page_url=f"{protocol}://{app_ip}:{app_port}/{EnvInit.DEPLOY_WITH}/",
                           health_check_url=f"{protocol}://{app_ip}:{app_port}/{EnvInit.DEPLOY_WITH}/ping",
                           status_page_url=f"{protocol}://{app_ip}:{app_port}/{EnvInit.DEPLOY_WITH}/about"
                           )

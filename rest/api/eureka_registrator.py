import py_eureka_client.eureka_client as eureka_client

from about import properties


class EurekaRegistrator:

    def __init__(self, host):
        self.host = host

    def register_app(self, app_ip_port):
        app_ip = app_ip_port.split(":")[0]
        app_port = int(app_ip_port.split(":")[1])
        print(f"Starting eureka register on eureka server {self.host}. \n")
        print(f"{properties['name']} registering with: ip={app_ip}, port={app_port}... \n")
        eureka_client.init(eureka_server=f"{self.host}",
                           app_name=f"{properties['name']}",
                           instance_port=app_port,
                           instance_ip=app_ip,
                           health_check_url="ping",
                           home_page_url="env",
                           status_page_url="ping"
                           )

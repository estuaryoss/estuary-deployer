import py_eureka_client.eureka_client as eureka_client


class EurekaClient:

    def __init__(self, host):
        self.host = host

    def get_apps(self):
        apps_list = []
        print(f"Getting apps from eureka server {self.host} ... \n")
        for app in eureka_client.get_applications(eureka_server=f"{self.host}").applications:
            for instance in app.up_instances:
                # print(instance.app)
                apps_list.append(instance.hostName)
        return apps_list


if __name__ == '__main__':
    # step 1 - get all services registered in eureka
    up_services = EurekaClient("http://10.133.14.238:8080/eureka/v2").get_apps()
    print(up_services)

    # step 2 - start deploying your test envs on them (until no more ram available to use). Use multi thread
    # TODO

    # step 3 - spread the tests across all env obtained at step 2. Use multi thread
    # TODO

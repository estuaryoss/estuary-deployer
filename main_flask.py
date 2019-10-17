#!/usr/bin/python3
import os

from about import properties
from rest.api.eureka_registrator import EurekaRegistrator
from rest.api.schedulers.clean_folder_scheduler import CleanFolderScheduler
from rest.api.schedulers.docker_scheduler import DockerScheduler
from rest.api.schedulers.env_expire_scheduler import EnvExpireScheduler
from rest.api.views.docker_view import DockerView
from rest.api.views.kubectl_view import KubectlView

if __name__ == "__main__":

    app_append_id = ""
    deploy_on = "docker"  # default runs on docker
    env_expire_in = 1440  # minutes

    if os.environ.get('APP_APPEND_ID'):
        app_append_id = os.environ.get('APP_APPEND_ID').lower()
    if os.environ.get('EUREKA_SERVER'):
        EurekaRegistrator(os.environ.get('EUREKA_SERVER')).register_app(os.environ.get("APP_IP_PORT"), app_append_id)
    if os.environ.get('DEPLOY_ON'):
        deploy_on = os.environ.get("DEPLOY_ON")
    if os.environ.get('ENV_EXPIRE_IN'):
        env_expire_in = int(os.environ.get("ENV_EXPIRE_IN"))

    DockerScheduler().start()
    CleanFolderScheduler().start()
    EnvExpireScheduler(env_expire_in=env_expire_in).start()

    if "docker" in deploy_on:
        app = DockerView().get_app()
        DockerView.register(app)
        app.run(host='0.0.0.0', port=properties["port"])
    elif "kubectl" in deploy_on:
        app = KubectlView().get_app()
        KubectlView.register(app)
        app.run(host='0.0.0.0', port=properties["port"])
    else:
        raise NotImplementedError("Deploy on '%s' option is not supported" % os.environ.get('DEPLOY_ON'))

#!/usr/bin/python3
import os

from about import properties
from rest.api.eureka_registrator import EurekaRegistrator
from rest.api.schedulers.docker_clean_folder_scheduler import DockerCleanFolderScheduler
from rest.api.schedulers.docker_env_expire_scheduler import DockerEnvExpireScheduler
from rest.api.schedulers.docker_scheduler import DockerScheduler
from rest.api.schedulers.kubectl_env_expire_scheduler import KubectlEnvExpireScheduler
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

    if "docker" in deploy_on:
        # start schedulers
        DockerScheduler().start()
        DockerEnvExpireScheduler(env_expire_in=env_expire_in).start()  # minutes
        DockerCleanFolderScheduler().start()

        app = DockerView().get_app()
        DockerView.register(app)
        app.run(host='0.0.0.0', port=properties["port"])
    elif "kubectl" in deploy_on:
        KubectlEnvExpireScheduler(env_expire_in=env_expire_in).start()

        app = KubectlView().get_app()
        KubectlView.register(app)
        app.run(host='0.0.0.0', port=properties["port"])
    else:
        raise NotImplementedError("Deploy on '%s' option is not supported" % deploy_on)

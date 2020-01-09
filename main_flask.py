#!/usr/bin/python3
import os

from about import properties
from rest.api.eureka_registrator import EurekaRegistrator
from rest.api.logginghelpers.message_dumper import MessageDumper
from rest.api.schedulers.docker_clean_folder_scheduler import DockerCleanFolderScheduler
from rest.api.schedulers.docker_env_expire_scheduler import DockerEnvExpireScheduler
from rest.api.schedulers.docker_scheduler import DockerScheduler
from rest.api.schedulers.kubectl_env_expire_scheduler import KubectlEnvExpireScheduler
from rest.api.views.docker_view import DockerView
from rest.api.views.kubectl_view import KubectlView

if __name__ == "__main__":

    app_append_id = ""
    deploy_on = "kubectl"  # default runs on docker
    env_expire_in = 1440  # minutes

    if os.environ.get('APP_APPEND_ID'):
        app_append_id = os.environ.get('APP_APPEND_ID').lower()
    if os.environ.get('EUREKA_SERVER'):
        EurekaRegistrator(os.environ.get('EUREKA_SERVER')).register_app(os.environ.get("APP_IP_PORT"), app_append_id)
    if os.environ.get('DEPLOY_ON'):
        deploy_on = os.environ.get("DEPLOY_ON")
    if os.environ.get('ENV_EXPIRE_IN'):
        env_expire_in = int(os.environ.get("ENV_EXPIRE_IN"))

    host = '0.0.0.0'
    port = properties["port"]
    fluentd_tag = "startup"
    message_dumper = MessageDumper()

    if "docker" in deploy_on:
        # start schedulers
        view = DockerView()

        DockerScheduler().start()
        DockerEnvExpireScheduler(fluentd_utils=view.get_view_fluentd_utils(),
                                 env_expire_in=env_expire_in).start()  # minutes
        DockerCleanFolderScheduler().start()


    elif "kubectl" in deploy_on:
        # start schedulers
        view = KubectlView()

        KubectlEnvExpireScheduler(fluentd_utils=view.get_view_fluentd_utils(),
                                  env_expire_in=env_expire_in).start()
    else:
        raise NotImplementedError("Deploy on '%s' option is not supported" % deploy_on)

    app = view.get_view_app()
    fluentd_utils = view.get_view_fluentd_utils()
    view.register(app)

    environ_dump = message_dumper.dump_message(dict(os.environ))
    ip_port_dump = message_dumper.dump_message({"host": host, "port": port})

    app.logger.debug({"msg": environ_dump})
    app.logger.debug({"msg": ip_port_dump})

    fluentd_utils.debug(fluentd_tag, environ_dump)

    app.run(host=host, port=port)

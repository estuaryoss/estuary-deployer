#!/usr/bin/python3
from pathlib import Path

from fluent import sender

from about import properties
from rest.api.constants.env_constants import EnvConstants
from rest.api.constants.env_init import EnvInit
from rest.api.loghelpers.message_dumper import MessageDumper
from rest.api.schedulers.scheduler_aggregator import SchedulerAggregator
from rest.api.views import app
from rest.api.views.docker_view import DockerView
from rest.api.views.kubectl_view import KubectlView
from rest.environment.environment import EnvironmentSingleton
from rest.service.eureka import Eureka
from rest.service.fluentd import Fluentd
from rest.utils.env_startup import EnvStartupSingleton
from rest.utils.io_utils import IOUtils

DockerView.register(app=app)
KubectlView.register(app=app)

if __name__ == "__main__":

    fluentd_tag = "startup"
    host = '0.0.0.0'
    message_dumper = MessageDumper()
    io_utils = IOUtils()

    if EnvStartupSingleton.get_instance().get_config_env_vars().get(EnvConstants.EUREKA_SERVER):
        Eureka(EnvStartupSingleton.get_instance().get_config_env_vars().get(EnvConstants.EUREKA_SERVER)).register_app(
            EnvStartupSingleton.get_instance().get_config_env_vars().get(EnvConstants.APP_IP_PORT),
            EnvStartupSingleton.get_instance().get_config_env_vars().get(EnvConstants.APP_APPEND_ID))

    io_utils.create_dir(Path(EnvInit.DEPLOY_PATH))
    io_utils.create_dir(Path(EnvInit.TEMPLATES_PATH))
    io_utils.create_dir(Path(EnvInit.VARIABLES_PATH))

    SchedulerAggregator(
        env_expire_in=EnvStartupSingleton.get_instance().get_config_env_vars().get(EnvConstants.ENV_EXPIRE_IN)).start()

    environ_dump = message_dumper.dump_message(EnvironmentSingleton.get_instance().get_env_and_virtual_env())
    ip_port_dump = message_dumper.dump_message(
        {"host": host, "port": EnvStartupSingleton.get_instance().get_config_env_vars().get(EnvConstants.PORT)})

    app.logger.debug({"msg": environ_dump})
    app.logger.debug({"msg": ip_port_dump})
    app.logger.debug({"msg": EnvStartupSingleton.get_instance().get_config_env_vars()})

    logger = \
        sender.FluentSender(tag=properties.get('name'),
                            host=EnvStartupSingleton.get_instance().get_config_env_vars().get(
                                EnvConstants.FLUENTD_IP_PORT).split(":")[0],
                            port=int(EnvStartupSingleton.get_instance().get_config_env_vars().get(
                                EnvConstants.FLUENTD_IP_PORT).split(":")[1])) \
            if EnvStartupSingleton.get_instance().get_config_env_vars().get(EnvConstants.FLUENTD_IP_PORT) else None
    fluentd_utils = Fluentd(logger)
    fluentd_utils.emit(tag=fluentd_tag, msg=environ_dump)

    app.run(host=host, port=EnvStartupSingleton.get_instance().get_config_env_vars().get(EnvConstants.PORT))

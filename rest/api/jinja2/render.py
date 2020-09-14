#!/usr/bin/env python3

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import os
import sys

import jinja2
import yaml

from rest.api.constants.env_constants import EnvConstants
from rest.environment.environment import EnvironmentSingleton


class Render:

    def __init__(self, template=None, variables=None):
        """
        Custom jinja2 render
        """
        self.template = template
        self.variables = variables
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(
                EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.TEMPLATES_DIR)),
            extensions=['jinja2.ext.autoescape', 'jinja2.ext.do', 'jinja2.ext.loopcontrols', 'jinja2.ext.with_'],
            autoescape=True,
            trim_blocks=True)

    @staticmethod
    def yaml_filter(value):
        return yaml.dump(value, Dumper=yaml.RoundTripDumper, indent=4)

    @staticmethod
    def env_override(value, key):
        return os.getenv(key, value)

    def rend_template(self, vars_dir=EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
        EnvConstants.VARS_DIR)):
        with open(vars_dir + "/" + self.variables, closefd=True) as f:
            data = yaml.safe_load(f)

        self.env.filters['yaml'] = self.yaml_filter
        self.env.globals["environ"] = lambda key: EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(key)
        self.env.globals["get_context"] = lambda: data

        try:
            template = self.env.get_template(self.template).render(data)
        except Exception as e:
            raise e
        sys.stdout.write(template)

        return template

    def get_jinja2env(self):
        return self.env


if __name__ == '__main__':
    render = Render(EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(EnvConstants.TEMPLATE),
                    EnvironmentSingleton.get_instance().get_env_and_virtual_env().get(
                        EnvConstants.VARIABLES)).rend_template()

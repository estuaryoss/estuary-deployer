#!/usr/bin/env python3

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import os
import jinja2
import sys
import yaml

class Render:

    def __init__(self, template=None, variables=None, templates_dir=os.environ.get('TEMPLATES_DIR')):
        self.template = template
        self.variables = variables
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(templates_dir),
            extensions=['jinja2.ext.autoescape', 'jinja2.ext.do', 'jinja2.ext.loopcontrols', 'jinja2.ext.with_'],
            autoescape=True,
            trim_blocks=True)

    def yaml_filter(self, value):
        return yaml.dump(value, Dumper=yaml.RoundTripDumper, indent=4)

    def env_override(self, value, key):
        return os.getenv(key, value)

    def rend_template(self, vars_dir=os.environ.get('VARS_DIR')):
        with open(vars_dir + "/" + self.variables, closefd=True) as f:
            data = yaml.load(f, Loader=yaml.Loader)

        self.env.filters['yaml'] = self.yaml_filter
        self.env.globals["environ"] = lambda key: os.environ.get(key)
        self.env.globals["get_context"] = lambda: data

        try:
            template = self.env.get_template(self.template).render(data)
        except Exception as e:
            raise e
        sys.stdout.write(template)

        return template

    def get_jinja2env(self):
        return self.env

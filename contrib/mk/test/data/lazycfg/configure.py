#!/usr/bin/env python

from os.path import dirname, abspath
import sys
import logging

# For now, fake get configurelib on the path.
sys.path.insert(0, dirname(dirname(dirname(dirname(abspath(__file__))))))
from configurelib import main, ConfigVar, ConfigureError, Profile


log = logging.getLogger("configure")


#---- config vars

class Foo(ConfigVar):
    name = "foo"

    def add_options(self, optparser):
        optparser.add_option("--foo", help="what should foo be?")

    def determine(self, config_var_from_name, options):
        self.value = "bar"  # default
        if options.foo is not None:
            self.value = options.foo


config_vars = [
    Foo(),
]


#---- mainline

if __name__ == "__main__":
    main(config_vars, project_name="lazycfg")


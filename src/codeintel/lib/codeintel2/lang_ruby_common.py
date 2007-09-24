#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See LICENSE.txt for license details.

"""Common routines for ruby and ruby/rhtml support for CodeIntel"""

import os.path
import logging

log = logging.getLogger("codeintel.ruby.common")
#log.setLevel(logging.DEBUG)
class RubyCommonBufferMixin:
    def check_for_rails_app_path(self, path):
        self.framework_role = None
        if path is None:
            #log.debug("check_for_rails_app_path: no path given")
            return
        apath = os.path.abspath(path)
        aplist = apath.split(os.path.sep)
        role_root = "rails"
        if len(aplist) < 3:
            return
        elif (aplist[-3] == "app" and
            (aplist[-2] == "controllers" and aplist[-1].endswith(".rb")
             or aplist[-2] == "helpers" and aplist[-1].endswith("_helper.rb")
             or aplist[-2] == "models" and aplist[-1].endswith(".rb"))):
            role = '.'.join((role_root, aplist[-2]))
        elif (len(aplist) >= 4
              and aplist[-4] == "app" and aplist[-3] == "views"
              and aplist[-1].endswith(".rhtml")):
            role = '.'.join((role_root, aplist[-3], aplist[-2]))
        elif (aplist[-3] == "db" and aplist[-2] == "migrate"
              and aplist[-1][0].isdigit()
              and aplist[-1].endswith(".rb")):
            role = '.'.join((role_root, aplist[-3], aplist[-2]))        
        elif (aplist[-3] == "test"
              and aplist[-2] in ("functional", "unit")
              # integration tests not supported until we can find
              # ActionController::IntegrationTest
              and aplist[-1].endswith("_test.rb")):
            role = '.'.join((role_root, aplist[-3], aplist[-2]))        
        else:
            return
        self.framework_role = role



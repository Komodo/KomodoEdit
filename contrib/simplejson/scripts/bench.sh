#!/bin/sh
/usr/bin/env python -mtimeit -s 'from simplejson.tests.test_pass1 import test_parse' 'test_parse()'

# -*- coding: utf-8 -*-
#
#  SelfTest/Hash/__init__.py: Self-test for hash modules
#
# Written in 2008 by Dwayne C. Litzenberger <dlitz@dlitz.net>
#
# ===================================================================
# The contents of this file are dedicated to the public domain.  To
# the extent that dedication to the public domain is not available,
# everyone is granted a worldwide, perpetual, royalty-free,
# non-exclusive license to exercise all rights associated with the
# contents of this file for any purpose whatsoever.
# No rights are reserved.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ===================================================================

"""Self-test for hash modules"""
from __future__ import absolute_import

__revision__ = "$Id$"

def get_tests(config={}):
    tests = []
    from . import test_HMAC;   tests += test_HMAC.get_tests(config=config)
    from . import test_MD2;    tests += test_MD2.get_tests(config=config)
    from . import test_MD4;    tests += test_MD4.get_tests(config=config)
    from . import test_MD5;    tests += test_MD5.get_tests(config=config)
    from . import test_RIPEMD; tests += test_RIPEMD.get_tests(config=config)
    from . import test_SHA;    tests += test_SHA.get_tests(config=config)
    from . import test_SHA256; tests += test_SHA256.get_tests(config=config)
    return tests

if __name__ == '__main__':
    import unittest
    suite = lambda: unittest.TestSuite(get_tests())
    unittest.main(defaultTest='suite')

# vim:set ts=4 sw=4 sts=4 expandtab:

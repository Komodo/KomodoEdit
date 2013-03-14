# Copyright (c) 2012-2013 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import unittest

from xpcom import components

class koLanguageSvcTestCase(unittest.TestCase):
    """Base class for koIDocument test cases."""
    _langRegistrySvc = None
    @property
    def langRegistrySvc(self):
        if self._langRegistrySvc is None:
            self._langRegistrySvc = components.classes['@activestate.com/koLanguageRegistryService;1'].\
                                        getService(components.interfaces.koILanguageRegistryService)
        return self._langRegistrySvc

    def _check_filepath_language(self, filepath, expected_lang):
        found_lang = self.langRegistrySvc.suggestLanguageForFile(filepath)
        self.assertEqual(found_lang, expected_lang,
                         "Incorrect language given for path %r, got %r, expected %r"
                         % (filepath, found_lang, expected_lang))


    def test_html_recognition(self):
        self._check_filepath_language("foo.html", "HTML")

    def test_django_recognition(self):
        self._check_filepath_language("foo.django.html", "Django")

    def test_django_recognition(self):
        self._check_filepath_language("foo.django.html", "Django")

    #def test_template_toolkit_recognition(self):
    #    self._check_filepath_language("ttk-test01.ttkt.html", "Template Toolkit")

    def test_erb_recognition(self):
        self._check_filepath_language("foo.html.erb", "RHTML")

    def test_scss_recognition(self):
        self._check_filepath_language("foo.css.scss", "SCSS")

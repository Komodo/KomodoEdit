"""Language package for AngularJS"""

from xpcom import components, ServerException

from koLanguageServiceBase import *
from koXMLLanguageBase import koHTMLLanguageBase

def registerLanguage(registery):
    registery.registerLanguage(KoAngularJSLanguage())

class KoAngularJSLanguage(koHTMLLanguageBase):
    name = "AngularJS"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{da0400ca-579b-4f1d-98b7-65e41908c400}"
    _reg_categories_ = [("komodo-language", name)]
    
    lexresLangName = "AngularJS"
    lang_from_udl_family = {'CSL': 'JavaScript', 'M': 'AngularJS', 'CSS': 'CSS'}

    primary = 1
    accessKey = 'n'
    defaultExtension = ".html"

    _lineup_chars = '' # don't indent ()'s and the like in HTML!
    _lineup_open_chars = "" # don't indent ()'s and the like in HTML!

    # The set of elements which do not have a close tag. See
    # http://www.whatwg.org/specs/web-apps/current-work/multipage/syntax.html#void-elements
    _void_elements = set(("area", "base", "br", "col", "command", "embed", "hr",
                          "img", "input", "keygen", "link", "meta", "param",
                          "source", "track", "wbr"))

    sample = """<div ng-app="ngAppStrictDemo" ng-strict-di>
    <div ng-controller="GoodController1">
        I can add: {{a}} + {{b}} =  {{ a+b }}

        <p>This renders because the controller does not fail to
           instantiate, by using explicit annotation style (see
           script.js for details)
        </p>
    </div>

    <div ng-controller="GoodController2">
        Name: <input ng-model="name"><br />
        Hello, {{name}}!

        <p>This renders because the controller does not fail to
           instantiate, by using explicit annotation style
           (see script.js for details)
        </p>
    </div>

    <div ng-controller="BadController">
        I can add: {{a}} + {{b}} =  {{ a+b }}

        <p>The controller could not be instantiated, due to relying
           on automatic function annotations (which are disabled in
           strict mode). As such, the content of this section is not
           interpolated, and there should be an error in your web console.
        </p>
    </div>
</div>
"""

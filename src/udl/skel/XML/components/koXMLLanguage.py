from xpcom import components

from koLanguageServiceBase import *
from koXMLLanguageBase import koXMLLanguageBase

log = logging.getLogger('koXMLLanguage')

def registerLanguage(registery):
    registery.registerLanguage(koXMLLanguage())
    
class koXMLLanguage(koXMLLanguageBase):
    name = "XML"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{13CE88EE-3F2D-4ad4-8D33-CC8178E4BA26}"

    lexresLangName = "XML"
    lang_from_udl_family = {'M': 'XML'}

    accessKey = 'x'
    primary = 1
    defaultExtension = ".xml"
    sample = """<?xml version="1.0" encoding="UTF-8"?>
<!-- This sample XML file shows you ... -->

<Class>
<Order Name="TINAMIFORMES">
        <Family Name="TINAMIDAE">
            <Species attr="value">content.</Species>
            <![CDATA[
                This is a CDATA section
            ]]>
        </Family>
    </Order>
"""
 

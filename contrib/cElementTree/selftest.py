# $Id$
# elementtree selftest program

# this test script uses Python's "doctest" module to check that the
# *test script* works as expected.

import sys, StringIO

import cElementTree as ElementTree

def unserialize(text):
    import StringIO
    file = StringIO.StringIO(text)
    tree = ElementTree.parse(file)
    return tree.getroot()

def serialize(elem, encoding=None):
    import StringIO
    file = StringIO.StringIO()
    tree = ElementTree.ElementTree(elem)
    if encoding:
        tree.write(file, encoding)
    else:
        tree.write(file)
    return file.getvalue()

def summarize(elem):
    return elem.tag

def summarize_list(seq):
    return map(summarize, seq)

SAMPLE_XML = unserialize("""
<body>
  <tag>text</tag>
  <tag />
  <section>
    <tag>subtext</tag>
  </section>
</body>
""")

SAMPLE_XML_NS = unserialize("""
<body xmlns="http://effbot.org/ns">
  <tag>text</tag>
  <tag />
  <section>
    <tag>subtext</tag>
  </section>
</body>
""")

# interface tests

def check_string(string):
    len(string)
    for char in string:
        if len(char) != 1:
            print "expected one-character string, got %r" % char
    new_string = string + ""
    new_string = string + " "
    string[:0]

def check_mapping(mapping):
    len(mapping)
    keys = mapping.keys()
    items = mapping.items()
    for key in keys:
        item = mapping[key]
    mapping["key"] = "value"
    if mapping["key"] != "value":
        print "expected value string, got %r" % mapping["key"]

def check_element(element):
    if not ElementTree.iselement(element):
        print "not an element"
    if not hasattr(element, "tag"):
        print "no tag member"
    if not hasattr(element, "attrib"):
        print "no attrib member"
    if not hasattr(element, "text"):
        print "no text member"
    if not hasattr(element, "tail"):
        print "no tail member"
    check_string(element.tag)
    check_mapping(element.attrib)
    if element.text != None:
        check_string(element.text)
    if element.tail != None:
        check_string(element.tail)

def check_element_tree(tree):
    check_element(tree.getroot())

def check_method(method):
    if not callable(method):
        print method, "not callable"

def version():
    """
    >>> ElementTree.__version__
    '1.0.5'
    >>> ElementTree.VERSION
    '1.0.5'
    """

def element():
    """
    Test element tree interface.

    >>> element = ElementTree.Element("tag")
    >>> check_element(element)
    >>> tree = ElementTree.ElementTree(element)
    >>> check_element_tree(tree)

    Make sure all standard element methods exist.

    >>> check_method(element.append)
    >>> check_method(element.insert)
    >>> check_method(element.remove)
    >>> check_method(element.getchildren)
    >>> check_method(element.find)
    >>> check_method(element.findall)
    >>> check_method(element.findtext)
    >>> check_method(element.clear)
    >>> check_method(element.get)
    >>> check_method(element.set)
    >>> check_method(element.keys)
    >>> check_method(element.items)
    >>> check_method(element.getiterator)

    Basic method sanity checks.

    >>> serialize(element) # 1
    '<tag key="value" />'
    >>> subelement = ElementTree.Element("subtag")
    >>> element.append(subelement)
    >>> serialize(element) #  2
    '<tag key="value"><subtag /></tag>'
    >>> element.insert(0, subelement)
    >>> serialize(element) # 3
    '<tag key="value"><subtag /><subtag /></tag>'
    >>> element.remove(subelement)
    >>> serialize(element) # 4
    '<tag key="value"><subtag /></tag>'
    >>> element.remove(subelement)
    >>> serialize(element) # 5
    '<tag key="value" />'
    >>> element.remove(subelement)
    Traceback (most recent call last):
    ValueError: list.remove(x): x not in list
    >>> serialize(element) # 6
    '<tag key="value" />'

    """

def parsefile():
    """
    Test parsing from file.  Note that we're opening the files in
    here; by default, the 'parse' function opens the file in binary
    mode, and doctest doesn't filter out carriage returns.

    >>> tree = ElementTree.parse(open("samples/simple.xml", "r"))
    >>> tree.write(sys.stdout)
    <root>
       <element key="value">text</element>
       <element>text</element>tail
       <empty-element />
    </root>
    >>> tree = ElementTree.parse(open("samples/simple-ns.xml", "r"))
    >>> tree.write(sys.stdout)
    <ns0:root xmlns:ns0="namespace">
       <ns0:element key="value">text</ns0:element>
       <ns0:element>text</ns0:element>tail
       <ns0:empty-element />
    </ns0:root>

    >>> parser = ElementTree.XMLParser()
    >>> parser.version
    'Expat 1.95.8'
    >>> parser.feed(open("samples/simple.xml").read())
    >>> print serialize(parser.close())
    <root>
       <element key="value">text</element>
       <element>text</element>tail
       <empty-element />
    </root>

    >>> parser = ElementTree.XMLTreeBuilder() # 1.2 compatibility
    >>> parser.feed(open("samples/simple.xml").read())
    >>> print serialize(parser.close())
    <root>
       <element key="value">text</element>
       <element>text</element>tail
       <empty-element />
    </root>

    >>> target = ElementTree.TreeBuilder()
    >>> parser = ElementTree.XMLParser(target=target)
    >>> parser.feed(open("samples/simple.xml").read())
    >>> print serialize(parser.close())
    <root>
       <element key="value">text</element>
       <element>text</element>tail
       <empty-element />
    </root>
    """

def writefile():
    """
    >>> elem = ElementTree.Element("tag")
    >>> elem.text = "text"
    >>> serialize(elem)
    '<tag>text</tag>'
    >>> ElementTree.SubElement(elem, "subtag").text = "subtext"
    >>> serialize(elem)
    '<tag>text<subtag>subtext</subtag></tag>'
    >>> elem.insert(0, ElementTree.Comment("comment"))
    >>> serialize(elem)
    '<tag>text<!-- comment --><subtag>subtext</subtag></tag>'
    >>> elem[0] = ElementTree.PI("key", "value")
    >>> serialize(elem)
    '<tag>text<?key value?><subtag>subtext</subtag></tag>'
    """

def encoding():
    r"""
    Test encoding issues.

    >>> elem = ElementTree.Element("tag")
    >>> elem.text = u"abc"
    >>> serialize(elem)
    '<tag>abc</tag>'
    >>> serialize(elem, "utf-8")
    '<tag>abc</tag>'
    >>> serialize(elem, "us-ascii")
    '<tag>abc</tag>'
    >>> serialize(elem, "iso-8859-1")
    "<?xml version='1.0' encoding='iso-8859-1'?>\n<tag>abc</tag>"

    >>> elem.text = "<&\"\'>"
    >>> serialize(elem)
    '<tag>&lt;&amp;"\'&gt;</tag>'
    >>> serialize(elem, "utf-8")
    '<tag>&lt;&amp;"\'&gt;</tag>'
    >>> serialize(elem, "us-ascii") # cdata characters
    '<tag>&lt;&amp;"\'&gt;</tag>'
    >>> serialize(elem, "iso-8859-1")
    '<?xml version=\'1.0\' encoding=\'iso-8859-1\'?>\n<tag>&lt;&amp;"\'&gt;</tag>'

    >>> elem.attrib["key"] = "<&\"\'>"
    >>> elem.text = None
    >>> serialize(elem)
    '<tag key="&lt;&amp;&quot;&apos;&gt;" />'
    >>> serialize(elem, "utf-8")
    '<tag key="&lt;&amp;&quot;&apos;&gt;" />'
    >>> serialize(elem, "us-ascii")
    '<tag key="&lt;&amp;&quot;&apos;&gt;" />'
    >>> serialize(elem, "iso-8859-1")
    '<?xml version=\'1.0\' encoding=\'iso-8859-1\'?>\n<tag key="&lt;&amp;&quot;&apos;&gt;" />'

    >>> elem.text = u'\xe5\xf6\xf6<>'
    >>> elem.attrib.clear()
    >>> serialize(elem)
    '<tag>&#229;&#246;&#246;&lt;&gt;</tag>'
    >>> serialize(elem, "utf-8")
    '<tag>\xc3\xa5\xc3\xb6\xc3\xb6&lt;&gt;</tag>'
    >>> serialize(elem, "us-ascii")
    '<tag>&#229;&#246;&#246;&lt;&gt;</tag>'
    >>> serialize(elem, "iso-8859-1")
    "<?xml version='1.0' encoding='iso-8859-1'?>\n<tag>\xe5\xf6\xf6&lt;&gt;</tag>"

    >>> elem.attrib["key"] = u'\xe5\xf6\xf6<>'
    >>> elem.text = None
    >>> serialize(elem)
    '<tag key="&#229;&#246;&#246;&lt;&gt;" />'
    >>> serialize(elem, "utf-8")
    '<tag key="\xc3\xa5\xc3\xb6\xc3\xb6&lt;&gt;" />'
    >>> serialize(elem, "us-ascii")
    '<tag key="&#229;&#246;&#246;&lt;&gt;" />'
    >>> serialize(elem, "iso-8859-1")
    '<?xml version=\'1.0\' encoding=\'iso-8859-1\'?>\n<tag key="\xe5\xf6\xf6&lt;&gt;" />'

    """

def qname():
    """
    Test QName handling.

    1) decorated tags

    >>> elem = ElementTree.Element("{uri}tag")
    >>> serialize(elem) # 1.1
    '<ns0:tag xmlns:ns0="uri" />'

    2) decorated attributes

    >>> elem.attrib["{uri}key"] = "value"
    >>> serialize(elem) # 2.1
    '<ns0:tag ns0:key="value" xmlns:ns0="uri" />'

    """

def cdata():
    """
    Test CDATA handling (etc).

    >>> serialize(unserialize("<tag>hello</tag>"))
    '<tag>hello</tag>'
    >>> serialize(unserialize("<tag>&#104;&#101;&#108;&#108;&#111;</tag>"))
    '<tag>hello</tag>'
    >>> serialize(unserialize("<tag><![CDATA[hello]]></tag>"))
    '<tag>hello</tag>'

    """

def find():
    """
    Test find methods (including xpath syntax).

    >>> elem = SAMPLE_XML
    >>> elem.find("tag").tag
    'tag'
    >>> ElementTree.ElementTree(elem).find("tag").tag
    'tag'
    >>> elem.find("section/tag").tag
    'tag'
    >>> ElementTree.ElementTree(elem).find("section/tag").tag
    'tag'
    >>> elem.findtext("tag")
    'text'
    >>> elem.findtext("tog", "default")
    'default'
    >>> ElementTree.ElementTree(elem).findtext("tag")
    'text'
    >>> elem.findtext("section/tag")
    'subtext'
    >>> ElementTree.ElementTree(elem).findtext("section/tag")
    'subtext'
    >>> summarize_list(elem.findall("tag"))
    ['tag', 'tag']
    >>> summarize_list(elem.findall("*"))
    ['tag', 'tag', 'section']
    >>> summarize_list(elem.findall(".//tag"))
    ['tag', 'tag', 'tag']
    >>> summarize_list(elem.findall("section/tag"))
    ['tag']
    >>> summarize_list(elem.findall("section//tag"))
    ['tag']
    >>> summarize_list(elem.findall("section/*"))
    ['tag']
    >>> summarize_list(elem.findall("section//*"))
    ['tag']
    >>> summarize_list(elem.findall("section/.//*"))
    ['tag']
    >>> summarize_list(elem.findall("*/*"))
    ['tag']
    >>> summarize_list(elem.findall("*//*"))
    ['tag']
    >>> summarize_list(elem.findall("*/tag"))
    ['tag']
    >>> summarize_list(elem.findall("*/./tag"))
    ['tag']
    >>> summarize_list(elem.findall("./tag"))
    ['tag', 'tag']
    >>> summarize_list(elem.findall(".//tag"))
    ['tag', 'tag', 'tag']
    >>> summarize_list(elem.findall("././tag"))
    ['tag', 'tag']
    >>> summarize_list(ElementTree.ElementTree(elem).findall("/tag"))
    ['tag', 'tag']
    >>> summarize_list(ElementTree.ElementTree(elem).findall("./tag"))
    ['tag', 'tag']
    >>> elem = SAMPLE_XML_NS
    >>> summarize_list(elem.findall("tag"))
    []
    >>> summarize_list(elem.findall("{http://effbot.org/ns}tag"))
    ['{http://effbot.org/ns}tag', '{http://effbot.org/ns}tag']
    >>> summarize_list(elem.findall(".//{http://effbot.org/ns}tag"))
    ['{http://effbot.org/ns}tag', '{http://effbot.org/ns}tag', '{http://effbot.org/ns}tag']
    """

def copy():
    """
    Test copy handling (etc).

    >>> import copy
    >>> e1 = unserialize("<tag>hello<foo/></tag>")
    >>> e2 = copy.copy(e1)
    >>> e3 = copy.deepcopy(e1)
    >>> e1.find("foo").tag = "bar"
    >>> serialize(e1)
    '<tag>hello<bar /></tag>'
    >>> serialize(e2)
    '<tag>hello<bar /></tag>'
    >>> serialize(e3)
    '<tag>hello<foo /></tag>'

    """

def attrib():
    """
    Test attribute handling.

    >>> elem = ElementTree.Element("tag")
    >>> elem.get("key") # 1.1
    >>> elem.get("key", "default") # 1.2
    'default'
    >>> elem.set("key", "value")
    >>> elem.get("key") # 1.3
    'value'

    >>> elem = ElementTree.Element("tag", key="value")
    >>> elem.get("key") # 2.1
    'value'
    >>> elem.attrib # 2.2
    {'key': 'value'}

    >>> attrib = {"key": "value"}
    >>> elem = ElementTree.Element("tag", attrib)
    >>> attrib.clear() # check for aliasing issues
    >>> elem.get("key") # 3.1
    'value'
    >>> elem.attrib # 3.2
    {'key': 'value'}

    >>> attrib = {"key": "value"}
    >>> elem = ElementTree.Element("tag", **attrib)
    >>> attrib.clear() # check for aliasing issues
    >>> elem.get("key") # 4.1
    'value'
    >>> elem.attrib # 4.2
    {'key': 'value'}

    >>> elem = ElementTree.Element("tag", {"key": "other"}, key="value")
    >>> elem.get("key") # 5.1
    'value'
    >>> elem.attrib # 5.2
    {'key': 'value'}

    """

def makeelement():
    """
    Test makeelement handling.

    >>> elem = ElementTree.Element("tag")
    >>> attrib = {"key": "value"}
    >>> subelem = elem.makeelement("subtag", attrib)
    >>> if subelem.attrib is attrib:
    ...     print "attrib aliasing"
    >>> elem.append(subelem)
    >>> serialize(elem)
    '<tag><subtag key="value" /></tag>'

    >>> elem.clear()
    >>> serialize(elem)
    '<tag />'
    >>> elem.append(subelem)
    >>> serialize(elem)
    '<tag><subtag key="value" /></tag>'

    """

def iterparse():
    """
    Test iterparse interface.

    >>> context = ElementTree.iterparse("samples/simple.xml")
    >>> for action, elem in context:
    ...   print action, elem.tag
    end element
    end element
    end empty-element
    end root
    >>> context.root.tag
    'root'

    >>> context = ElementTree.iterparse("samples/simple-ns.xml")
    >>> for action, elem in context:
    ...   print action, elem.tag
    end {namespace}element
    end {namespace}element
    end {namespace}empty-element
    end {namespace}root

    >>> events = ()
    >>> context = ElementTree.iterparse("samples/simple.xml", events)
    >>> for action, elem in context:
    ...   print action, elem.tag

    >>> events = ()
    >>> context = ElementTree.iterparse("samples/simple.xml", events=events)
    >>> for action, elem in context:
    ...   print action, elem.tag

    >>> events = ("start", "end")
    >>> context = ElementTree.iterparse("samples/simple.xml", events)
    >>> for action, elem in context:
    ...   print action, elem.tag
    start root
    start element
    end element
    start element
    end element
    start empty-element
    end empty-element
    end root

    >>> events = ("start", "end")
    >>> context = ElementTree.iterparse("samples/simple-ns.xml", events)
    >>> for action, elem in context:
    ...   if action in ("start", "end"):
    ...     print action, elem.tag
    ...   else:
    ...     print action, elem
    start {namespace}root
    start {namespace}element
    end {namespace}element
    start {namespace}element
    end {namespace}element
    start {namespace}empty-element
    end {namespace}empty-element
    end {namespace}root

    >>> events = ("start", "end", "bogus")
    >>> context = ElementTree.iterparse("samples/simple.xml", events)
    >>> if sys.version[:3] > "2.1": # don't apply this test for 2.1
    ...   for action, elem in context:
    ...     if action in ("start", "end"):
    ...       print action, elem.tag
    ...     else:
    ...       print action, elem
    ... else:
    ...   raise ValueError("unknown event 'bogus'")
    Traceback (most recent call last):
    ValueError: unknown event 'bogus'
    """

def custom_builder():
    """
    Test parser w. custom builder.

    >>> class Builder:
    ...     def start(self, tag, attrib):
    ...         print "start", tag
    ...     def end(self, tag):
    ...         print "end", tag
    ...     def data(self, text):
    ...         pass
    >>> builder = Builder()
    >>> parser = ElementTree.XMLParser(builder)
    >>> parser.feed(open("samples/simple.xml", "r").read())
    start root
    start element
    end element
    start element
    end element
    start empty-element
    end empty-element
    end root

    >>> class Builder:
    ...     def start(self, tag, attrib):
    ...         print "start", tag
    ...     def end(self, tag):
    ...         print "end", tag
    ...     def data(self, text):
    ...         pass
    ...     def pi(self, target, data):
    ...         print "pi", target, repr(data)
    ...     def comment(self, data):
    ...         print "comment", repr(data)
    >>> builder = Builder()
    >>> parser = ElementTree.XMLParser(builder)
    >>> parser.feed(open("samples/simple-ns.xml", "r").read())
    pi pi 'data'
    comment ' comment '
    start {namespace}root
    start {namespace}element
    end {namespace}element
    start {namespace}element
    end {namespace}element
    start {namespace}empty-element
    end {namespace}empty-element
    end {namespace}root

    """

def getchildren():
    """

    >>> tree = ElementTree.parse(open("samples/simple.xml", "r"))
    >>> for elem in tree.getiterator():
    ...     summarize_list(elem.getchildren())
    ['element', 'element', 'empty-element']
    []
    []
    []

    """

ENTITY_XML = """\
<!DOCTYPE points [
<!ENTITY % user-entities SYSTEM 'user-entities.xml'>
%user-entities;
]>
<document>&entity;</document>
"""

def entity():
    """
    Test entity handling.

    1) bad entities

    >>> ElementTree.XML("<document>&entity;</document>")
    Traceback (most recent call last):
    SyntaxError: undefined entity: line 1, column 10

    2) custom entity

    >>> parser = ElementTree.XMLParser()
    >>> parser.entity["entity"] = "text"
    >>> parser.feed(ENTITY_XML)
    >>> root = parser.close()
    >>> serialize(root)
    '<document>text</document>'

    """

#
# reported bugs

class ExceptionFile:
    def read(self, x):
        raise IOError

def xmltoolkit60():
    """
    Handle crash in stream source.
    >>> tree = ElementTree.parse(ExceptionFile())
    Traceback (most recent call last):
    IOError
    """

def xmltoolkit61(encoding):
    """
    Handle non-standard encodings.
    >>> xmltoolkit61("ascii")
    >>> xmltoolkit61("us-ascii")
    >>> xmltoolkit61("iso-8859-1")
    >>> xmltoolkit61("iso-8859-15")
    >>> xmltoolkit61("cp437")
    >>> xmltoolkit61("mac-roman")
    """
    ElementTree.XML(
        "<?xml version='1.0' encoding='%s'?><xml />" % encoding
        )

if __name__ == "__main__":
    import doctest
    failed, tested = doctest.testmod(__import__(__name__))
    print tested - failed, "tests ok."

# $Id$
# sgmlop selftest (designed for python 2.1)
#
# See the README file for information on usage and redistribution.

import sgmlop, string

class echo_handler:
    def handle_special(self, text):
        print "SPECIAL", repr(text)
    def handle_proc(self, target, value):
        print "PROC", repr(target), repr(value)
    def finish_starttag(self, tag, attrs):
        print "START", tag,
        if isinstance(attrs, type({})):
            items = attrs.items()
            items.sort()
            attrs = "{"
            for key, value in items:
                if len(attrs) > 1:
                    attrs = attrs + ", "
                attrs = attrs + "%r: %r" % (key, value)
            attrs = attrs + "}"
        else:
            attrs = repr(attrs)
        print attrs
    def finish_endtag(self, tag):
        print "END", tag
    def handle_data(self, data):
        print "DATA", repr(data)

class recursive_handler(echo_handler):
    parser = None
    def finish_starttag(self, tag, attrs):
        echo_handler.finish_starttag(self, tag, attrs)
        self.parser.feed("")

class entity_handler(echo_handler):
    def handle_entityref(self, entityref):
        print "ENTITY", entityref

class charref_handler(echo_handler):
    def handle_charref(self, charref):
        print "CHARREF", charref

class entity_resolve_handler(echo_handler):
    def resolve_entityref(self, entityref):
        print "RESOLVE", entityref
        return entityref

# sanity checks

def sanity():
    """
    Basic sanity check
    >>> parser = sgmlop.SGMLParser()
    >>> parser.register(echo_handler())
    >>> parser.feed("<a b='c'>gurk</a>")
    START a [('b', 'c')]
    DATA 'gurk'
    END a
    0
    >>> parser.close()
    0
    >>> parser = sgmlop.XMLParser()
    >>> parser.register(echo_handler())
    >>> parser.feed("<a b='c'>gurk</a>")
    START a {'b': 'c'}
    DATA 'gurk'
    END a
    0
    >>> parser.close()
    0
    """

def doctype():
    """
    Doctype parsing
    >>> parser = sgmlop.XMLParser()
    >>> parser.register(echo_handler())
    >>> parser.feed("<!DOCTYPE html SYSTEM 'html'>")
    SPECIAL "DOCTYPE html SYSTEM 'html'"
    0
    >>> parser.feed("<!DOCTYPE doc [ <!ELEMENT doc (#PCDATA)> ]>")
    SPECIAL 'DOCTYPE doc '
    DATA ' '
    SPECIAL 'ELEMENT doc (#PCDATA)'
    DATA ' '
    SPECIAL ''
    DATA '>'
    0
    >>> parser.close()
    0
    """

def entities():
    """
    Check built-in entities

    1) Using the default entity handler

    >>> parser = sgmlop.XMLParser()
    >>> parser.register(echo_handler())
    >>> parser.feed("&amp;&apos;&gt;&lt;&quot;")
    DATA '&'
    DATA "'"
    DATA '>'
    DATA '<'
    DATA '"'
    0
    >>> parser.feed("&spam;")
    0
    >>> parser.close()
    0

    2) Using an entity handler

    >>> parser = sgmlop.XMLParser()
    >>> parser.register(entity_handler())
    >>> parser.feed("&amp;&apos;&gt;&lt;&quot;")
    ENTITY amp
    ENTITY apos
    ENTITY gt
    ENTITY lt
    ENTITY quot
    0
    >>> parser.feed("&spam;")
    ENTITY spam
    0
    >>> parser.close()
    0

    3) Using an entity resolver

    >>> parser = sgmlop.XMLParser()
    >>> parser.register(entity_resolve_handler())
    >>> parser.feed("&amp;&apos;&gt;&lt;&quot;")
    DATA '&'
    DATA "'"
    DATA '>'
    DATA '<'
    DATA '"'
    0
    >>> parser.feed("&spam;")
    RESOLVE spam
    DATA 'spam'
    0
    >>> parser.close()
    0

    4) Character references

    >>> parser = sgmlop.XMLParser()
    >>> parser.register(entity_resolve_handler())
    >>> parser.feed("&#38;&#39;&#62;&#60;&#34;")
    DATA '&'
    DATA "'"
    DATA '>'
    DATA '<'
    DATA '"'
    0
    >>> parser.feed("&#x26;&#x27;&#x3e;&#x3c;&#x22;")
    DATA '&'
    DATA "'"
    DATA '>'
    DATA '<'
    DATA '"'
    0
    >>> parser.close()
    0
    """

# --------------------------------------------------------------------
# fixed bugs/features (numbers from Secret Labs' issue database)

def bug_xmltoolkit1():
    """
    Make sure the parser doesn't drop characters

    >>> parser = sgmlop.SGMLParser()
    >>> parser.register(echo_handler())
    >>> parser.feed("gurk")
    DATA 'gurk'
    0
    >>> parser.close()
    0
    """

def bug_xmltoolkit2():
    """
    Unicode parsing bug

    >>> parser = sgmlop.XMLParser()
    >>> parser.register(echo_handler())
    >>> parser.feed(u"<a>gurk</a>")
    START a {}
    DATA 'gurk'
    END a
    0
    >>> parser.close()
    0
    """

def bug_xmltoolkit3():
    """
    Check that close doesn't accept optional argument

    >>> parser = sgmlop.XMLParser()
    >>> parser.feed("foo")
    0
    >>> parser.close("bar")
    Traceback (most recent call last):
    TypeError: close() takes exactly 0 arguments (1 given)
    >>> parser.close()
    0
    """

def bug_xmltoolkit4():
    """
    Prevent recursive parsing

    >>> parser = sgmlop.XMLParser()
    >>> handler = recursive_handler()
    >>> parser.register(handler)
    >>> handler.parser = parser # self-reference
    >>> parser.feed(u"<a>gurk</a>")
    Traceback (most recent call last):
    AssertionError: recursive feed
    """

def bug_xmltoolkit7():
    """
    Don't crash on SGML attribute value without key

    >>> parser = sgmlop.SGMLParser()
    >>> parser.register(echo_handler())
    >>> parser.parse('<page title="test" keywords="test" nohome/>')
    START page [('title', 'test'), ('keywords', 'test'), ('nohome', 'nohome')]
    END page
    0
    >>> parser.close()
    0
    """

def bug_xmltoolkit8():
    """
    Check built-in entities

    >>> parser = sgmlop.XMLParser()
    >>> parser.register(echo_handler())
    >>> parser.feed(u"<a>spam&amp;egg</a>")
    START a {}
    DATA 'spam'
    DATA '&'
    DATA 'egg'
    END a
    0
    >>> parser.close()
    0
    """

def bug_xmltoolkit9():
    """
    Expand entities in attributes

    >>> parser = sgmlop.XMLParser()
    >>> parser.register(echo_handler())
    >>> parser.feed("<element class='spam&#38;egg'/>")
    START element {'class': 'spam&egg'}
    END element
    0
    >>> parser.feed("<element class='spam&#x26;egg'/>")
    START element {'class': 'spam&egg'}
    END element
    0
    >>> parser.feed("<element class='spam&amp;egg'/>")
    START element {'class': 'spam&egg'}
    END element
    0
    >>> parser.feed("<element class='spam&ignore;egg'/>")
    START element {'class': 'spamegg'}
    END element
    0
    >>> parser = sgmlop.XMLParser()
    >>> parser.register(entity_resolve_handler())
    >>> parser.feed("<element class='spam&ham;egg' />")
    RESOLVE ham
    START element {'class': 'spamhamegg'}
    END element
    0
    >>> parser.close()
    0
    """

def bug_xmltoolkit11():
    """
    DOCTYPE parsing

    >>> parser = sgmlop.XMLParser()
    >>> parser.register(echo_handler())
    >>> parser.feed(u"<?xml version='1.0'><!doctype foo system 'hello'>")
    PROC 'xml' "version='1.0'"
    SPECIAL "doctype foo system 'hello'"
    0
    >>> parser.close()
    0
    """

def bug_xmltoolkit12():
    """
    Ignore undefined entities in 'sloppy' mode

    >>> parser = sgmlop.XMLParser()
    >>> parser.register(echo_handler())
    >>> parser.feed(u"&undefined;")
    0
    >>> parser.close()
    0
    """

def bug_xmltoolkit15():
    """
    Problem with unicode charrefs.

    >>> parser = sgmlop.XMLParser()
    >>> parser.register(charref_handler())
    >>> parser.feed("&#8364;")
    CHARREF 8364
    0
    >>> parser.register(echo_handler())
    >>> parser.feed("&#8364;") # entity ignored in non-strict 8-bit mode
    0
    >>> parser.feed("<a gurk='&#8364;'>")
    START a {'gurk': ''}
    0
    >>> parser.close()
    0
    """

def bug_xmltoolkit20():
    """
    Problem with empty tags.

    >>> parser = sgmlop.XMLParser()
    >>> parser.register(echo_handler())
    >>> parser.feed("<params/>")
    START params {}
    END params
    0
    >>> parser.feed("<params />")
    START params {}
    END params
    0
    >>> parser.close()
    0
    """

def bug_xmltoolkit24():
    """
    Problems with processing instructions.

    >>> parser = sgmlop.XMLParser()
    >>> parser.register(echo_handler())
    >>> parser.feed("<doc><?target?><?target value?><?target ?></doc>")
    START doc {}
    PROC 'target' ''
    PROC 'target' 'value'
    PROC 'target' ''
    END doc
    0
    """

def bug_xmltoolkit38():
    """
    Problems with unicode characters in attribute values.

    >>> parser = sgmlop.XMLParser()
    >>> parser.register(entity_resolve_handler())
    >>> parser.feed("<doc><img alt='&#8220;value&#8221;' /></doc>")
    START doc {}
    RESOLVE #8220
    RESOLVE #8221
    START img {'alt': '#8220value#8221'}
    END img
    END doc
    0
    """

if __name__ == "__main__":
    import doctest, selftest
    failed, tested = doctest.testmod(selftest)
    print tested - failed, "tests ok."

#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

"""Test some CSS-specific codeintel handling."""

import os
import sys
import re
import random
from os.path import join, dirname, abspath, exists, basename
import unittest
import logging

from codeintel2.common import *
from codeintel2.util import indent, dedent, banner, markup_text, \
                            unmark_text, CompareNPunctLast
from codeintel2.constants_css3 import CSS_ATTR_DICT

from testlib import TestError, TestSkipped, TestFailed, tag
from citestsupport import CodeIntelTestCase



log = logging.getLogger("test")


# We want to provide the same tests for straight CSS as well as for the
# multilang CSS (aka UDL CSS). To do this, we have a base class
# _BaseCSSTestCase, which provides the test code, and then the different
# types of CSS handling (straight, multilang) inherit from this class
# and provide a wrapper to translate the test into the desired language format.

class _BaseCSSTestCase(CodeIntelTestCase):
    #XXX Watch out for '@media foo {...' scope stuff, e.g.:
    #    @media print {
    #      @import "print-main.css";
    #      BODY { font-size: 10pt }
    #    }
    #XXX Add tests for: complete-at-rule, complete-units, complete-import-url

    def test_complete_tag_names(self):
        tag_names_trigger = "css-complete-tag-names"
        self.assertTriggerMatches("a<|>bc", name=tag_names_trigger, pos=0)
        self.assertTriggerMatches("b<|>ody { }", name=tag_names_trigger, pos=0)
        # Trigger on all parts of the name
        self.assertTriggerMatches("bod<|>y { }", name=tag_names_trigger, pos=0)
        self.assertNoTrigger("/* b<|>ody")
        # Note: This triggers for UDL, with "css-complete-property-values"
        self.assertTriggerDoesNotMatch("<|>h1 ", name=tag_names_trigger)
        # Not sure about this one, fail or okay. It's a completion but nothing
        # to complete to.
        self.assertTriggerMatches("a i<|>mg")
        tag_names = [ 's', 'samp', 'script', 'select', 'small', 'span',
                     'strike', 'strong', 'style', 'sub', 'sup' ]
        tag_names.sort(CompareNPunctLast)
        self.assertCompletionsInclude("s<|>tr",
            [ ("element", v) for v in tag_names ])
        self.assertCompletionsInclude(" b<|>ody { } ",
            [("element", "body")])

        # assert no trig in string or URL
        self.assertNoTrigger('body { background: "../a i<|>mage.png"')
        self.assertTriggerDoesNotMatch('body { background: url(a i<|>mage.png)',
                                       name=tag_names_trigger)

    def test_complete_anchors(self):
        trigger_name = "css-complete-anchors"
        self.assertTriggerMatches("#<|>myid", name=trigger_name)
        self.assertTriggerMatches("#<|>", name=trigger_name)
        self.assertTriggerMatches("h1 {} #<|>", name=trigger_name)
        self.assertTriggerMatches("h1 {}\n\t#<|>", name=trigger_name)
        self.assertTriggerMatches("h1 {}\n#<|>", name=trigger_name)
        self.assertNoTrigger("/*h1 {}\n#<|>*/")
        self.assertNoTrigger("h1 {/*}\n#<|>")
        self.assertNoTrigger("/*h1 {}\n#<|>")
        # assert no trig in string or URL
        self.assertNoTrigger('body { background: "../myimage#<|>1.png"')
        self.assertTriggerDoesNotMatch('body { background: url(myimage#<|>1.png)',
                                       name=trigger_name)

    def test_complete_class_names(self):
        #        .<|>
        trigger_name = "css-complete-class-names"
        self.assertTriggerMatches(".<|>myclass", name=trigger_name)
        self.assertTriggerMatches(".<|>", name=trigger_name)
        self.assertTriggerMatches("h1 {} .<|>", name=trigger_name)
        self.assertTriggerMatches("h1 {}\n\t.<|>", name=trigger_name)
        self.assertTriggerMatches("h1 {}\n.<|>", name=trigger_name)
        self.assertNoTrigger("/*h1 {}\n.<|>*/")
        self.assertNoTrigger("h1 {/*}\n.<|>")
        self.assertNoTrigger("/*h1 {}\n.<|>")
        # assert no trig in string or URL
        self.assertNoTrigger('body { background: "../myimage.<|>png"')
        self.assertTriggerDoesNotMatch('body { background: url(myimage.<|>png)',
                                       name=trigger_name)

    def test_complete_property_names(self):
        #        selector {
        #            abc<|>...;
        #            def<|>...;
        self.assertTriggerMatches("h1 { a<|>bc",
                                  name="css-complete-property-names")
        #XXX Or should this NOT trigger here. I.e. when sub-editing an
        #    existing property name.
        self.assertTriggerMatches("h1 { c<|>olor ",
                                  name="css-complete-property-names")
        self.assertTriggerMatches("h1 { color: blue; p<|>ad ",
                                  name="css-complete-property-names", pos=18)
        # Trigger on all parts of the name
        self.assertTriggerMatches("h1 { colo<|>r: blue; pad ",
                                  name="css-complete-property-names", pos=5)
        #self.assertTriggerMatches("h1 { color: blue; pad<|> ", name="css-complete-property-names", pos=21)
        self.assertNoTrigger("/* c<|>ol")
        property_names = ( 'margin', 'margin-bottom', 'margin-left',
                          'margin-right', 'margin-top', 'marker-offset',
                          'marks', 'max-height', 'max-width', 'min-height',
                          'min-width', )
        self.assertCompletionsInclude("h1 { m<|>ax ",
            [ ("property", v + ': ') for v in property_names ])
        # assert no trig in string or URL
        self.assertNoTrigger('body { background: "../myimage.png { m<|>ax"')
        # This one is a bit much to ask for udl
        #self.assertNoTrigger('body { background: url(../myimage.png { m<|>ax)')

    def test_calltip_property_values(self):
        #        selector { abc:<|>
        import textwrap
        calltip_trigger_name = "css-calltip-property-values"
        self.assertTriggerMatches("h1 { color:<|>",
                                  name=calltip_trigger_name,
                                  form=TRG_FORM_CALLTIP)
        self.assertTriggerMatches("div.section {\r\n    display:<|>}",
                                  name=calltip_trigger_name,
                                  form=TRG_FORM_CALLTIP)
        self.assertNoTrigger("/*h1 { color:<|>")
        self.assertCalltipIs("h1 { color:<|>",
                             "\n".join(textwrap.wrap("This property describes the foreground color of an element's text content\n(CSS1, CSS2, CSS3)",
                                           40)))
        # assert no trig in string or URL
        self.assertNoTrigger('body { background: "../myimage.png:<|>"')
        self.assertTriggerDoesNotMatch('body { background: url(myimage.png:<|>)',
                                       name=calltip_trigger_name)
        self.assertTriggerDoesNotMatch('body { background: url(myimage.png:<|>)',
                                       name=calltip_trigger_name)

    def test_preceding_trg_from_pos(self):
        # Test for explicit trigger
        # test for explicit trigger on multiple spaces
        trigger_cplns_pv = "css-complete-property-values"
        trigger_calltip_pv = "css-calltip-property-values"
        self.assertPrecedingTriggerMatches("h1 { background: <$><|>no-repeat; }",
            name=trigger_cplns_pv, pos=17)
        self.assertPrecedingTriggerMatches("h1 { background:<$> <|>no-repeat; }",
            name=trigger_calltip_pv, pos=16)
        self.assertPrecedingTriggerMatches("h1 { background: n<$><|>o-repeat; }",
            name=trigger_cplns_pv, pos=17)
        self.assertPrecedingTriggerMatches("h1 { background: no<$><|>-repeat; }",
            name=trigger_cplns_pv, pos=17)
        self.assertPrecedingTriggerMatches("h1 { background: no-r<$><|>epeat; }",
            name=trigger_cplns_pv, pos=17)
        self.assertPrecedingTriggerMatches("h1 { background: no-repeat<$><|>; }",
            name=trigger_cplns_pv, pos=17)
        self.assertPrecedingTriggerMatches("h1 { border:    <$><|> ",
            name=trigger_cplns_pv, pos=16)
        self.assertPrecedingTriggerMatches("h1 { border:<$>    <|> ",
            name=trigger_calltip_pv, pos=12)
        self.assertNoPrecedingTrigger("<$>h1 { border:    <|> ")

    @tag("bug62238")
    def test_complete_property_values(self):
        #        h1 { border: <|>1px <|>solid <|>black; }  # implicit: one space
        #        h1 { border:   <|>...  # explicit: allow trig on multiple spaces
        name = "css-complete-property-values"
        self.assertTriggerMatches("h1 { color: <|>",
                                  name=name, pos=12, form=TRG_FORM_CPLN)
        self.assertTriggerMatches("h1 { color: <|>;",
                                  name=name, pos=12, form=TRG_FORM_CPLN)
        self.assertTriggerMatches("h1 { border: blue <|>", name=name)
        self.assertTriggerMatches("h1 { border: blue <|>;", name=name)
        # We implicitly trigger on multiple spaces
        self.assertTriggerMatches("h1 { color: <|>", name=name)
        self.assertTriggerMatches("h1 { color:    <|>", name=name)
        self.assertTriggerMatches("h1 { color: <|>;", name=name)
        self.assertTriggerMatches("h1 { color:    <|>;", name=name)
        #self.assertTriggerMatches("h1 { color: rgb(255, 255, 255) <|>", name=name)
        ## Don't trigger inside braces
        #self.assertNoTrigger("h1 { color: rgb(255, <|>")
        #self.assertNoTrigger("h1 { color: rgb(255, 255, <|>255) white; }")
        # Don't trigger inside comments
        self.assertNoTrigger("/*h1 { color: <|>")
        # assert no trig in string or URL
        self.assertNoTrigger('body { background: "../myimage.png: <|>"')

        # Special handling for the following content, it is handled differently
        # between straight CSS and UDL.
        css_content = dedent('body { background: url(myimage.png: <|>)')
        # This does trigger, as it does not yet know enough
        # information. It will not produce any cpln's though, test
        # it to make sure that is the case.
        self.assertTriggerMatches(css_content, name=name)
        self.assertCompletionsAre(css_content, None)

        css_content = dedent("""
            /* http://www.w3.org/TR/REC-CSS2/fonts.html#propdef-font-weight */
            h1 {
                border: 1px solid black;
                font-weight /* hi */: <|> !important
            }
        """)
        values = CSS_ATTR_DICT['font-weight']
        self.assertCompletionsAre(css_content, [("value", v) for v in values])

        # Specific bug tests
        #
        # Ensure semi-colan does not screw us up:
        #   http://bugs.activestate.com/show_bug.cgi?id=50368
        self.assertTriggerMatches("h1 { font-variable: s<|>mall-caps; }", name="css-complete-property-values")

        # Ensure already used property values do not get shown again:
        #   http://bugs.activestate.com/show_bug.cgi?id=48978
        css_content = dedent("""
            /* http://www.w3.org/TR/REC-CSS2/fonts.html#propdef-font-variant */
            h1 {
                border: 1px solid black;
                font-variant: normal <|>; /* normal shouldn't be in CC list */
            }
        """)
        values = CSS_ATTR_DICT['font-variant'][:] # copy, so we don't modify it
        values.remove('normal') # Should not be in the list
        self.assertCompletionsAre(css_content, [("value", v) for v in values])

    def test_complete_property_values_complex(self):
        # completions for complex style of propery-values
        name = "css-complete-property-values"
        content, positions = unmark_text(dedent("""\
            body {
                background: <1>transparent <2>url("../img/header_tab.gif") <3>100% <4>-600px <5>no-repeat;
                font-family: <6>"Lucida Grande", <7>Verdana, <8>sans-serif;
                float:          <9>left;
            }
        """))
        values = set(CSS_ATTR_DICT['background'])
        for i in range(1, 6):
            self.assertTriggerMatches(markup_text(content, pos=positions[i]),
                                      name=name)
            # Remove these values, as they are already in the property list
            v = values.copy()
            if i == 1:
                v.difference_update(set(['no-repeat', 'url(']))
            elif i == 2:
                v.difference_update(set(['transparent', 'no-repeat']))
            elif i == 5:
                v.difference_update(set(['transparent', 'url(']))
            else:
                v.difference_update(set(['transparent', 'url(', 'no-repeat']))
            self.assertCompletionsInclude(markup_text(content, pos=positions[i]),
                [("value", x) for x in v])

        values = set(CSS_ATTR_DICT['font-family'])
        # Remove these values, as they are already in the property list
        values = values.difference(set(['sans-serif']))
        for i in range(6, 9):
            self.assertTriggerMatches(markup_text(content, pos=positions[i]),
                                      name=name)
            self.assertCompletionsInclude(markup_text(content, pos=positions[i]),
                [("value", v) for v in values])

        values = set(CSS_ATTR_DICT['float'])
        # Remove these values, as they are already in the property list
        values = values.difference(set(['left']))
        self.assertTriggerMatches(markup_text(content, pos=positions[9]),
                                  name=name)
        self.assertCompletionsInclude(markup_text(content, pos=positions[9]),
            [("value", v) for v in values])

    def test_complete_property_values_complex2(self):
        # completions for complex style of propery-values
        name = "css-complete-property-values"
        content, positions = unmark_text(dedent("""\
            body {
                background: <1>url("../img/header <2>tab.gif") /* <3>comment: <4>"abc <5>xyz" <6>*/ <7>600px <8>no-r;
            }
        """))
        values = set(CSS_ATTR_DICT['background'])
        for i in (1, 7, 8):
            self.assertTriggerMatches(markup_text(content, pos=positions[i]),
                                      name=name)
            # Remove these values, as they are already in the property list
            v = values.copy()
            if i == 7 or i == 8:
                v.discard('url(')
            self.assertCompletionsInclude(markup_text(content, pos=positions[i]),
                [("value", x) for x in v])
        for i in range(2, 7):
            self.assertTriggerDoesNotMatch(markup_text(content, pos=positions[i]),
                                           name=name)


    @tag("bug62977")
    def test_complete_property_values_at_buf_end(self):
        values = CSS_ATTR_DICT['font-variant'][:]
        self.assertCompletionsAre("h1 { font-variant: <|>",
                                  [("value", v) for v in values])

    def test_complete_pseudo_class_names(self):
        #        a:<|>link:<|>hover;  # implicit: on ":"
        #        a: <|>...  # explicit: allow trig on multiple spaces
        trigger_name = "css-complete-pseudo-class-names"
        self.assertTriggerMatches(":<|>link", name=trigger_name)
        self.assertTriggerMatches("a:<|>link", name=trigger_name)
        self.assertTriggerMatches("a :<|>hover", name=trigger_name)
        # Can trigger inside the word
        # XXX - Scopped for now
        #self.assertTriggerMatches("a :hov<|>er", name=trigger_name)
        self.assertTriggerDoesNotMatch("h1 { color: <|>", name=trigger_name)
        pseudo_names = ["active", "visited", "link", "hover", "first-child"]
        self.assertCompletionsInclude(":<|>link", [ ("pseudo-class", s) for s in pseudo_names ])
        # No triggers if there was a space between the ":" and the identifier
        self.assertNoTrigger('body { background: "a: <|>link"')
        # assert no trig in string or URL
        self.assertNoTrigger('body { background: "a:<|>link"')
        self.assertTriggerDoesNotMatch('body { background: url(a:<|>link)',
                                       name=trigger_name)

    def test_complete_at_rule(self):
        #        @<|>import:<|>hover;  # implicit: on "@"
        #        @<|>page;
        self.assertTriggerMatches("@<|>import;", name="css-complete-at-rule", pos=1)
        self.assertTriggerMatches("@<|>media;", name="css-complete-at-rule", pos=1)
        # Can trigger inside the word
        # XXX - Scopped for now
        #self.assertTriggerMatches("@med<|>ia;", name="css-complete-at-rule", pos=1)
        # Does not occurs in block sections
        # XXX - Fails, due to lexer not highlighting this correctly
        #self.assertTriggerDoesNotMatch("h1 { @<|>import ", name="css-complete-at-rule")
        # Only occurs before rule sets
        # XXX - Fails, due to lexer not highlighting correctly
        #self.assertTriggerDoesNotMatch("h1 { color: blue }\n@<|>import ", name="css-complete-at-rule")
        # Does not allow extra whitespace
        self.assertTriggerDoesNotMatch("@ <|>import;", name="css-complete-at-rule")
        at_rule_names = [ "import", "media", "charset", "font-face", "page" ]
        self.assertCompletionsInclude("@<|>import", [ ("rule", s) for s in at_rule_names ] )
        # assert no trig in string or URL
        self.assertNoTrigger('body { background: "@<|>import"')
        #self.assertNoTrigger('body { background: url(@<|>media)')

    # PUNTing on these two for now
    #def test_complete_attr_names(self):
    #    #        textbox[<|>
    #    pass
    #def test_complete_attr_values(self):
    #    #        checkbox[checked=<|>
    #    pass

    def test_complete_tag_names_in_ws(self):
        tag_names_trigger = "css-complete-tag-names"
        body = "a <|>"
        self.assertTriggerMatches(body, name=tag_names_trigger, pos=2)
        self.assertCompletionsInclude(body,
            [("element", "body"), ("element", "li")])

    @tag("bug58637")
    def test_complete_tag_names_multiple(self):
        for content in ("b<|>ody { ... }",
                        "div b<|>ody { ... }",
                        "div, b<|>ody { ... }",
                        "div > b<|>ody { ... }"):
            self.assertCompletionsInclude(content, [("element", "body")])

    @tag("bug65994")
    def test_no_trg_after_comment(self):
        self.assertTriggerMatches(dedent("""
                body {
                    color: #036;
                    /* fill in css declarations in here to test css autocomplete */
                    b<|>
                }
            """),
            name="css-complete-property-names")

    @tag("bug65995")
    def test_trg_prop_value_after_url(self):
        content = dedent("""
            body {
                background: url("blah") <|>;
            }
        """)
        self.assertCompletionsInclude(content,
            [("value", "no-repeat")])

    @tag("bug71073")
    def test_pseudo_retrigger(self):
        content, positions = unmark_text(dedent("""
            .cursor {
                font-weight: bold;
            }
            .cursor:<1>h<2>ov
        """))
        pseudo_results = [("pseudo-class", s) for s in ("active", "visited", "link", "hover", "first-child")]
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
                                      pseudo_results)
        self.assertNoTrigger(markup_text(content, pos=positions[2]))

    @tag("css3")
    def test_css3_transition_property_completions(self):
        content = dedent("""
            body {
                transition-property: <|>;
            }
        """)
        transitions = [("value", s) for s in ("all", "IDENT", "none", "<single-transition-property>")]
        self.assertCompletionsAre(content, transitions)

class CSS_StraightTest(_BaseCSSTestCase):
    lang = "CSS"
    
    @tag("bug95929")
    def test_buffer_overrun(self):
        content, positions = unmark_text(dedent("""\
            /* 101 'a's in the next line: */
            aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
            <body> {
                background: <1>transparent <2>url('../img/header_tab.gif') <3>100% <4>-600px <5>no-repeat;
                font-family: <6>'Lucida Grande', <7>Verdana, <8>sans-serif;
                float:          <9>left;
            }
        """))
        name = "css-complete-property-values"
        self.assertTriggerMatches(markup_text(content, pos=positions[1]),
                                  name=name)
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
                                     (('value', 'repeat-x'),))



class CSS_UDL_HTMLTest(_BaseCSSTestCase):
    lang = "HTML"

    _prefix = """\
<html>
  <head>
    <style>
    """

    _suffix = """
    </style>
  </head>
  <body>
  </body>
</html>
    """

    def adjust_content(self, content):
        """A hook for subclasses to modify markedup_content before use in
        test cases. This is useful for sharing test cases between pure-
        and multi-lang uses of a given lang.
        """
        return "%s%s%s" % (self._prefix, content, self._suffix)

    def adjust_pos(self, pos):
        """A accompanying hook for `adjust_content' to adjust trigger
        pos values accordingly.
        """
        return pos + len(self._prefix)

    def test_complete_tag_names_in_ws(self):
        tag_names_trigger = "css-complete-property-values"
        body = "a <|>"
        self.assertTriggerMatches(body, name=tag_names_trigger, pos=2)
        # Unfortunately udl css scanning doesn't recognize the tag region
        #self.assertCompletionsInclude(body,
        #    [("element", "body"), ("element", "li")])


class CSS_UDL_RHTMLTest(CSS_UDL_HTMLTest):
    lang = "RHTML"

#@tag("bug69537")
class CSS_UDL_HTMLStyleAttributes(CodeIntelTestCase):
    lang = "HTML"

    _prefix = """\
<html>
  <head>
  </head>
  <body>
"""

    _suffix = """
  </body>
</html>
    """

    def adjust_content(self, content):
        """A hook for subclasses to modify markedup_content before use in
        test cases. This is useful for sharing test cases between pure-
        and multi-lang uses of a given lang.
        """
        #print "adjust_content\n%s%s%s" % (self._prefix, content, self._suffix)
        return "%s%s%s" % (self._prefix, content, self._suffix)

    def adjust_pos(self, pos):
        """A accompanying hook for `adjust_content' to adjust trigger
        pos values accordingly.
        """
        return pos + len(self._prefix)

    def test_complete_property_names(self):
        #        selector {
        #            abc<|>...;
        #            def<|>...;
        self.assertTriggerMatches('<p style="a<|>bc" />',
                                  name="css-complete-property-names")
        #XXX Or should this NOT trigger here. I.e. when sub-editing an
        #    existing property name.
        self.assertTriggerMatches('<p style="c<|>olor" />',
                                  name="css-complete-property-names")
        self.assertTriggerMatches('<p style="color: blue; p<|>ad " />',
                                  name="css-complete-property-names", pos=23)
        # Trigger on all parts of the name
        self.assertTriggerMatches('<p style="colo<|>r: blue; pad" />',
                                  name="css-complete-property-names", pos=10)
        #self.assertTriggerMatches("h1 { color: blue; pad<|> ", name="css-complete-property-names", pos=21)
        property_names = ( 'margin', 'margin-bottom', 'margin-left',
                          'margin-right', 'margin-top', 'marker-offset',
                          'marks', 'max-height', 'max-width', 'min-height',
                          'min-width', )
        self.assertCompletionsInclude('<p style="m<|>ax" />',
            [ ("property", v + ': ') for v in property_names ])
        # assert no trig in string or URL
        #self.assertNoTrigger('''<p style="background: '../myimage.png { m<|>ax'" />''')
        # This one is a bit much to ask for udl
        #self.assertNoTrigger('body { background: url(../myimage.png { m<|>ax)')

    def test_calltip_property_values(self):
        #        selector { abc:<|>
        import textwrap
        calltip_trigger_name = "css-calltip-property-values"
        self.assertTriggerMatches('<p style="color:<|>" />',
                                  name=calltip_trigger_name,
                                  form=TRG_FORM_CALLTIP)
        self.assertTriggerMatches('<p style="\r\n    display:<|>}" />',
                                  name=calltip_trigger_name,
                                  form=TRG_FORM_CALLTIP)
        self.assertNoTrigger('''<!-- <p style="color:<|>" /> -->''')
        self.assertCalltipIs('<p style="color:<|>" />',
                             "\n".join(textwrap.wrap("This property describes the foreground color of an element's text content\n(CSS1, CSS2, CSS3)",
                                           40)))
        # assert no trig in string or URL
        # XXX - Talk with Eric
        #self.assertNoTrigger('''<p style="background: '../myimage.png:<|>'" />''')
        self.assertTriggerDoesNotMatch('<p style="background: url(myimage.png:<|>)" />',
                                       name=calltip_trigger_name)
        self.assertTriggerDoesNotMatch('<p style="background: url(myimage.png:<|>)" />',
                                       name=calltip_trigger_name)

    def test_preceding_trg_from_pos(self):
        # Test for explicit trigger
        # test for explicit trigger on multiple spaces
        trigger_cplns_pv = "css-complete-property-values"
        trigger_calltip_pv = "css-calltip-property-values"
        self.assertPrecedingTriggerMatches('<p style="background: <$><|>no-repeat;" />',
            name=trigger_cplns_pv, pos=22)
        self.assertPrecedingTriggerMatches('<p style="background:<$> <|>no-repeat;" />',
            name=trigger_calltip_pv, pos=21)
        self.assertPrecedingTriggerMatches('<p style="background: n<$><|>o-repeat;" />',
            name=trigger_cplns_pv, pos=22)
        self.assertPrecedingTriggerMatches('<p style="background: no<$><|>-repeat;" />',
            name=trigger_cplns_pv, pos=22)
        self.assertPrecedingTriggerMatches('<p style="background: no-r<$><|>epeat;" />',
            name=trigger_cplns_pv, pos=22)
        self.assertPrecedingTriggerMatches('<p style="background: no-repeat<$><|>;" />',
            name=trigger_cplns_pv, pos=22)
        self.assertPrecedingTriggerMatches('<p style="border:    <$><|> " />',
            name=trigger_cplns_pv, pos=21)
        self.assertPrecedingTriggerMatches('<p style="border:<$>    <|> " />',
            name=trigger_calltip_pv, pos=17)
        self.assertNoPrecedingTrigger('<$><p style="border:    <|> " />')

    @tag("bug62238")
    def test_complete_property_values(self):
        #        h1 { border: <|>1px <|>solid <|>black; }  # implicit: one space
        #        h1 { border:   <|>...  # explicit: allow trig on multiple spaces
        name = "css-complete-property-values"
        self.assertTriggerMatches('<p style="color: <|>" />',
                                  name=name, pos=17, form=TRG_FORM_CPLN)
        self.assertTriggerMatches('<p style="color: <|>;" />',
                                  name=name, pos=17, form=TRG_FORM_CPLN)
        self.assertTriggerMatches('<p style="border: blue <|>" />', name=name)
        self.assertTriggerMatches('<p style="border: blue <|>;" />', name=name)
        # We implicitly trigger on multiple spaces
        self.assertTriggerMatches('<p style="color: <|>" />', name=name)
        self.assertTriggerMatches('<p style="color:    <|>" />', name=name)
        self.assertTriggerMatches('<p style="color: <|>;" />', name=name)
        self.assertTriggerMatches('<p style="color:    <|>;" />', name=name)
        #self.assertTriggerMatches('<p style="color: rgb(255, 255, 255) <|>", name=name)
        ## Don't trigger inside braces
        #self.assertNoTrigger('<p style="color: rgb(255, <|>")
        #self.assertNoTrigger('<p style="color: rgb(255, 255, <|>255) white; }")
        # Don't trigger inside comments
        self.assertNoTrigger('<!-- <p style="color: <|>" -->')
        # assert no trig in string or URL
        # XXX - Talk with Eric
        #self.assertNoTrigger('''<p style="background: '../myimage.png: <|>'" />''')

        # Special handling for the following content, it is handled differently
        # between straight CSS and UDL.
        css_content = dedent('<p style="background: url(myimage.png: <|>)" />')
        # This does trigger, as it does not yet know enough
        # information. It will not produce any cpln's though, test
        # it to make sure that is the case.
        self.assertTriggerMatches(css_content, name=name)
        self.assertCompletionsAre(css_content, None)

        css_content = dedent("""
            <!-- http://www.w3.org/TR/REC-CSS2/fonts.html#propdef-font-weight -->
            <p style="
                border: 1px solid black;
                font-weight /* hi */: <|> !important
            " />
        """)
        values = CSS_ATTR_DICT['font-weight']
        self.assertCompletionsAre(css_content, [("value", v) for v in values])

        # Specific bug tests
        #
        # Ensure semi-colan does not screw us up:
        #   http://bugs.activestate.com/show_bug.cgi?id=50368
        self.assertTriggerMatches('<p style="font-variable: s<|>mall-caps;" />',
                                  name="css-complete-property-values")

        # Ensure already used property values do not get shown again:
        #   http://bugs.activestate.com/show_bug.cgi?id=48978
        css_content = dedent("""
            <!-- http://www.w3.org/TR/REC-CSS2/fonts.html#propdef-font-weight -->
            <p style="
                border: 1px solid black;
                font-variant: normal <|>; /* normal shouldn't be in CC list */
            " />
        """)
        values = CSS_ATTR_DICT['font-variant'][:] # copy, so we don't modify it
        values.remove('normal') # Should not be in the list
        self.assertCompletionsAre(css_content, [("value", v) for v in values])

    def test_complete_property_values_complex(self):
        # completions for complex style of propery-values
        name = "css-complete-property-values"
        content, positions = unmark_text(dedent("""\
            <p style="
                background: <1>transparent <2>url('../img/header_tab.gif') <3>100% <4>-600px <5>no-repeat;
                font-family: <6>'Lucida Grande', <7>Verdana, <8>sans-serif;
                float:          <9>left;
            " />
        """))
        values = set(CSS_ATTR_DICT['background'])
        for i in range(1, 6):
            self.assertTriggerMatches(markup_text(content, pos=positions[i]),
                                      name=name)
            # Remove these values, as they are already in the property list
            v = values.copy()
            if i == 1:
                v.difference_update(set(['no-repeat', 'url(']))
            elif i == 2:
                v.difference_update(set(['transparent', 'no-repeat']))
            elif i == 5:
                v.difference_update(set(['transparent', 'url(']))
            else:
                v.difference_update(set(['transparent', 'url(', 'no-repeat']))
            self.assertCompletionsInclude(markup_text(content, pos=positions[i]),
                [("value", x) for x in v])

        values = set(CSS_ATTR_DICT['font-family'])
        # Remove these values, as they are already in the property list
        values = values.difference(set(['sans-serif']))
        for i in range(6, 9):
            self.assertTriggerMatches(markup_text(content, pos=positions[i]),
                                      name=name)
            self.assertCompletionsInclude(markup_text(content, pos=positions[i]),
                [("value", v) for v in values])

        values = set(CSS_ATTR_DICT['float'])
        # Remove these values, as they are already in the property list
        values = values.difference(set(['left']))
        self.assertTriggerMatches(markup_text(content, pos=positions[9]),
                                  name=name)
        self.assertCompletionsInclude(markup_text(content, pos=positions[9]),
            [("value", v) for v in values])

    def test_complete_property_values_complex2(self):
        # completions for complex style of propery-values
        name = "css-complete-property-values"
        # XXX - Talk to Eric
        #content, positions = unmark_text(dedent("""\
        #    <p style="
        #        background: <1>url('../img/header <2>tab.gif') /* <3>comment: <4>'abc <5>xyz' <6>*/ <7>600px <8>no-r;
        #    " />
        #"""))
        content, positions = unmark_text(dedent("""\
            <p style="
                background: <1> /* <3>comment: <4>'abc <5>xyz' <6>*/ <7>600px <8>no-r;
            " />
        """))
        values = set(CSS_ATTR_DICT['background'])
        for i in (1, 7, 8):
            self.assertTriggerMatches(markup_text(content, pos=positions[i]),
                                      name=name)
            # Remove these values, as they are already in the property list
            v = values.copy()
            if i == 7 or i == 8:
                v.discard('url(')
            self.assertCompletionsInclude(markup_text(content, pos=positions[i]),
                [("value", x) for x in v])
        for i in range(3, 7):
            self.assertTriggerDoesNotMatch(markup_text(content, pos=positions[i]),
                                           name=name)
            

class CSS_UDL_HTML_Selectors(CodeIntelTestCase):
    lang = "HTML"
    
    def test_completions(self):
        content, positions = unmark_text(dedent("""\
            <html>
            <head>
                <style type="text/css">
                    #header, #footer { }
                    #content { }
                    #header:hover, #footer:hover { }
                    .foo { }
                    p .bar { }
                    p > .baz[what=now] { }
                    ul, ol { }
                    li { }
                </style>
            </head>
            <body>
                <div id="<1>">
                    <p class="<2>">
                        <span style="<3>">
        """))
        self.assertTriggerMatches(markup_text(content, pos=positions[1]),
                                  name="css-complete-anchors")
        self.assertCompletionsAre(markup_text(content, pos=positions[1]),
                                  [("id", "content"),
                                   ("id", "footer"),
                                   ("id", "header")])
        self.assertTriggerMatches(markup_text(content, pos=positions[2]),
                                  name="css-complete-class-names")
        self.assertCompletionsAre(markup_text(content, pos=positions[2]),
                                  [("class", "bar"),
                                   ("class", "baz"),
                                   ("class", "foo")])
        self.assertTriggerMatches(markup_text(content, pos=positions[3]),
                                  name="html-complete-attr-enum-values")
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[3]),
                                           [("id", "header"),
                                            ("id", "footer"),
                                            ("id", "content"),
                                            ("class", "foo"),
                                            ("class", "bar"),
                                            ("class", "baz")])
        
    def test_no_completions(self):
        content, positions = unmark_text(dedent("""\
            <div id="<1>">
            <div class="<2>">
        """))
        self.assertCompletionsAre(markup_text(content, pos=positions[1]), None)
        self.assertCompletionsAre(markup_text(content, pos=positions[2]), None)



#---- mainline
if __name__ == "__main__":
    unittest.main()

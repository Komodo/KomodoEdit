#!/usr/bin/env python
# Copyright (c) 2006-2012 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Test some Sass-specific codeintel handling.

This is a big copy of the CSS test suite.
"""

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

class SassTestCase(CodeIntelTestCase):
    lang = "Sass"
    #XXX Watch out for '@media foo \n...' scope stuff, e.g.:
    #    @media print
    #      @import "print-main.css";
    #      BODY
    #        font-size: 10pt
    #XXX Add tests for: complete-at-rule, complete-units, complete-import-url

    def test_complete_tag_names(self):
        tag_names_trigger = "css-complete-tag-names"
        self.assertTriggerMatches("a<|>bc", name=tag_names_trigger, pos=0)
        self.assertTriggerMatches("b<|>ody\n\n", name=tag_names_trigger, pos=0)
        # Trigger on all parts of the name
        self.assertTriggerMatches("bod<|>y\n\n", name=tag_names_trigger, pos=0)
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
        self.assertCompletionsInclude(" b<|>ody\n\n ",
            [("element", "body")])

        # assert no trig in string or URL
        self.assertNoTrigger('body\n   background: "../a i<|>mage.png"')
        self.assertTriggerDoesNotMatch('body\n   background: url(a i<|>mage.png)',
                                       name=tag_names_trigger)

    def test_complete_anchors(self):
        trigger_name = "css-complete-anchors"
        self.assertTriggerMatches("#<|>myid", name=trigger_name)
        self.assertTriggerMatches("#<|>", name=trigger_name)
        self.assertTriggerMatches("h1\n #<|>", name=trigger_name)
        self.assertTriggerMatches("h1\n\n\t#<|>", name=trigger_name)
        self.assertTriggerMatches("h1\n\n#<|>", name=trigger_name)
        self.assertNoTrigger("/*h1\n\n#<|>*/")
        self.assertNoTrigger("h1\n   /*\n\n#<|>")
        self.assertNoTrigger("/*h1 \n\n#<|>")
        # assert no trig in string or URL
        self.assertNoTrigger('body\n   background: "../myimage#<|>1.png"')
        self.assertTriggerDoesNotMatch('body\n   background: url(myimage#<|>1.png)',
                                       name=trigger_name)

    def test_complete_class_names(self):
        #        .<|>
        trigger_name = "css-complete-class-names"
        self.assertTriggerMatches(".<|>myclass", name=trigger_name)
        self.assertTriggerMatches(".<|>", name=trigger_name)
        self.assertTriggerMatches("h1 \n .<|>", name=trigger_name)
        self.assertTriggerMatches("h1 \n\n\t.<|>", name=trigger_name)
        self.assertTriggerMatches("h1 \n\n.<|>", name=trigger_name)
        self.assertNoTrigger("/*h1 \n\n.<|>*/")
        self.assertNoTrigger("h1\n   /*\n.<|>")
        self.assertNoTrigger("/*h1 \n\n.<|>")
        # assert no trig in string or URL
        self.assertNoTrigger('body\n   background: "../myimage.<|>png"')
        self.assertTriggerDoesNotMatch('body\n   background: url(myimage.<|>png)',
                                       name=trigger_name)

    def test_complete_property_names(self):
        #        selector
        #            abc<|>...;
        #            def<|>...;
        self.assertTriggerMatches("h1\n   a<|>bc",
                                  name="sass-complete-tag-or-property-names")
        #XXX Or should this NOT trigger here. I.e. when sub-editing an
        #    existing property name.
        self.assertTriggerMatches("h1\n   c<|>olor ",
                                  name="sass-complete-tag-or-property-names")
        self.assertTriggerMatches("h1\n   color: blue\n   p<|>ad ",
                                  name="sass-complete-tag-or-property-names", pos=21)
        # Trigger on all parts of the name
        self.assertTriggerMatches("h1\n   colo<|>r: blue\n   pad ",
                                  name="sass-complete-tag-or-property-names", pos=6)
        #self.assertTriggerMatches("h1\n   color: blue; pad<|> ", name="css-complete-property-names", pos=21)
        self.assertNoTrigger("/* c<|>ol")
        property_names = ( 'margin', 'margin-bottom', 'margin-left',
                          'margin-right', 'margin-top', 'marker-offset',
                          'marks', 'max-height', 'max-width', 'min-height',
                          'min-width', )
        self.assertCompletionsInclude("h1\n   m<|>ax ",
            [ ("property", v + ': ') for v in property_names ])
        # assert no trig in string or URL
        self.assertNoTrigger('body\n   background: "../myimage.png   m<|>ax"')
        # This one is a bit much to ask for udl
        #self.assertNoTrigger('body\n   background: url(../myimage.png\n   m<|>ax)')

    def test_calltip_property_values(self):
        #        selector\n   abc:<|>
        import textwrap
        calltip_trigger_name = "css-calltip-property-values"
        self.assertTriggerMatches("h1\n  color:<|>",
                                  name=calltip_trigger_name,
                                  form=TRG_FORM_CALLTIP)
        self.assertTriggerMatches("div.section\n   \r\n    display:<|>\n",
                                  name=calltip_trigger_name,
                                  form=TRG_FORM_CALLTIP)
        self.assertNoTrigger("/*h1\n  color:<|>")
        self.assertCalltipIs("h1\n  color:<|>",
                             "\n".join(textwrap.wrap("This property describes the foreground color of an element's text content\n(CSS1, CSS2, CSS3)",
                                           40)))
        # assert no trig in string or URL
        self.assertNoTrigger('body\n  background: "../myimage.png:<|>"')
        self.assertTriggerDoesNotMatch('body\n  background: url(myimage.png:<|>)',
                                       name=calltip_trigger_name)
        self.assertTriggerDoesNotMatch('body\n  background: url(myimage.png:<|>)',
                                       name=calltip_trigger_name)

    def test_preceding_trg_from_pos(self):
        # Test for explicit trigger
        # test for explicit trigger on multiple spaces
        trigger_cplns_pv = "css-complete-property-values"
        trigger_calltip_pv = "css-calltip-property-values"
        self.assertPrecedingTriggerMatches("h1\n   background: <$><|>no-repeat; \n",
            name=trigger_cplns_pv, pos=18)
        self.assertPrecedingTriggerMatches("h1\n   background:<$> <|>no-repeat; \n",
            name=trigger_calltip_pv, pos=17)
        self.assertPrecedingTriggerMatches("h1\n   background: n<$><|>o-repeat; \n",
            name=trigger_cplns_pv, pos=18)
        self.assertPrecedingTriggerMatches("h1\n   background: no<$><|>-repeat; \n",
            name=trigger_cplns_pv, pos=18)
        self.assertPrecedingTriggerMatches("h1\n   background: no-r<$><|>epeat; \n",
            name=trigger_cplns_pv, pos=18)
        self.assertPrecedingTriggerMatches("h1\n   background: no-repeat<$><|>; \n",
            name=trigger_cplns_pv, pos=18)
        self.assertPrecedingTriggerMatches("h1\n   border:    <$><|> ",
            name=trigger_cplns_pv, pos=17)
        self.assertPrecedingTriggerMatches("h1\n   border:<$>    <|> ",
            name=trigger_calltip_pv, pos=13)
        self.assertNoPrecedingTrigger("<$>h1\n   border:    <|> ")

    @tag("bug62238")
    def test_complete_property_values(self):
        #        h1\n   border: <|>1px <|>solid <|>black;
        #        # implicit: one space
        #        h1\n   border:   <|>...  # explicit: allow trig on multiple spaces
        name = "css-complete-property-values"
        self.assertTriggerMatches("h1\n   color: <|>",
                                  name=name, pos=13, form=TRG_FORM_CPLN)
        self.assertTriggerMatches("h1\n   color: <|>;",
                                  name=name, pos=13, form=TRG_FORM_CPLN)
        self.assertTriggerMatches("h1\n   border: blue <|>", name=name)
        self.assertTriggerMatches("h1\n   border: blue <|>;", name=name)
        # We implicitly trigger on multiple spaces
        self.assertTriggerMatches("h1\n   color: <|>", name=name)
        self.assertTriggerMatches("h1\n   color:    <|>", name=name)
        self.assertTriggerMatches("h1\n   color: <|>;", name=name)
        self.assertTriggerMatches("h1\n   color:    <|>;", name=name)
        #self.assertTriggerMatches("h1\n   color: rgb(255, 255, 255) <|>", name=name)
        ## Don't trigger inside braces
        #self.assertNoTrigger("h1\n   color: rgb(255, <|>")
        #self.assertNoTrigger("h1\n   color: rgb(255, 255, <|>255) white; ")
        # Don't trigger inside comments
        self.assertNoTrigger("/*h1\n   color: <|>")
        # assert no trig in string or URL
        self.assertNoTrigger('body\n   background: "../myimage.png: <|>"')

        # Special handling for the following content, it is handled differently
        # between straight CSS and UDL.
        css_content = dedent('body\n   background: url(myimage.png: <|>)')
        # This does trigger, as it does not yet know enough
        # information. It will not produce any cpln's though, test
        # it to make sure that is the case.
        self.assertTriggerMatches(css_content, name=name)
        self.assertCompletionsAre(css_content, None)

        css_content = dedent("""
            /* http://www.w3.org/TR/REC-CSS2/fonts.html#propdef-font-weight */
            h1\n   border: 1px solid black;
                font-weight /* hi */: <|> !important
        """)
        values = CSS_ATTR_DICT['font-weight']
        self.assertCompletionsAre(css_content, [("value", v) for v in values])

        # Specific bug tests
        #
        # Ensure semi-colan does not screw us up:
        #   http://bugs.activestate.com/show_bug.cgi?id=50368
        self.assertTriggerMatches("h1\n   font-variable: s<|>mall-caps; ", name="css-complete-property-values")

        # Ensure already used property values do not get shown again:
        #   http://bugs.activestate.com/show_bug.cgi?id=48978
        css_content = dedent("""
            /* http://www.w3.org/TR/REC-CSS2/fonts.html#propdef-font-variant */
            h1\n   border: 1px solid black;
                font-variant: normal <|>; /* normal shouldn't be in CC list */
        """)
        values = CSS_ATTR_DICT['font-variant'][:] # copy, so we don't modify it
        values.remove('normal') # Should not be in the list
        self.assertCompletionsAre(css_content, [("value", v) for v in values])
        
    def test_complete_property_values_complex(self):
        # completions for complex style of propery-values
        name = "css-complete-property-values"
        content, positions = unmark_text(dedent("""\
            body
                background: <1>transparent <2>url("../img/header_tab.gif") <3>100% <4>-600px <5>no-repeat
                font-family: <6>"Lucida Grande", <7>Verdana, <8>sans-serif
                float:          <9>left
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
            body
                background: <1>url("../img/header <2>tab.gif") /* <3>comment: <4>"abc <5>xyz" <6>*/ <7>600px <8>no-r
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
        self.assertCompletionsAre("h1\n   font-variant: <|>",
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
        self.assertTriggerDoesNotMatch("h1\n   color: <|>", name=trigger_name)
        pseudo_names = ["active", "visited", "link", "hover", "first-child"]
        self.assertCompletionsInclude(":<|>link", [ ("pseudo-class", s) for s in pseudo_names ])
        # No triggers if there was a space between the ":" and the identifier
        self.assertNoTrigger('body\n   background: "a: <|>link"')
        # assert no trig in string or URL
        self.assertNoTrigger('body\n   background: "a:<|>link"')
        self.assertTriggerDoesNotMatch('body\n   background: url(a:<|>link)',
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
        #self.assertTriggerDoesNotMatch("h1\n   @<|>import ", name="css-complete-at-rule")
        # Only occurs before rule sets
        # XXX - Fails, due to lexer not highlighting correctly
        #self.assertTriggerDoesNotMatch("h1\n   color: blue \n\n@<|>import ", name="css-complete-at-rule")
        # Does not allow extra whitespace
        self.assertTriggerDoesNotMatch("@ <|>import;", name="css-complete-at-rule")
        at_rule_names = [ "import", "media", "charset", "font-face", "page" ]
        self.assertCompletionsInclude("@<|>import", [ ("rule", s) for s in at_rule_names ] )
        # assert no trig in string or URL
        self.assertNoTrigger('body\n   background: "@<|>import"')
        #self.assertNoTrigger('body\n   background: url(@<|>media)')

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
        for content in ("b<|>ody\n   ... \n",
                        "div b<|>ody\n   ... \n",
                        "div, b<|>ody\n   ... \n",
                        "div > b<|>ody\n   ... \n"):
            self.assertCompletionsInclude(content, [("element", "body")])

    @tag("bug65994")
    def test_no_trg_after_comment(self):
        self.assertTriggerMatches(dedent("""
                body
                    color: #036
                    /* fill in css declarations in here to test css autocomplete */
                    b<|>
            """),
            name="sass-complete-tag-or-property-names")

    @tag("bug65995")
    def test_trg_prop_value_after_url(self):
        content = dedent("""
            body
                background: url("blah") <|>
        """)
        self.assertCompletionsInclude(content,
            [("value", "no-repeat")])

    @tag("bug71073")
    def test_pseudo_retrigger(self):
        content, positions = unmark_text(dedent("""
            .cursor
                font-weight: bold
            .cursor:<1>h<2>ov
        """))
        pseudo_results = [("pseudo-class", s) for s in ("active", "visited", "link", "hover", "first-child")]
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
                                      pseudo_results)
        self.assertNoTrigger(markup_text(content, pos=positions[2]))

    @tag("css3")
    def test_css3_transition_property_completions(self):
        content = dedent("""
            body
                transition-property: <|>""")
        transitions = [("value", s) for s in ("all", "IDENT", "none", "<single-transition-property>")]
        self.assertCompletionsAre(content, transitions)

#---- mainline
if __name__ == "__main__":
    unittest.main()

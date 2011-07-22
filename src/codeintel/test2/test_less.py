from test_css import _BaseCSSTestCase
from codeintel2.util import dedent, CompareNPunctLast
from testlib import tag

class Less_StraightTest(_BaseCSSTestCase):
    lang = "Less"

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

    def test_complete_property_names(self):
        #        selector {
        #            abc<|>...;
        #            def<|>...;
        expected_trg_name = self.lang.lower() + "-complete-tag-or-property-names"
        self.assertTriggerMatches("h1 { a<|>bc",
                                  name=expected_trg_name)
        #XXX Or should this NOT trigger here. I.e. when sub-editing an
        #    existing property name.
        self.assertTriggerMatches("h1 { c<|>olor ",
                                  name=expected_trg_name)
        self.assertTriggerMatches("h1 { color: blue; p<|>ad ",
                                  name=expected_trg_name, pos=18)
        # Trigger on all parts of the name
        self.assertTriggerMatches("h1 { colo<|>r: blue; pad ",
                                  name=expected_trg_name, pos=5)
        #self.assertTriggerMatches("h1 { color: blue; pad<|> ", name="less-complete-property-names", pos=21)
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

    @tag("bug65994")
    def test_no_trg_after_comment(self):
        expected_trg_name = self.lang.lower() + "-complete-tag-or-property-names"
        self.assertTriggerMatches(dedent("""
                body {
                    color: #036;
                    /* fill in css declarations in here to test css autocomplete */
                    b<|>
                }
            """),
            name=expected_trg_name)


class SCSS_StraightTest(Less_StraightTest):
    lang = "SCSS"

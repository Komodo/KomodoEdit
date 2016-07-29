from test_css import _BaseCSSTestCase
from codeintel2.util import dedent, CompareNPunctLast, unmark_text, markup_text
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
    
    def test_trg_at_sign(self):
        complete_variable = self.lang.lower() + "-complete-variable"
        self.assertTriggerMatches(".foo(@<|>) { /*...*/ };",
                                  name=complete_variable)
        self.assertTriggerMatches("@foo: @<|>", name=complete_variable)
        self.assertTriggerMatches("@<|>", name="css-complete-at-rule")
        self.assertTriggerMatches(dedent("""
            .foo {
                @<|>
            }
        """), name="css-complete-at-rule")

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
        
    def test_complete_less_classes(self):
        content, positions = unmark_text(dedent("""\
            @base: #f938ab;
            
            .box-shadow(@style, @c) when (iscolor(@c)) {
              -webkit-box-shadow: @style @c;
              box-shadow:         @style @c;
            }
            .<1>box-shadow(@style, @alpha: 50%) when (isnumber(@alpha)) {
              .<2>box-shadow(@style, rgba(0, 0, 0, @alpha));
            }
            .box {
              color: saturate(@base, 5%);
              border-color: lighten(@base, 30%);
              div { .<3>box-shadow(0 0 5px, 30%) }
            }
        """))
        for i in xrange(1, 3):
            self.assertTriggerMatches(markup_text(content, pos=positions[i]),
                                      name="css-complete-class-names")
            self.assertCompletionsAre(markup_text(content, pos=positions[i]),
                                  [("class", "box"),
                                   ("class", "box-shadow")])
    
    @tag("bug1091")
    def test_no_trg_after_variable(self):
        self.assertNoTrigger("@myvar:<|>")
        
    @tag("bug1092")
    def test_complete_nested(self):
        if self.lang != 'Less': return # SCSS inherits this test case; ignore
        content, positions = unmark_text(dedent("""\
            .test {
                .testClass {
                    .<1>
                }
            }
        """))
        self.assertCompletionsAre(markup_text(content, pos=positions[1]),
                                  [("class", "test"),
                                   ("class", "testClass")])
    
    def test_cpln_variable(self):
        content, positions = unmark_text(dedent("""\
            @nice-blue: #5B83AD;
            @light-blue: @<1>nice-blue + #111;

            #header {
              @nested-color: white;
              color: @<2>light-blue;
            }
            
            #footer {
              color: @<3>
            }
            
            @<4>
        """))
        self.assertCompletionsAre(markup_text(content, pos=positions[1]),
                                  [("variable", "light-blue"),
                                   ("variable", "nice-blue")])
        self.assertCompletionsAre(markup_text(content, pos=positions[2]),
                                  [("variable", "light-blue"),
                                   ("variable", "nested-color"),
                                   ("variable", "nice-blue")])
        self.assertCompletionsAre(markup_text(content, pos=positions[3]),
                                  [("variable", "light-blue"),
                                   ("variable", "nice-blue")])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[4]),
                                  [("variable", "light-blue"),
                                   ("variable", "nice-blue")])



class SCSS_StraightTest(Less_StraightTest):
    lang = "SCSS"

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
        at_rule_names += ["extend", "at-root", "debug", "warn", "error", "if",
                          "for", "each", "while", "mixin", "include",
                          "function"] # Sass and SCSS specific rules
        self.assertCompletionsInclude("@<|>import", [ ("rule", s) for s in at_rule_names ] )
        # assert no trig in string or URL
        self.assertNoTrigger('body\n   background: "@<|>import"')
        #self.assertNoTrigger('body\n   background: url(@<|>media)')

    def test_trg_at_sign(self):
        """
        SCSS does not have @variables, so ensure all @ triggers are for
        at-rules.
        """
        self.assertTriggerMatches(".foo(@<|>) { /*...*/ };",
                                  name="css-complete-at-rule")
        self.assertTriggerMatches("@<|>", name="css-complete-at-rule")
        self.assertTriggerMatches(dedent("""
            .foo {
                @<|>
            }
        """), name="css-complete-at-rule")
    
    def test_trg_dollar_sign(self):
        complete_variable = self.lang.lower() + "-complete-variable"
        self.assertTriggerMatches("body { color: $<|> }",
                                  name=complete_variable)
        self.assertNoTrigger("$<|>")

    def test_complete_scss_classes(self):
        content, positions = unmark_text(dedent("""\
            .error {
              border: 1px #f00;
              background-color: #fdd;
            }
            .seriousError {
              @extend .<1>error;
              border-width: 3px;
            }
            .<2>
        """))
        for i in xrange(1, 2):
            self.assertTriggerMatches(markup_text(content, pos=positions[i]),
                                      name="css-complete-class-names")
            self.assertCompletionsAre(markup_text(content, pos=positions[i]),
                                      [("class", "error"),
                                       ("class", "seriousError")])
    
    def test_cpln_variable(self):
        content, positions = unmark_text(dedent("""\
            $font-stack:    Helvetica, sans-serif;
            $primary-color: #333;

            body {
              font: 100% $<1>font-stack;
              color: $<2>primary-color;
            }
            
            #main {
              $width: 5em;
              width: $<3>width;
            }
            
            #sidebar {
              width: $<4>;
            }
        """))
        for i in xrange(1, 2):
            self.assertCompletionsAre(markup_text(content, pos=positions[i]),
                                      [("variable", "font-stack"),
                                       ("variable", "primary-color")])
        self.assertCompletionsAre(markup_text(content, pos=positions[3]),
                                  [("variable", "font-stack"),
                                   ("variable", "primary-color"),
                                   ("variable", "width")])
        self.assertCompletionsAre(markup_text(content, pos=positions[4]),
                                  [("variable", "font-stack"),
                                   ("variable", "primary-color")])

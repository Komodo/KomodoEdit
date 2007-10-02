from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koJavaLanguage())

class koJavaLanguage(KoLanguageBase):
    name = "Java"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{A5907F34-F7CC-40ec-898A-551CBAA0557B}"

    accessKey = 'a'
    defaultExtension = ".java"

    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    sample = """import java.awt.*;
import java.util.*;

// This is a comment
public class Showtime extends Frame implements Runnable {
    Button quitBtn;
    Label  timeLbl;
    Thread tthread;
 
    public Showtime() {
        super(\"Java Showtime\");
        setLayout(new FlowLayout());
        quitBtn = new Button(\"Quit\");
        timeLbl = new Label((new Date()).toString());
        add(quitBtn);   add(timeLbl);
        pack();
        show();
        tthread = new Thread(this);
        tthread.run();
    }
 
    public boolean action(Event evt, Object what) {
        if (evt.target == quitBtn) {
                tthread.stop();
                System.exit(0);
        }
        return super.action(evt,what);
    }
 
    public void run() {
        while(true) {
                try { Thread.sleep(10000); } 
                catch (Exception e) { }
                timeLbl.setText((new Date()).toString());
        }
    }

    public static void main(String [] argv) {
        Showtime st = new Showtime();
    }
}
"""
    _dedenting_statements = [u'throw', u'return', u'break', u'continue']
    _indenting_statements = [u'case']
    supportsSmartIndent = "brace"

    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_C_COMMENT,
                                     sci_constants.SCE_C_COMMENTDOC,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORD,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORDERROR]
            )
        self._setupIndentCheckSoftChar()

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_CPP)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 1
        return self._lexer


    _keywords = ["abstract", "boolean", "break", "byte", "case",
                 "catch", "char", "class", "const", "continue", "default", "do",
                 "double", "else", "extends", "final", "finally", "float", "for",
                 "future", "generic", "goto", "if", "implements", "import",
                 "inner", "instanceof", "int", "interface", "long", "native",
                 "new", "null", "operator", "outer", "package", "private",
                 "protected", "public", "rest", "return", "short", "static",
                 "super", "switch", "synchronized", "this", "throw", "throws",
                 "transient", "try", "var", "void", "volatile", "while"]

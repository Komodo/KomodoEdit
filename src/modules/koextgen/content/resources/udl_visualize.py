from xpcom.server import UnwrapObject
from komodo import components, document

# Convert the current editor document to html.
koICodeIntelBuffer = components.interfaces.koICodeIntelBuffer

def callback(status, html):
    if html is None:
        return # Error calling to_html_async

    # Write the html to a file.
    fileSvc = (components.classes["@activestate.com/koFileService;1"]
                         .getService(components.interfaces.koIFileService))
    f = fileSvc.makeTempFile(".html", "w")
    f.puts(html.encode("utf-8"))
    f.close()

    # Open it in the default web browser.
    webbrowser = (components.classes['@activestate.com/koWebbrowser;1']
                            .getService(components.interfaces.koIWebbrowser))
    webbrowser.open_new(f.path)

# You can also enable the "TO_HTML_DO_TRG" and "TO_HTML_DO_EVAL" flags to see
# Code Intelligence completions and calltips.
document.ciBuf.to_html_async(callback,
                             koICodeIntelBuffer.TO_HTML_INCLUDE_STYLING |
                                koICodeIntelBuffer.TO_HTML_INCLUDE_HTML,
                             document.baseName)

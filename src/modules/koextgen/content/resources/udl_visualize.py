from xpcom.server import UnwrapObject
from komodo import components, document

# Convert the current editor document to html.
buf = UnwrapObject(document.ciBuf)
# You can also enable the "do_trg" and "do_eval" settings to see Code
# Intelligence completions and calltips.
html = buf.to_html(include_styling=True, include_html=True,
                   title=document.baseName, do_trg=False, do_eval=False)

# Write the html to a file.
fileSvc = components.classes["@activestate.com/koFileService;1"].getService(components.interfaces.koIFileService)
f = fileSvc.makeTempFile(".html", "w")
f.puts(html.encode("utf-8"))
f.close()

# Open it in the default web browser.
webbrowser = components.classes['@activestate.com/koWebbrowser;1'].getService(components.interfaces.koIWebbrowser)
webbrowser.open_new(f.path)

#!/usr/bin/env python

# XXX Change the above to point to your Python installation

"""
This Python CGI script styles source code into HTML. For more
information, see http://silvercity.sourceforge.net/

The following arguments can be passed to this script using
either GET or POST:

    source=<filename> - File is the path to the source file to
                        be styled (required)
                        
    generator=<generator> - The name of the generator used to
                            convert the file to HTML e.g.
                            python, perl (optional)

                            If this argument is not present
                            then the correct generator is
                            guessed based on the file name
                            and contents.
"""

try:
    # This module first appeared in Python 2.2, so it might
    # not be available
    import cgitb
except ImportError: pass
else:
    # Change or remove this line if you don't want the user
    # to see a Python tracebacks in their browser
    cgitb.enable()

import cgi
import sys
import source2html
import os
import urllib
import SilverCity

# XXX Change this to the URL of your script
script_url = "http://www.sweetapp.com/cgi-bin/cgi-styler.py"

stylesheet_path = "http://www.sweetapp.com/default.css"

suffix = \
"""
</span>
<p align="center">
    <a href="%(file_url)s"
        target="download"
        onclick="window.open('about:blank', 'download', 'resizeable=1,scrollbars=1')">
    <b>Download</b></a><br/>
    <small><em>The source was styled using <a href="http://silvercity.sourceforge.net/">SilverCity</a></em></small>
</p>
</body>
</html>
"""

params = cgi.FieldStorage(keep_blank_values = 1)

if not params.has_key("source"):
    import pydoc

    print "Content-type: text/plain"
    print

    doc = pydoc.HTMLDoc()

    print doc.page("Docs", doc.preformat(__doc__))
    
else:    
    source = params["source"].value
    file_name = urllib.unquote(source) 

    if params.has_key("download"):
        # The user has asked to download the source, so send it
        # as plain text
        print "Content-type: text/plain"
        print
        sys.stdout.write(open(file_name, 'r').read())    

    else:
        # The user has asked for styled source
        print "Content-type: text/html"
        print

        # Create the URL for use in downloading the source
        file_url = script_url + '?' + urllib.urlencode([('download', ''), ('source', file_name)])

        if params.has_key("generator"):
            generator = params["generator"].value
        else:
            generator = None
            
        source2html.generate_html(
            source_file_name = file_name,
            css = stylesheet_path,
            generator = generator,
            suffix = suffix % {'file_url' : file_url}
                                  )

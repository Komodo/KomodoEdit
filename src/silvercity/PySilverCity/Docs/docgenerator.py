import Pyana
import tempfile
import webbrowser
import sys
import urllib

source_uri = Pyana.URI('file:' + urllib.pathname2url(sys.argv[1]))
style_uri = Pyana.URI('file:' + urllib.pathname2url(sys.argv[2]))

if len(sys.argv) > 3:
    target_file_name = sys.argv[3]
else:    
    target_file_name = tempfile.mktemp('.html')
Pyana.transformToFile(source_uri, style_uri, target_file_name)
webbrowser.open(target_file_name)
#!/usr/bin/env python
import cgi

print 'Content-Type: text/html'
print # Blank line marking end of HTTP headers

cgiParameters = cgi.FieldStorage()

# Check to see that we have our required parameters
if not (cgiParameters.has_key("name") and cgiParameters.has_key("address")):
    print "<H1>Error</H1>"
    print "Please fill in the name and address fields."
else:
    print "<p>name:", form["name"].value
    print "<p>addr:", form["addr"].value

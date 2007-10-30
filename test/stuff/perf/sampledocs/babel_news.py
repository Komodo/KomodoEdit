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

import sys
import string
import WebService

reload(sys)
sys.setdefaultencoding("latin-1")

def scrapeHeadlines(text):
    headlines = "";
    lines = text.splitlines()
    for line in lines:
        if (string.find(line, "<a href") == 0):
            pos1 = string.find(line, "<b>")
            if pos1 > 0:
                pos2 = string.find(line, "</b>")
                if pos2 > 0:
                    headlines += line[pos1+len("<b>"):pos2] + ".\n"
    return headlines
    
print '--- Creating Headline Web Service'
news_service = WebService.ServiceProxy("http://www.soapclient.com/xml/SQLDataSoap.WSDL");
print '--- Calling Headline Web Service'
news = news_service.ProcessSRL("NEWS.SRI", "yahoo", "");
headlines = scrapeHeadlines(news)
print '--- Got headlines in English'
print headlines

print '--- Creating Translation Web Service'
babel_service = WebService.ServiceProxy("http://www.xmethods.net/sd/BabelFishService.wsdl");
print '--- Calling Translation Web Service'
translation = babel_service.BabelFish("en_fr", headlines)
print '--- Translated headlines:'
print translation
print '--- Done!'

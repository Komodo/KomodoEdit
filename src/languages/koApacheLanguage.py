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

from xpcom import components, ServerException

from koLanguageServiceBase import *

#_stateMap = {
#        'directives': ('SCE_CONF_DIRECTIVE',),
#        'parameters': ('SCE_CONF_PARAMETER',),
#        'extensions': ('SCE_CONF_EXTENSION',),
#        'default': ('SCE_CONF_DEFAULT',),
#        'numbers': ('SCE_CONF_NUMBER',),
#        'identifiers': ('SCE_CONF_IDENTIFIER',),
#        'strings': ('SCE_CONF_STRING',),
#        'comments': ('SCE_CONF_COMMENT',),
#        'ip_addresses': ('SCE_CONF_IP',),
#        }

class koApacheLanguage(KoLanguageBase):
    name = "Apache"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{4F13B454-43E9-41E7-AE72-F8EED38119B4}"
    _reg_categories_ = [("komodo-language", name)]

    defaultExtension = ".conf"
    commentDelimiterInfo = { "line": [ "#" ]  }
    searchURL = "http://httpd.apache.org/docs"

    _directives = """
    accessconfig accessfilename action addalt
    addaltbyencoding addaltbytype addcharset 
    adddefaultcharset adddescription 
    addencoding addhandler addicon addiconbyencoding 
    addiconbytype addlanguage addmodule addmoduleinfo 
    addtype agentlog alias aliasmatch 
    allow allowconnect allowoverride anonymous 
    anonymous_authoritative anonymous_logemail anonymous_mustgiveemail 
    anonymous_nouserid anonymous_verifyemail authauthoritative 
    authdbauthoritative authdbgroupfile authdbmauthoritative 
    authdbmgroupfile authdbmgroupfile authdbuserfile authdbmuserfile 
    authdigestfile authgroupfile authname authtype 
    authuserfile bindaddress browsermatch browsermatchnocase 
    bs2000account cachedefaultexpire cachedirlength cachedirlevels 
    cacheforcecompletion cachegcinterval cachelastmodifiedfactor cachemaxexpire 
    cachenegotiateddocs cacheroot cachesize checkspelling 
    clearmodulelist contentdigest cookieexpires cookielog 
    cookielog cookietracking coredumpdirectory customlog 
    defaulticon defaultlanguage defaulttype define 
    deny directory directorymatch directoryindex 
    documentroot errordocument errorlog example 
    expiresactive expiresbytype expiresdefault extendedstatus 
    fancyindexing files filesmatch forcetype
    group header headername hostnamelookups 
    identitycheck ifdefine ifmodule imapbase 
    imapdefault imapmenu include indexignore 
    indexoptions keepalive keepalivetimeout languagepriority 
    limit limitexcept limitrequestbody limitrequestfields 
    limitrequestfieldsize limitrequestline listen listenbacklog 
    loadfile loadmodule location locationmatch 
    lockfile logformat loglevel maxclients 
    maxkeepaliverequests maxrequestsperchild maxspareservers metadir 
    metafiles metasuffix mimemagicfile minspareservers 
    mmapfile namevirtualhost nocache options order 
    passenv pidfile port proxy proxyblock proxydomain 
    proxypass proxypassreverse proxyreceivebuffersize proxyremote 
    proxyrequests proxyvia qsc readmename 
    redirect redirectmatch redirectpermanent redirecttemp 
    refererignore refererlog removehandler require 
    resourceconfig rewritebase rewritecond rewriteengine 
    rewritelock rewritelog rewriteloglevel rewritemap 
    rewriteoptions rewriterule rlimitcpu rlimitmem 
    rlimitnproc satisfy scoreboardfile script 
    scriptalias scriptaliasmatch scriptinterpretersource scriptlog 
    scriptlogbuffer scriptloglength sendbuffersize 
    serveradmin serveralias servername serverpath 
    serverroot serversignature servertokens servertype 
    setenv setenvif setenvifnocase sethandler 
    singlelisten startservers threadsperchild timeout 
    transferlog typesconfig unsetenv usecanonicalname 
    user userdir virtualhost virtualdocumentroot 
    virtualdocumentrootip virtualscriptalias virtualscriptaliasip 
    xbithack from all
    pythonpostreadrequesthandler pythontranshandler pythonheaderparserhandler
    pythoninithandler pythonaccesshandler pythonauthzhandler
    pythontypehandler pythonfixuphandler pythonhandler
    pythonloghandler pythoncleanuphandler
    pythoninputfilter pythonoutputfilter
    pythonconnectionhandler
    pythonenablepdb
    pythondebug pythonimport pythoninterpperdirectory
    pythoninterpperdirective pythoninterpreter
    pythonhandlermodule pythonautoreload pythonoptimize
    pythonoption pythonpath
    
    """.split()

    _options = """
    any all on off double email dns min minimal os prod productonly full
    ascending descending name date size description
    debuglevel implicitadd noimplicitadd
    descriptionwidth fancyindexing foldersfirst iconheight iconsarelinks iconwidth namewidth scanhtmltitles suppresscolumnsorting suppressdescription suppresshtmlpreamble suppresslastmodified suppresssize trackmodified
    htmltable supressicon supressrules versionsort
    inode mtime size
    netscape cookie cookie2 rfc2109 rfc2965
    preservescontentlength debuglevel logstderr nologstderr
    always never searching finding
    block
    builtin sem
    default sdbm gdbm ndbm db
    emerg alert crit error warn notice info debug
    flock fcntl sysvsem pthread
    inherit
    nocontent referer error map
    none auth auth-int md5 md5-sess
    none formatted semiformatted unformatted
    on off full
    optional require optional_no_ca
    permanent temp seeother gone
    registry script inetd standalone
    set unset append add
    user group valid-user
    """.split()
    
    sample = """
ServerRoot "C:/Program Files/Apache Group/Apache2"

# Timeout: The number of seconds before receives and sends time out.
Timeout 300

DocumentRoot "C:/Program Files/Apache Group/Apache2/htdocs"

<Directory />
    Options FollowSymLinks
    AllowOverride None
</Directory>

LogFormat "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"" combined
"""

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_CONF)
            self._lexer.setKeywords(0, self._directives)
            self._lexer.setKeywords(1, self._options)
            self._lexer.supportsFolding = 0
        return self._lexer

    def getEncodingWarning(self, encoding):
        if not encoding.use_byte_order_marker:
            if encoding.python_encoding_name.startswith('utf-16') or encoding.python_encoding_name.startswith('ucs-'):
                return 'Including a signature (BOM) is recommended for "%s".' % encoding.friendly_encoding_name
            else:
                return ''
        else: # It's all good
            return ''


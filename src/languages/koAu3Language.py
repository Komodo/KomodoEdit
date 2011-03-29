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


class koAu3Language(KoLanguageBase):
    name = "AutoIt" # AKA "Au3"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % (name)
    _reg_clsid_ = "{0e9c0002-dc18-40eb-ab60-c3620ddc8a7a}"
    _reg_categories_ = [("komodo-language", name)]

    _stateMap = {
        'default': ('SCE_AU3_DEFAULT',
                    'SCE_AU3_SPECIAL',),
        'keywords': ('SCE_AU3_KEYWORD',),
        'functions': ('SCE_AU3_FUNCTION',),
        'comments': ('SCE_AU3_COMMENT',
                     'SCE_AU3_COMMENTBLOCK',),
        'operators': ('SCE_AU3_OPERATOR',),
        'numbers': ('SCE_AU3_NUMBER',),
        'strings': ('SCE_AU3_STRING',),
        'macros': ('SCE_AU3_MACRO',),
        'variables': ('SCE_AU3_VARIABLE',),
        'preprocessor': ('SCE_AU3_PREPROCESSOR',),
        'sent': ('SCE_AU3_SENT',),
        }
    defaultExtension = ".au3"
    commentDelimiterInfo = {}
    
    sample = """
; This is a comment.
MsgBox(0, "My second script!", "Hello from the main script!")
TestFunc()

Func TestFunc()
    MsgBox(0, "My Second Script!", "Hello from the functions!")
EndFunc
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_AU3)
            self._lexer.setKeywords(0, self.keywordclass)
            self._lexer.setKeywords(1, self.keywords2)
            self._lexer.setKeywords(2, self.keywords3)
            self._lexer.setKeywords(3, self.keywords4)
        return self._lexer

    #autoit keywords
    keywordclass="""#ce #cs #comments_end #comments_start #include #include-once
        and byref case continueloop dim do else elseif endfunc endif
        endselect exit exitloop for func global if local next not or return select step then to until wend while
        """.split()
    
    #autoit functions
    keywords2="""abs acos adlibdisable adlibenable asc asin atan autoitsetoption autoitwingettitle autoitwinsettitle
        bitand bitnot bitor bitshift bitxor blockinput break call cdtray chr clipget clipput controlclick controlcommand
        controldisable controlenable controlfocus controlgetfocus controlgetpos controlgettext controlhide controlmove
        controlsend controlsettext controlshow cos dec dircopy dircreate dirmove dirremove drivegetdrive drivegetfilesystem
        drivegetlabel drivegetserial drivegettype drivesetlabel drivespacefree drivespacetotal drivestatus envget envset
        envupdate eval exp filechangedir fileclose filecopy filecreateshortcut filedelete fileexists filefindfirstfile
        filefindnextfile filegetattrib filegetlongname filegetshortname filegetsize filegettime filegetversion fileinstall
        filemove fileopen fileopendialog fileread filereadline filerecycle filesavedialog fileselectfolder filesetattrib
        filesettime filewrite filewriteline hex hotkeyset inidelete iniread iniwrite inputbox int isadmin isarray isdeclared
        isfloat isint isnumber isstring log memgetstats mod mouseclick mouseclickdrag mousedown mousegetcursor mousegetpos
        mousemove mouseup msgbox number pixelgetcolor pixelsearch processclose processexists processwait processwaitclose
        progressoff progresson progressset random regdelete regread regwrite round run runasset runwait send seterror
        shutdown sin sleep soundplay soundsetwavevolume splashimageon splashoff splashtexton sqrt statusbargettext string
        stringaddcr stringformat stringinstr stringisalnum stringisalpha stringisascii stringisdigit stringisfloat stringisint
        stringislower stringisspace stringisupper stringisxdigit stringleft stringlen stringlower stringmid stringreplace
        stringright stringsplit stringstripcr stringstripws stringtrimleft stringtrimright stringupper tan timerstart
        timerstop tooltip traytip ubound urldownloadtofile winactivate winactive winclose winexists wingetcaretpos
        wingetclasslist wingetclientsize wingethandle wingetpos wingetstate wingettext wingettitle winkill winmenuselectitem
        winminimizeall winminimizeallundo winmove winsetontop winsetstate winsettitle winwait winwaitactive winwaitclose
        winwaitnotactive""".split()
    
    #autoit macros
    keywords3= """@appdatacommondir @appdatadir @autoitversion @commonfilesdir @compiled
        @computername @comspec @cr @crlf @desktopcommondir @desktopdir @desktopheight @desktopwidth @documentscommondir @error
        @favoritescommondir @favoritesdir @homedrive @homepath
        @homeshare @hour @ipaddress1 @ipaddress2 @ipaddress3 @ipaddress4 @lf @logondnsdomain
        @logondomain @logonserver @mday @min @mon @mydocumentsdir @osbuild @oslang @osservicepack
        @ostype @osversion @programfilesdir @programscommondir @programsdir @scriptdir @scriptfullpath @scriptname @sec
        @startmenucommondir @startmenudir @startupcommondir @startupdir @sw_hide @sw_maximize @sw_minimize @sw_restore @sw_show
        @systemdir @tab @tempdir @username @userprofiledir @wday @windowsdir @workingdir @yday @year @year""".split()
    
    #autoit Sent Keys
    keywords4="""{!} {#} {^} {{} {}} {+} {alt} {altdown} {appskey} {asc nnnn} {backspace} {browser_back} {browser_favorites}
        {browser_forward} {browser_home} {browser_refresh} {browser_search} {browser_stop} {capslock} {ctrlbreak}
        {ctrldown} {delete} {down} {end} {enter} {escape} {f1} {f10} {f11} {f12} {f2} {f3} {f4} {f5} {f6} {f7} {f8} {f9}
        {home} {insert} {lalt} {launch_app1} {launch_app2} {launch_mail} {launch_media} {lctrl} {left} {lshift} {lwin}
        {lwindown} {media_next} {media_play_pause} {media_prev} {media_stop} {numlock}
        {numpad0} {numpad1} {numpad2} {numpad3} {numpad4} {numpad5} {numpad6} {numpad7} {numpad8} {numpad9}
        {numpadadd} {numpaddiv} {numpaddot} {numpadenter} {numpadmult} {numpadsub} {pause} {pgdn} {pgup}
        {printscreen} {ralt} {rctrl} {right} {rshift} {rwin} {rwindown} {shiftdown} {sleep} {space} {tab} {up}
        {volume_down} {volume_mute} {volume_up}""".split()

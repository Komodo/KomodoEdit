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

class koEScriptLanguage(KoLanguageBase):
    name = "EScript"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{d093af1d-4a8f-4eaa-b662-42a32777e364}"
    _reg_categories_ = [("komodo-language", name)]

    _stateMap = {
        'default': ('SCE_ERLANG_DEFAULT',),
        'comments': ('SCE_ERLANG_COMMENT',),
        'variables': ('SCE_ERLANG_VARIABLE',),
        'numbers': ('SCE_ERLANG_NUMBER',),
        'keywords': ('SCE_ERLANG_KEYWORD',),
        'strings': ('SCE_ERLANG_STRING',
                    'SCE_ERLANG_CHARACTER',),
        'operators': ('SCE_ERLANG_OPERATOR',),
        'functions': ('SCE_ERLANG_FUNCTION_NAME',),
        'macros': ('SCE_ERLANG_MACRO',),
        'records': ('SCE_ERLANG_RECORD',),
        'atoms': ('SCE_ERLANG_ATOM',),
        'nodes': ('SCE_ERLANG_NODE_NAME',),
        'unknown': ('SCE_ERLANG_UNKNOWN',),
    }
    defaultExtension = '.em'
    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    
    sample = """// syntax highlite example
ocal a := { 2,4,6,8 };

Local i;
for( i := 1; i <= len(a); i := i + 1 )
print( a[i] );
endfor

foreach i in a
print( i );
endforeach
"""

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_ESCRIPT)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.setKeywords(1, self._keywords2)
            self._lexer.setKeywords(2, self._keywords3)
        return self._lexer

    _keywords="""basic basicio boats cfgfile file http npc os uo util accessible
                 addmenuitem appendconfigfileelem applyconstraint applydamage
                 applyrawdamage assignrecttoweatherregion append
                 baseskilltorawskill boatfromitem broadcast ban cdbl cint cstr
                 checklineofsight checklosat checkskill consumemana
                 consumereagents consumesubstance createaccount
                 createitematlocation createiteminbackpack createitemininventory
                 createitemincontainer createmenu createmultiatlocation
                 createnpcfromtemplate createrootiteminstoragearea
                 createstoragearea clear_script_profile_counters close damage
                 destroyitem destroymulti destroyrootiteminstoragearea detach
                 disableevents disconnectclient distance disable enableevents
                 enumerateitemsincontainer enumerateonlinecharacters
                 equipfromtemplate equipitem eraseglobalproperty
                 eraseobjproperty enable enabled erase events_waiting exists
                 findconfigelem findobjtypeincontainer findrootiteminstoragearea
                 findstoragearea fclose find fopen fread fseek ftell fwrite
                 gamestat getamount getcommandhelp getconfigint getconfigintkeys
                 getconfigmaxintkey getconfigreal getconfigstring
                 getconfigstringkeys getconfigstringarray getelemproperty
                 getequipmentbylayer getglobalproperty getharvestdifficulty
                 getmapinfo getmenuobjtypes getobjproperty getobjtype
                 getobjtypebyname getproperty getrawskill getregionstring
                 getskill getspelldifficulty getstandingheight getworldheight
                 grantprivilege harvestresource healdamage hex islegalmove
                 insert keys listequippeditems listghostsnearlocation
                 listhostiles listitemsatlocation listitemsnearlocation
                 listitemsnearlocationoftype listmobilesinlineofsight
                 listmobilesnearlocation listmobilesnearlocationex
                 listobjectsinbox loadtusscpfile left len log_profile
                 lower makeboundingbox move moveboat moveboatrelative
                 movecharactertolocation moveitemtocontainer moveitemtolocation
                 move_offline_mobiles openpaperdoll open pack performaction
                 playlightningbolteffect playmovingeffect playmovingeffectxyz
                 playobjectcenteredeffect playsoundeffect playsoundeffectprivate
                 playstationaryeffect printtextabove printtextaboveprivate
                 packages polcore position print queryparam randomdiceroll
                 randomint rawskilltobaseskill readconfigfile readgameclock
                 releaseitem registerforspeechevents registeritemwithboat
                 requestinput reserveitem restartscript resurrect
                 revokeprivilege runawayfrom runawayfromlocation runtoward
                 runtowardlocation reverse run_script_to_completion
                 saveworldstate selectmenuitem2 self sendbuywindow
                 senddialoggump sendevent sendopenspecialcontainer sendpacket
                 sendsellwindow sendskillwindow sendstringastipwindow
                 sendsysmessage sendtextentrygump setanchor setglobalproperty
                 setname setobjproperty setopponent setproperty setrawskill
                 setregionlightlevel setregionweatherlevel setscriptcontroller
                 setwarmode shutdown speakpowerwords splitwords startspelleffect
                 subtractamount systemfindboatbyserial systemfindobjectbyserial
                 say set_critical set_debug set_priority set_priority_divide
                 set_script_option setcmdlevel setdex setint setlightlevel
                 setmaster setname setpassword setstr shrink size sleep sleepms
                 sort spendgold squelch start_script syslog system_rpm target
                 targetcoordinates targetmultiplacement turnawayfrom
                 turnawayfromlocation turnboat turntoward turntowardlocation
                 toggle unloadconfigfile unpack unban unload_scripts upper
                 walkawayfrom walkawayfromlocation walktoward walktowardlocation
                 wander writehtml writehtmlraw wait_for_event
                 movechar_forcelocation moveitem_forcelocation moveitem_normal
                 scriptopt_debug scriptopt_no_interrupt scriptopt_no_runaway
                 te_cancel_disable te_cancel_enable te_style_disable
                 te_style_normal te_style_numerical tgtopt_check_los
                 tgtopt_harmful tgtopt_helpful tgtopt_neutral tgtopt_nocheck_los
                 setprop getprop""".split()
        
    _keywords2="""array const dictionary global local var and default in
                  next not or return to include use enum""".split()
    
    
    _keywords3="""while for endfor function program endprogram endfunction
                foreach case else elseif if endcase endenum endforeach
                endif endwhile""".split()

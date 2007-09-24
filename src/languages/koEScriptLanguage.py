from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koEScriptLanguage())

class koEScriptLanguage(KoLanguageBase):
    name = "EScript"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{d093af1d-4a8f-4eaa-b662-42a32777e364}"

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
        'separators': ('SCE_ERLANG_SEPARATOR',),
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

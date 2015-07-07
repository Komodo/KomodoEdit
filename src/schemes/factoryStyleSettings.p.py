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

import copy

CommonFactoryStyles = {
    'default': {
# #if PLATFORM == 'win'
        'font_default': 'Courier New',
        'font_default_fixed': 'Courier New',
        'font_default_proportional': 'Verdana',
        'size': 10,
# #else
        'font_default': 'fixed',
        'font_default_fixed': 'fixed',
        'font_default_proportional': 'lucida',
        'size': 12,
# #endif
        'eolfilled': 0,
        'bold': 0,
        'italic': 0,
        'fore': 0,
        'back': 0xffffff,
        },
    'control characters': {'fore': 0x0,
                           'back': 0xffffff},
    'indent guides': {'fore': 0xbbbbbb},
    'linenumbers': {'fore': 0x555555},
    'fold markers': {'fore': 0x555555},
    'comments': {'italic': 1,
                 'fore': 0x696969,
                },
    'preprocessor': {'fore': 0x696969,},
    'keywords': {'fore': 0x781f87},
    'keywords2': {'fore': 0x781f87},
    'operators': {'fore': 0x871f78},
    'identifiers': {'fore': 0x0},
    'strings': {'fore': 0x8e2323},
    'stringeol': {'back': 0x99ccff,
                  'eolfilled': 1},
    'numbers': {'fore': 0x8b},
    'functions': {'fore': 0x8b8b00},
    'classes': {'fore': 0x8b8b00},
    'bracehighlight': {'fore': 0x6464c8,
                       'bold': 1},
    'bracebad': {'fore': 0x6464c8,
                 'back': 0x00ffff,
                 'bold': 1},
    'variables': {'fore': 0,},
    'regex': {'fore': 0x0064c8},
    'tags': {'fore': 0xff3200,},
    'attribute name': {'fore': 0x781f87,},
    'attribute value': {'fore': 0x2f4f2f,},
    'stdin': {'fore': 0,},
    'stdout': {'fore': 0,},
    'stderr': {'fore': 0x000066,},
}

LanguageFactoryStyles = {
    'Perl': {
        'here documents': {'fore': 0x832323,
                           'bold': 1},
    },
    'XML': {
        'prolog': {'fore': 0,},
        'entity references': {'fore': 0x23238e,},
        'data': {'fore': 0x23238e,},
        'cdata tags': {'fore': 0x8b0000,},
        'cdata content': {'fore': 0x8b8b00,},
        'pi tags': {'fore': 0x8b0000,},
        'pi content': {'fore': 0x8b8b00,},
        'declarations': {'fore': 0x33405c,},
        'xpath tags': {'fore': 0xb,},
        'xpath attributes': {'fore': 0x8b0000,},
        'xpath content': {'fore': 0x8cff,},
    },
    'JavaScript': {
        'commentdockeyworderror': {'fore': 0xdd0000},
        'verbatim': {'fore': 0},
        'UUIDs': {'fore': 0},
        'verbatim': {'fore': 0},
        'globalclass': {'fore': 0x8b8b00},
        'commentdockeyword': {'fore': 0},
        'instance properties': {'fore': 0},
    },
    'HTML': {
        
    },
    'Diff': {
        'fileline': {'fore': 0x781f87,
                     'italic': 1},
        'chunkheader': {'fore': 0x8b8b00},
        'diffline': {'fore': 0x696969,
                     'italic': 1},
        'deletionline': {'fore': 0x8b},
        'additionline': {'fore': 0x8b0000},
    }
}

LanguageFactoryStyles['C++'] = copy.deepcopy(LanguageFactoryStyles['JavaScript'])
LanguageFactoryStyles['IDL'] = copy.deepcopy(LanguageFactoryStyles['JavaScript'])
LanguageFactoryStyles['C#'] = copy.deepcopy(LanguageFactoryStyles['JavaScript'])
LanguageFactoryStyles['Java'] = copy.deepcopy(LanguageFactoryStyles['JavaScript'])
LanguageFactoryStyles['JSON'] = copy.deepcopy(LanguageFactoryStyles['JavaScript'])

#<string id="style/PHP/tag/fore">activeblue</string>
#<string id="style/PHP/tagunknown/fore">activeorange</string>
#<string id="style/PHP/attribute/fore">darkpurple</string>
#<string id="style/PHP/attributeunknown/fore">activeorange</string>
#<string id="style/PHP/tagend/fore">activeblue</string>
#<string id="style/PHP/xmlstart/fore">darkcyan</string>
#<string id="style/PHP/xmlend/fore">darkcyan</string>
#<string id="style/PHP/script/fore">navyblue</string>
#<string id="style/PHP/asp/fore">activeorange</string>
#<string id="style/PHP/aspat/fore">activeorange</string>
#<string id="style/PHP/cdata/fore">activeorange</string>
#<string id="style/PHP/question/fore">activered</string>
#<string id="style/PHP/js-symbols/fore">navyblue</string>
#<string id="style/PHP/js-regex/fore">orange</string>
#<string id="style/PHP/js-asp-symbols/fore">navyblue</string>
#<string id="style/PHP/js-asp-regex/fore">orange</string>
#<string id="style/Tcl/array/fore">rosybrown</string>
#<string id="style/Tcl/literal/fore">darkgreen</string>
#<string id="style/C++/preprocessor/fore">darkcyan</string>
#<string id="style/Fortran 77/intrinsic_extended_functions/fore">#B00040</string>
#<string id="style/Fortran 77/other_functions/fore">#B04080</string>
#<string id="style/Fortran 77/preprocessor/fore">darkcyan</string>
#<string id="style/Fortran 77/.operator./fore">darkblue</string>
#<string id="style/Fortran 77/label/fore">darkred</string>
#<string id="style/Fortran 77/continuation/back">#F0E080</string>
#<string id="style/CSS/class/fore">darkcyan</string>
#<string id="style/CSS/tag/fore">darkred</string>
#<string id="style/CSS/value/fore">darkpurple</string>
#<string id="style/CSS/pseudoclass/fore">navyblue</string>
#<string id="style/CSS/important/fore">darkblue</string>
#<string id="style/CSS/id/fore">darkred</string>
#<string id="style/HTML/tag/fore">activeblue</string>
#<string id="style/HTML/tagunknown/fore">navyblue</string>
#<string id="style/HTML/attribute/fore">darkpurple</string>
#<string id="style/HTML/attributeunknown/fore">activeorange</string>
#<string id="style/HTML/tagend/fore">activeblue</string>
#<string id="style/HTML/xmlstart/fore">darkcyan</string>
#<string id="style/HTML/xmlend/fore">darkcyan</string>
#<string id="style/HTML/script/fore">navyblue</string>
#<string id="style/HTML/asp/fore">activeorange</string>
#<string id="style/HTML/aspat/fore">activeorange</string>
#<string id="style/HTML/cdata/fore">activeorange</string>
#<string id="style/HTML/question/fore">activered</string>
#<string id="style/Apache/directive/fore">darkblue</string>
#<string id="style/Apache/ip_address/fore">darkpurple</string>
#<string id="style/Apache/extensions/fore">brown</string>
#<string id="style/Apache/parameter/fore">darkcyan</string>
#<string id="style/Apache/operator/fore">darkblue</string>
#<string id="style/Makefile/target/fore">blue</string>
#<string id="style/Makefile/error/fore">activered</string>
#<string id='style/nnCrontab/task/fore'>black</string>
#<string id='style/nnCrontab/section/fore'>navyblue</string>
#<string id='style/nnCrontab/keyword/fore'>darkblue</string>
#<string id='style/nnCrontab/modifier/fore'>blue</string>
#<string id='style/nnCrontab/asterisk/fore'>orange</string>
#<string id='style/nnCrontab/environment/fore'>black</string>
#<string id="style/IDL/uuid/fore">darkred</string>
#<string id="style/LaTeX/command/fore">darkpurple</string>
#<string id="style/LaTeX/tag/fore">activeblue</string>
#<string id="style/LaTeX/math/fore">navyblue</string>
#<string id="style/Batch/label/fore">darkpurple</string>
#<string id="style/Batch/hide/fore">darkred</string>
#<string id="style/Batch/command/fore">navyblue</string>
#<string id="style/Ruby/defname/fore">darkcyan</string>
#<string id="style/Ruby/classname/fore">darkcyan</string>
#<string id="style/VisualBasic/date/fore">blue</string>

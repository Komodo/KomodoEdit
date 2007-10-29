"""
TODO:  --

- move all key assignments into keys.xul somehow -- probably put them in a data file processed by mkkeys.py
- get rid of any overlay with <key>'s in the main window at first outside of keys.xul.
* Add keycodes for the other chars [, ], etc.
- Come up with a "chord" strategy
- Come up with a serialization/deserialization/application model.
* Figure out how to make menus do the right thing.

"""
import string, os, sys

os.system('p4 edit %s' % "src/chrome/komodo/content/keybindings/keys.unprocessed.xul")
keysxml = open('src/chrome/komodo/content/keybindings/keys.unprocessed.xul', 'w')
xmlheader = """<?xml version="1.0"?>
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
<!DOCTYPE overlay PUBLIC "-//MOZILLA//DTD XUL V1.0//EN" "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul">
<overlay id="keyBindings"
   xmlns="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul">
    <keyset id="widekeyset">
    
        <!-- start manual additions -->
        <key id="&lt;" name="&lt;" key="&lt;" modifiers="shift" command=""/>
        <key id="&gt;" name="&gt;" key="&gt;" modifiers="shift" command=""/>
        <!-- end manual additions -->

"""
xmlfooter = """    </keyset>
</overlay>
"""
"""
var VKLabels = {
    'Help': 'VK_HELP',
    'Home': 'VK_HOME',
    'End': 'VK_END',
    'Space': 'VK_SPACE',
    'Backspace': 'VK_BACK',
    ']': 'VK_CLOSE_BRACKET',
    '[': 'VK_OPEN_BRACKET',
    'Cancel': 'VK_CANCEL',
    'Clear': 'VK_CLEAR',
    'Return': 'VK_RETURN',
    'Enter': 'VK_ENTER',
    'Shift': 'VK_SHIFT',
    'Control': 'VK_CONTROL',
    'Alt': 'VK_ALT',
    'Meta': 'VK_META',
    'Pause': 'VK_PAUSE',
    'Caps_Lock': 'VK_CAPS_LOCK',
    'Escape': 'VK_ESCAPE',
    'Page_Up': 'VK_PAGE_UP',
    'Page_Down': 'VK_PAGE_DOWN',
    'Left': 'VK_LEFT',
    'Right': 'VK_RIGHT',
    'Up': 'VK_UP',
    'Down': 'VK_DOWN',
    'PrintScreen': 'VK_PRINTSCREEN',
    'Insert': 'VK_INSERT',
    'Delete': 'VK_DELETE',
    '+': 'VK_ADD',
    '-': 'VK_SUBTRACT',
    'F1': 'VK_F1',
    'F2': 'VK_F2',
    'F3': 'VK_F3',
    'F4': 'VK_F4',
    'F5': 'VK_F5',
    'F6': 'VK_F6',
    'F7': 'VK_F7',
    'F8': 'VK_F8',
    'F9': 'VK_F9',
    'F10': 'VK_F10',
    'F11': 'VK_F11',
    'F12': 'VK_F12',
}
"""
special_keycodes = ('VK_ADD', 'VK_MULTIPLY', 'VK_SUBTRACT', 'VK_DIVIDE', 'VK_BACK', 'VK_CLOSE_BRACKET', "VK_SPACE")
keycodemap = [
    #("VK_WINDOWS_KEY", "Windows Key", 91), ## Undocumented and doesn't seem to work
    ("VK_CLOSE_BRACKET", "]", 0xbd),
    ("VK_OPEN_BRACKET", "[", 0xbb),
    ("VK_BACK_SLASH", "\\", 28),
    ("VK_CANCEL", "cancel", 0x03),
    ("VK_BACK", "Backspace", 0x08),
    ("VK_TAB", "Tab", 0x09),
    ('VK_ADD', "+", 0x6B),
    ('VK_SUBTRACT', "-", 0x6D),
    ('VK_MULTIPLY', "*", 0x6A),
    ('VK_DIVIDE', "/", 0x6F),
    ("VK_HELP", "Help", 0x06),
    ("VK_CLEAR", "Clear", 0x0c),
    ("VK_RETURN", "Return", 0x0d),
    ("VK_ENTER", "Enter", 0x0e),
    #("VK_SHIFT", "Shift", 0x10),         # we don't let them catch these.
    #("VK_CONTROL", "Control", 0x11),
    #("VK_ALT", "Alt", 0x12),
    ("VK_PAUSE", "Pause", 0x13),
    #("VK_CAPS_LOCK", "Caps_Lock", 0x14),
    ("VK_ESCAPE", "Escape", 0x1b),
    ("VK_SPACE", "Space", 0x20),
    ("VK_PAGE_UP", "Page_Up", 0x21),
    ("VK_PAGE_DOWN", "Page_Down", 0x22),
    ("VK_END", "End", 0x23),
    ("VK_HOME", "Home", 0x24),
    ("VK_LEFT", "Left", 0x25),
    ("VK_UP", "Up", 0x26),
    ("VK_RIGHT", "Right", 0x27),
    ("VK_DOWN", "Down", 0x28),
    ("VK_PRINTSCREEN", "PrintScreen", 0x2c),
    ("VK_INSERT", "Insert", 0x2d),
    ("VK_DELETE", "Delete", 0x2e),
]

keys = []
print >> keysxml, xmlheader

def prefix2modifiers(prefix):
    if not prefix: return prefix
    prefix = prefix[:-1]
    words = prefix.split('+')
    newwords = []
    for word in words:
        if word == 'Ctrl':
            newwords.append('Control')
        else:
            newwords.append(word)
    return ','.join(newwords).lower()

def xmlescape(name):
   name = name.replace('&', '&amp;');
   name = name.replace('"', '&quot;');
   name = name.replace('<', '&lt;');
   name = name.replace('>', '&gt;');
   return name

for name in string.digits + string.letters + r"""`~!@#$%^&*()_+-=[]{}\|:'";,./<>?""":
   id = xmlescape(name)
   keys.append((id, id, id, ''))

alt_keys = ('Alt+', 'Alt+Shift+',)
ctrl_keys = ('Ctrl+', 'Ctrl+Shift+',)
ctrl_alt_keys = ('Ctrl+Alt+', 'Ctrl+Alt+Shift+',)
meta_keys = ('Meta+', 'Meta+Shift+',)
meta_alt_keys = ('Meta+Alt+', 'Meta+Alt+Shift+',)
meta_ctrl_keys = ('Meta+Ctrl+', 'Meta+Ctrl+Shift+',)
meta_insane_keys = ('Meta+Ctrl+Alt+Shift+',)
meta_all_keys = meta_keys + meta_ctrl_keys + meta_alt_keys + meta_insane_keys
all_combos = ctrl_keys + alt_keys + ctrl_alt_keys + meta_all_keys

digitlikes = '='
shifteddigits = '~!@#$%^&*()_'

id_used = {}

for prefix in all_combos:
    for key in string.uppercase + string.digits + digitlikes:
        id = prefix+key
        if id in id_used: continue
        modifiers = prefix2modifiers(prefix)
        keys.append((id, id, key, modifiers))
        id_used[id] = 1

for key in shifteddigits:
    key = xmlescape(key)
    id = key
    if id in id_used: continue
    keys.append((id, id, key, ''))
    id_used[id] = 1

onlyalt = '`~!@#$%^&*()_={}/,.<>?'

if sys.platform.startswith('win'):
    altonlykeys = alt_keys
else:
    altonlykeys = all_combos

for key in onlyalt:
    key = xmlescape(key)
    for prefix in altonlykeys:
        id = prefix+key
        if id in id_used: continue
        modifiers = prefix2modifiers(prefix)
        keys.append((id, id, key, modifiers))
        id_used[id] = 1

unixkeys = []

# On GTK, Ctrl+Shift+3 is only elicited by the Numeric Keypad.
# If you do Ctrl+Shift+3 with the 3 that's above the E, you get
# Ctrl+Shift+# (on a US keyboard).
unixnumbermap = [('1', '!'),
                 ('2', '@'),
                 ('3', '#'),
                 ('4', '$'),
                 ('5', '%'),
                 ('6', '^'),
                 ('7', '&'),
                 ('8', '*'),
                 ('9', '('),
                 ('0', ')'),
                 ('`', '~'),
                 ('-', '_'),
                 ('=', '+')]
for number,key in unixnumbermap:
    key = xmlescape(key)
    for prefix in ('Ctrl+Shift+', 'Alt+Shift+', 'Meta+Shift+'):
        id = prefix+number
        if id in id_used: continue
        modifiers = prefix2modifiers(prefix)
        unixkeys.append((id, id, key, modifiers))
        id_used[id] = 1

darwinkeys = []

# On Darwin, when you Meta+Shift you get a keycode that is the unshifted key
darwinmap = [('?', '/'),
             ('>', '.'),
             ('<', ','),
             (':', ';'),
             ('"', "'"),
             ('{', '['),
             ('}', ']'),
             ('|', '\\'),
             ('!', '1'),
             ('@', '2'),
             ('#', '3'),
             ('$', '4'),
             ('%', '5'),
             ('^', '6'),
             ('&', '7'),
             ('*', '8'),
             ('(', '9'),
             (')', '0'),
             ('_', '-'),
             ('+', '='),
             ]
for shifted_key,key in darwinmap:
    key = xmlescape(key)
    shifted_key = xmlescape(shifted_key)
    for prefix in meta_all_keys:
        id = prefix+shifted_key
        if id in id_used: continue
        modifiers = prefix2modifiers(prefix)
        darwinkeys.append((id, id, key, modifiers))
        id_used[id] = 1

keycodes = []
for fnum in range(1,25):
    name = 'F'+str(fnum)
    keycode = 'VK_F'+str(fnum)
    for prefix in ('', 'Shift+') + all_combos:
        id = prefix+name
        if id in id_used: continue
        modifiers = prefix2modifiers(prefix)
        keycodes.append((id, id, keycode, modifiers, 0))
        id_used[id] = 1

for keycode, name, code in keycodemap:
    for prefix in ('', 'Shift+') + all_combos:
        id = prefix+name
        if id in id_used: continue
        modifiers = prefix2modifiers(prefix)
        special = keycode in special_keycodes and (prefix.find('Meta') != -1 or prefix.find('Ctrl') != -1 or prefix.find('Alt') != -1)
        keycodes.append((id, id, keycode, modifiers, special))
        id_used[id] = 1

for (id, name, key, modifiers) in keys:
    #print >> keystxt, id
    if modifiers:
       print >> keysxml, '        <key id="%(id)s" name="%(name)s" key="%(key)s" modifiers="%(modifiers)s" command=""/>' % vars()
    else:
       print >> keysxml, '        <key id="%(id)s" name="%(name)s" key="%(key)s" command=""/>' % vars()

for (id, name, keycode, modifiers, special) in keycodes:
   if special:
      print >> keysxml, '        <key id="%(id)s" name="%(name)s" keycode="%(keycode)s" event="keydown" modifiers="%(modifiers)s" command=""/>' % vars()
   else:
      print >> keysxml, '        <key id="%(id)s" name="%(name)s" keycode="%(keycode)s" modifiers="%(modifiers)s" command=""/>' % vars()

print >> keysxml, "<!-- #if PLATFORM != 'win' -->"

for (id, name, key, modifiers) in unixkeys:
    if modifiers:
       print >> keysxml, '        <key id="%(id)s" name="%(name)s" key="%(key)s" modifiers="%(modifiers)s" command=""/>' % vars()
    else:
       print >> keysxml, '        <key id="%(id)s" name="%(name)s" key="%(key)s" command=""/>' % vars()

print >> keysxml, "<!-- #endif -->"

print >> keysxml, "<!-- #if PLATFORM == 'darwin' -->"

for (id, name, key, modifiers) in darwinkeys:
    if modifiers:
       print >> keysxml, '        <key id="%(id)s" name="%(name)s" key="%(key)s" modifiers="%(modifiers)s" command=""/>' % vars()
    else:
       print >> keysxml, '        <key id="%(id)s" name="%(name)s" key="%(key)s" command=""/>' % vars()

print >> keysxml, "<!-- #endif -->"

print >> keysxml, xmlfooter

# Haven't dealt with any of the remaining keycodes:
"""

  const unsigned long DOM_VK_SEMICOLON      = 0x3B;
  const unsigned long DOM_VK_EQUALS         = 0x3D;

  const unsigned long DOM_VK_NUMPAD0        = 0x60;
  const unsigned long DOM_VK_NUMPAD1        = 0x61;
  const unsigned long DOM_VK_NUMPAD2        = 0x62;
  const unsigned long DOM_VK_NUMPAD3        = 0x63;
  const unsigned long DOM_VK_NUMPAD4        = 0x64;
  const unsigned long DOM_VK_NUMPAD5        = 0x65;
  const unsigned long DOM_VK_NUMPAD6        = 0x66;
  const unsigned long DOM_VK_NUMPAD7        = 0x67;
  const unsigned long DOM_VK_NUMPAD8        = 0x68;
  const unsigned long DOM_VK_NUMPAD9        = 0x69;
  const unsigned long DOM_VK_MULTIPLY       = 0x6A;
  const unsigned long DOM_VK_ADD            = 0x6B;
  const unsigned long DOM_VK_SEPARATOR      = 0x6C;
  const unsigned long DOM_VK_SUBTRACT       = 0x6D;
  const unsigned long DOM_VK_DECIMAL        = 0x6E;
  const unsigned long DOM_VK_DIVIDE         = 0x6F;
  const unsigned long DOM_VK_NUM_LOCK       = 0x90;
  const unsigned long DOM_VK_SCROLL_LOCK    = 0x91;
  const unsigned long DOM_VK_COMMA          = 0xBC;
  const unsigned long DOM_VK_PERIOD         = 0xBE;
  const unsigned long DOM_VK_SLASH          = 0xBF;
  const unsigned long DOM_VK_BACK_QUOTE     = 0xC0;
  const unsigned long DOM_VK_OPEN_BRACKET   = 0xDB;
  const unsigned long DOM_VK_BACK_SLASH     = 0xDC;
  const unsigned long DOM_VK_CLOSE_BRACKET  = 0xDD;
  const unsigned long DOM_VK_QUOTE          = 0xDE;
  const unsigned long DOM_VK_META           = 0xE0;

var VKCodes = {0x03: "cancel",
0x08: "Back Space",
0x09: "Tab",
0x0c: "Clear",
0x0d: "Return",
0x0e: "Enter",
0x10: "Shift",
0x11: "Control",
0x12: "Alt",
0x13: "Pause",
0x14: "Caps Lock",
0x1b: "Esc",
0x20: "Space",
0x21: "Page Up",
0x22: "Page Down",
0x23: "End",
0x24: "Home",
0x25: "Left Arrow",
0x26: "Up Arrow",
0x27: "Right Arrow",
0x28: "Down Arrow",
0x2c: "PrintScreen",
0x2d: "Insert",
0x2e: "Delete",
0x3b: ";",
0x3d: "=",
0x60: "NumPad-0",
0x61: "NumPad-1",
0x62: "NumPad-2",
0x63: "NumPad-3",
0x64: "NumPad-4",
0x65: "NumPad-5",
0x66: "NumPad-6",
0x67: "NumPad-7",
0x68: "NumPad-8",
0x69: "NumPad-9",
0x6a: "*",
0x6b: "+",
0x6c: "Separator",
0x6d: "-",
0x6e: "Decimal",
0x6f: "/",
0x70: "F1",
0x71: "F2",
0x72: "F3",
0x73: "F4",
0x74: "F5",
0x75: "F6",
0x76: "F7",
0x77: "F8",
0x78: "F9",
0x79: "F10",
0x7A: "F11",
0x7B: "F12",
0x7C: "F13",
0x7D: "F14",
0x7E: "F15",
0x7F: "F16",
0x80: "F17",
0x81: "F18",
0x82: "F19",
0x83: "F20",
0x84: "F21",
0x85: "F22",
0x86: "F23",
0x87: "F24",
0x90: "Num Lock",
0x91: "Scroll Lock",
0xbc: ",",
0xbe: ".",
0xbf: "/",
0xc0: "`",
0xdb: "[",
0xdc: "\\",
0xdd: "]",
0xde: "\"",
0xe0: "Meta"

"""


#!python
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

from xpcom import components
import os, sys, traceback, re
import glob
import string
import logging

iface = components.interfaces.koIScintillaAutoCompleteController


log = logging.getLogger("koTclCompletion")
useCharSet = "_: " + string.ascii_uppercase + string.ascii_lowercase + string.digits
tipVersionStr = "version TclTip-1.0"

class KoTclCompletion:
    _com_interfaces_ = [components.interfaces.koICompletionLanguageService,
                        components.interfaces.koIScintillaAutoCompleteListener]
    _reg_desc_       = "Tcl Calltip/AutoCompletion Service"
    _reg_clsid_      = "{1F3FD077-F98E-450a-8EA5-235F23921013}"
    _reg_contractid_ = "@activestate.com/koTclCompletionLanguageService;1"

    triggers = ''

    lComplete = []
    dComplete = {}
    dTips = {}

    def __init__(self):
        self.triggersCallTip = ' '
        self.completionSeparator = ord('\n')
        self._ok = 0
        self._scintilla = None
        self._lastlComplete = []
        self._lastcompletion = None
        if self.lComplete == []:
            self._nameRe = re.compile(r'^([\w:]+)')
            self._baseRe = re.compile(r'^(.*?) ([\?<].*)$')
            self.load_funcs();

    def load_funcs(self):
        # read Tcl function definitions
        try:
            koDirs = components.classes["@activestate.com/koDirs;1"].\
              getService(components.interfaces.koIDirs)
            # tip files can be in the 'tcl' subdirectory of the
            # support, common and user data dirs
            # XXX should probably account for modified commonDataDir and
            # XXX reprocess tip files, otherwise won't work until ko restart
            lFiles = glob.glob(os.path.join(koDirs.supportDir, "tcl", "*.tip"))
            lFiles.extend(glob.glob(os.path.join(koDirs.commonDataDir,
                                                 "tcl", "*.tip")))
            lFiles.extend(glob.glob(os.path.join(koDirs.userDataDir,
                                                 "tcl", "*.tip")))

            for file in lFiles:
                self.processTipFile(file)

            self.lComplete.sort()
            self._ok = 1
        except Exception, e:
            log.exception("Error in loading Tcl function lists");
            pass

    def processTipFile(self, filename):
        #print "Tcl processTipFile:", filename
        inputfile = open(filename,"r")

        if string.strip(inputfile.readline()) != tipVersionStr:
            log.warn("(%s) does not have correct version string", filename)
            return

        lines = inputfile.readlines()
        inputfile.close()

        for line in lines:
            line = line.strip()
            tmatch = re.search(self._nameRe, line)
            if tmatch:
                # Build up the dictionaries and list for the method
                # completion/tip mechanism.  The method completion
                # contains the command name up to the first arg that
                # starts with < (variable arg) or ? (optional arg).
                # The method tips contain the rest (if any).
                cmdName = tmatch.group(1)
                tmatch = re.search(self._baseRe, line)
                if tmatch:
                    # There are args for method tips, so build up the
                    # dictionary for that.
                    cmdBase = tmatch.group(1)
                    cmdArgs = tmatch.group(2)
                    if (self.dTips.has_key(cmdBase)):
                        self.dTips[cmdBase].append(cmdArgs)
                    else:
                        self.dTips[cmdBase] = [cmdArgs]
                else:
                    cmdBase = line
                if (self.dComplete.has_key(cmdName)):
                    self.dComplete[cmdName].append(cmdBase)
                else:
                    self.dComplete[cmdName] = [cmdBase]
                    self.lComplete.append(cmdName)

    # get the available completions
    def getmethods(self, text):
        items = []
        doTip = 0
        space = text.find(' ')
        if space == -1:
            name = text
        else:
            # We are trying to complete methods of a multi-word command
            name = text[:space]

        if self._lastcompletion is not None and \
            self._lastcompletion == text[:len(self._lastcompletion)]:
            # We have done a completion based on the same name
            items = [key for key in self._lastlComplete \
                     if key.startswith(text)]

            #if same list, skip doing it.
            if self._scintilla.autoCActive() and \
               (len(items) == len(self._lastlComplete)): 
                #print "Tcl keeping current autocomplete"
                return None, 0, doTip

        # Either we didn't already have something, or it is no longer
        # valid with the new input
        if not items:
            if space == -1:
                # In the single-word case, just look in the list of
                # primary commands
                items = [key for key in self.lComplete if key.startswith(name)]
            elif self.dComplete.has_key(name):
                # In the multi-word case, look in the dictionary of
                # commands with methods
                items = [key for key in self.dComplete[name] \
                         if key.startswith(text)]

        # If we only found one item in the single-word case, then go
        # straight to the dictionary with submethods included
        if space == -1 and len(items) == 1:
            items = [key for key in self.dComplete[items[0]] \
                     if key.startswith(text)]

        # If we found nothing, then perhaps we are at a point where
        # only variable and optional args remain, and thus a method
        # tip is called for.
        if not items:
            name = string.rstrip(text)
            if self.dTips.has_key(name):
                items = self.dTips[name]
                doTip = 1

        self._lastcompletion = text
        self._lastlComplete = items
        return items, 1, doTip

    def AutoComplete(self, ch, scimoz, controller):
        if not self._ok: return
        # Don't assume that StartCallTip gets all the necessary events,
        # but we combine method completion and calltips together.
        self.StartCallTip(ch, scimoz, controller)

    def StartCallTip(self, ch, scimoz, controller):
        if not self._ok: return

        # In Tcl CallTips and AutoComplete are the same.
        # We pop up AutoComplete whenever we have something
        # in our dict that matches the current command input.
        # Otherwise we use the CallTips.
        s = self._scintilla = scimoz
        c = self._controller = controller;

        # Only do this if we have no selection
        if s.selectionStart == s.selectionEnd and s.selectionStart > 0:
            curPos = s.positionBefore(s.currentPos)
            style  = s.getStyleAt(curPos) & 127
            #print "Tcl StartCallTip"
            if style == s.SCE_TCL_COMMENT:
                # Don't do anything in comments
                return

            if s.callTipActive():
                # Just leave the call tip up for the user.  It goes
                # away when they hit <Escape> or backspace over the
                # cursor point where the method tip started.
                return
            else:
                char = s.getWCharAt(curPos)
                if style in (s.SCE_TCL_WORD, s.SCE_TCL_IDENTIFIER,
                             s.SCE_TCL_DEFAULT) and \
                    char in useCharSet:
                    self._DoTipComplete()
                    return

        if s.autoCActive():
            s.autoCCancel()
        if c.active:
            c.close()

    # koIScintillaAutoCompleteListener
    def onAutoCompleteEvent(self, controller, event):
        if event.type == "command":
            controller.applyCompletion(self._lastTriggerPos, -1, None)
        elif event.type == "focus":
            # Ugly hack: scimoz needs to keep accepting key presses while the
            # autocomplete popup is actually focused.  This needs to be done in
            # the 'focus' event (instead of, say, 'popupshown') because that is
            # the first event that occurs; otherwise we can end up losing keys.
            self._scintilla.isFocused = True
        elif event.type in ("keydown", "keypress"):
            import json
            
            koInterfaceProxy = components.classes["@activestate.com/koInterfaceProxy;1"]\
                        .getService(components.interfaces.koIInterfaceProxy)
            eventInfo = koInterfaceProxy.unpackKeyEvent(event)
            eventInfo = json.loads(eventInfo)
            
            completionCodes = [eventInfo["DOM_VK_RETURN"],
                               eventInfo["DOM_VK_TAB"]]
            thread = components.classes["@mozilla.org/thread-manager;1"]\
                               .getService()\
                               .currentThread
            if eventInfo["keyCode"] in completionCodes:
                if event.type == "keydown":
                    selectedText = controller.selectedText
                    log.debug("will accept completion " + controller.selectedText)
                    # Bug 94416:
                    # Find where selectedText starts before aStartPos
                    # and remove the existing leading characters.
                    scimoz = self._scintilla
                    if self._lastTriggerPos == scimoz.currentPos:
                        aStartPos = self._lastTriggerPos
                        earlierPos = aStartPos - len(selectedText)
                        if earlierPos < 0:
                            earlierPos = 0
                        aText = scimoz.getTextRange(earlierPos, aStartPos)
                        for i in range(len(aText)):
                            if selectedText.startswith(aText[i:]):
                                if i == 0:
                                    # Have to do this because
                                    # selectedText[-1:] gives the last letter,
                                    # but selectedText[-0:] gives the whole string
                                    selectedText = ""
                                else:
                                    selectedText = selectedText[-i:]
                                break
                    thread.dispatch(lambda: controller.applyCompletion(self._lastTriggerPos,
                                                                       scimoz.currentPos,
                                                                       selectedText),
                                    components.interfaces.nsIEventTarget.DISPATCH_NORMAL)
                event.stopPropagation()
                event.preventDefault()

    def _DoTipComplete(self):
        s = self._scintilla
        c = self._controller
        #s.autoCCancelAtStart = 0
        text = self._GetCmd()
        #print "Tcl _DoTipComplete text '" + text + "'"
        if len(text) < 3:
            if c.active: c.close()
            return

        cmds, cancel, doTip = self.getmethods(text)
        #print "Tcl getmethods:", cmds, cancel, doTip
        log.debug ("Tcl getmethods: %r", [cmds, cancel, doTip])
        if cmds:
            if doTip:
                if c.active:
                    c.close()
                cmds = chr(self.completionSeparator).join(cmds)
                self._scintilla.callTipShow(s.currentPos, cmds)
                #XXX Better to not highlight any of it than to highlight
                #    all of it.
                #self._scintilla.callTipSetHlt(0, len(cmds))
            else:
                c.listener = self
                c.reset()
                c.addColumn(iface.COLUMN_TYPE_IMAGE,
                            ["chrome://komodo/skin/images/cb_function.png" for x in cmds],
                            False)
                c.addColumn(iface.COLUMN_TYPE_TEXT, cmds, True)
                startPos = self._lastTriggerPos
                c.show(startPos, s.currentPos, startPos, text)
        elif cancel:
            if s.autoCActive():
                s.autoCCancel()
            if c.active:
                c.close()

    def _GetCmd(self):
        s = self._scintilla
        currentPos = s.selectionStart
        last = s.charPosAtPosition(currentPos)
        index = s.charPosAtPosition(s.positionBefore(currentPos))
        # Copy over the text, as otherwise it is an expensive
        # XPCOM reference per char fetch
        buffer = s.text
        # Walk backwards accepting everything in the "acceptable"
        # command char set
        while index >= 0 and buffer[index] in useCharSet:
            index -= 1
        # Readjust index to last "good" char
        index += 1
        # check preceeding character, don't do calltip on variables
        if index > 0 and buffer[index-1] == '$':
            return ""
        # Strip off just the preceding : chars
        while index < last and buffer[index] in ": ":
            index += 1
        # Remember where the text started
        word = buffer[index:last]
        self._lastTriggerPos = currentPos - len(word.decode("utf8"))
        # Return the slice of the buffer that represents that last "word"
        return word

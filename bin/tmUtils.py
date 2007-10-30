#!/usr/bin/env python

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

# Some general Python utilities for Trent

import sys, os


#---- globals

verbosity = 1
out = sys.stdout   # can be overridden



#---- the utilities

def AskYesNo(prompt="?", default=1):
    """Ask a yes no question on the command line and return the response.
    Returns true (1) if answer is yes, false (0) if answer is no.
    """
    import string
    validChoices = {'yes':1, 'y':1, 'ye':1, 'no':0, 'n':0}
    if default == None:
        postPrompt = ' [y/n] '
    elif default == 1:
        postPrompt = ' [Y/n] '
    else:
        postPrompt = ' [y/N] '
    while 1:
        out.write(prompt + postPrompt)
        choice = string.lower(raw_input())
        out.write("\n")
        if default is not None and choice == '':
            return default
        elif choice in validChoices.keys():
            return validChoices[choice]
        else:
            out.write("Please repond with 'yes' or 'no' (or 'y' or 'n').\n")


def AskYesNoQuit(prompt="?", default=1):
    """Ask a yes/no/quit question on the command line and return the response.
    Return values are: yes: 1,  no: 0,  quit: -1.
    """
    import string
    validChoices = {'yes':1, 'y':1, 'ye':1, 'no':0, 'n':0, 'quit':-1, 'q':-1}
    if default == None:
        postPrompt = ' [y/n/q] '
    elif default > 0:
        postPrompt = ' [Y/n/q] '
    elif default == 0:
        postPrompt = ' [Y/N/q] '
    elif default < 0:
        postPrompt = ' [y/n/Q] '
    while 1:
        out.write(prompt + postPrompt)
        choice = string.lower(raw_input())
        out.write("\n")
        if default is not None and choice == '':
            return default
        elif choice in validChoices.keys():
            return validChoices[choice]
        else:
            out.write("Please repond with 'yes', 'no' or 'quit' "\
                "(or 'y', 'n' or 'q').\n")


def AskQuestion(prompt="?", default="", isValidCallback=None):
    """Ask a question on the command line. Potential default."""
    import string
    if default:
        postPrompt = ' [%s] ' % default
    else:
        postPrompt = ' '
    while 1:
        out.write(prompt + postPrompt)
        choice = raw_input()
        if choice == "":
            choice = default
        if isValidCallback is not None:
            if isValidCallback(choice):
                return choice
            else:
                pass   # i.e. try again
        else:
            return choice


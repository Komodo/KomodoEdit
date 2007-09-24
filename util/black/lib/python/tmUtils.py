#!/usr/bin/env python

# Some general Python utilities for Trent

import sys, os


#---- globals

verbosity = 0           # <0==quiet, 0==normal, >0==versbose
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


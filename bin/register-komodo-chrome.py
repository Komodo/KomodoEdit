#!/usr/bin/env python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.
#
# Register the given Komodo chrome element, if necessary.
#
# This uses chrome's installed-chrome.txt to register the given Komodo
# chrome element in the current Mozilla build.
# 
# email on mozilla-xpinstall:
# 
# Trent Mick wrote:
# > 
# > (Not sure if I this or mozilla-xpfe is the proper forum.)
# > 
# > How do I register third party chrome? This includes packages, overlays,
# > skins, and locales. I have a chrome directory structure (say a package named
# > 'foo') plopped into the chrome directory appropriately and now I want to
# > launch:
# >   > mozilla -chrome chrome://foo/content
# > 
# > Do I *have* to create a .xpi and let install.js do the registration? I am
# > currently more interested in a quick development cycle right now and
# > therefore would rather not have to go through the .xpi procedure. Ideally I
# > would like to copy in my package/skin/locale/overlay directory in chrome, do
# > one other step (call a registration program, write a line to
# > installed-chrome.txt or something), invoke mozilla as above, and then just
# > have my package come up. Is there such a step?
# 
# In a development situation you don't have to use XPInstall. Assuming the
# chrome has somehow been placed in the directory bin/chrome/packages/foo then
# simply add the following line to installed-chrome.txt:
# 
#  content,install,url,resource:/chrome/packages/foo/
# 
# Note the trailing slash, it is required. Repeat if you are registering other
# types, with additional lines that are identical except for replacing
# "content" with "skin" and/or "locale"
# 
# If you are placing a foo.jar chrome archive instead then use
# 
#   content,install,url,jar:resource:/chrom/packages/foo.jar!/
# 
# the only difference being the jar: prefix on the URL and the '!' before the
# final slash (and repeat for each chrome type if required).
# 
# > Fringe questions:
# > - *Is* the mozilla chrome registry just the all-{packages|skins|...}.rdf
# >   files or are there other registry files about somewhere?
# 
# That's it, yes. Also user-<type>.rdf for selected skins and locales, and
# additional information in the overlays subdirectory describing any dynamic
# overlays. Also if the user has installed any local chrome in their profile
# you will find all-<type>.rdf files in your profile directory, and if the
# profile has ever switched skins or locales there will be user-<type>.rdf
# files in the profile directory.
# 
# > - Is there any official documentation for XPI yet?
# 
# No, our doc writer contractor went missing (family emergency overseas).
# 
# > - Does the installed-chrome.txt mechanism work anymore (the last reference I
# >   have seen to that was in May)?
# 
# Yes, XPInstall uses it in certain situations, in fact.
# 
# -Dan Veditz

import re, sys, os
import logging


#---- globals

log = logging.getLogger("regchrome")
log.setLevel(logging.DEBUG)



#---- support functions

def Mkdir(newdir):
    """mymkdir: works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise "Mkdir(): A file with the same name as the desired "\
            "dir, '%s', already exists." % newdir
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            Mkdir(head)
        if tail:
            os.mkdir(newdir)


def GetChromeType(urn):
    """return one of 'package', 'skin', 'locale' based on the given chrome urn"""
    if urn.startswith('urn:mozilla:package'):
        return 'package'
    elif urn.startswith('urn:mozilla:skin'):
        return 'skin'
    elif urn.startswith('urn:mozilla:locale'):
        return 'locale'
    else:
        raise "*** I don't know what chrome type the urn %s refers to." % repr(urn)


def GetResourceUrl(chromeUnitRootDirName, jarring):
    """e.g. 'komodo\\content', 0 -> 'resource:/chrome/komodo/content/'
            'jaguar/content', 1 -> 'jar:resource:/chrome/jaguar.jar!/content/'
    """
    chromeUnitRootDirName = chromeUnitRootDirName.replace('\\', '/')
    first, rest = chromeUnitRootDirName.split('/', 1)
    if not jarring:
        resourceUrl = 'resource:/chrome/%s/' % chromeUnitRootDirName
    else:
        resourceUrl = 'jar:resource:/chrome/%s.jar!/%s/' % (first, rest)
    return resourceUrl


def GetRegistrationLine(chromeType, chromeUnitRootDirName, jarring):
    """Return the line needed in installed-chrome.txt in the Mozilla chrome
    dir to have Mozilla register the given chrome unit"""
    if chromeType == 'package':
        regTypeName = 'content'
    else:
        regTypeName = chromeType
    regLine = '%s,install,url,%s\n' %\
        (regTypeName, GetResourceUrl(chromeUnitRootDirName, jarring))
    return regLine
    

def Register(chromeUnitUrn, chromeUnitRootDirName, chromeDirName, jarring):
    """Add a line to installed-chrome.txt in the chrome directory.
    Do not add the line if it already exists. Also, replace a line for the
    same chrome unit if the jarring status has changed.
    """
    log.debug("Register(chromeUnitUrn=%(chromeUnitUrn)r, "
              "chromeUnitRootDirName=%(chromeUnitRootDirName)r, "
              "chromeDirName=%(chromeDirName)r, jarring=%(jarring)r)"
              % locals())

    installedChromeTxt = os.path.join(chromeDirName, 'installed-chrome.txt')
    # determine the required registration line (and the one that may have to
    # be removed)
    chromeType = GetChromeType(chromeUnitUrn)
    if jarring:
        regLine = GetRegistrationLine(chromeType, chromeUnitRootDirName, 1)
        otherRegLine = GetRegistrationLine(chromeType, chromeUnitRootDirName, 0)
    else:
        regLine = GetRegistrationLine(chromeType, chromeUnitRootDirName, 0)
        otherRegLine = GetRegistrationLine(chromeType, chromeUnitRootDirName, 1)
    # ensure that line has a \n
    if not regLine.endswith('\n'): regLine = regLine + '\n'
    if not otherRegLine.endswith('\n'): otherRegLine = otherRegLine + '\n'
    log.debug("line to register: %r", regLine)
    log.debug("line to (possibly) remove: %r", otherRegLine)

    # check if this chrome element is registered already (whether are a JAR
    # or not)
    newLines = []
    actions = ["register"]
    if os.path.isfile(installedChromeTxt):
        fin = open(installedChromeTxt, 'r')
        lines = fin.readlines()
        fin.close()
        for line in lines:
            if line == regLine:
                # already registered
                log.info("%r already registered, skipping", regLine)
                actions.remove("register")
            elif line == otherRegLine:   # want to remove this line
                log.info("dropping unwanted line: %r, need to clean out "
                         "registry", otherRegLine)
                actions.append("clean")
            else:
                newLines.append(line)
    if "clean" in actions:
        chromeRdf = os.path.join(os.path.dirname(installedChromeTxt),
                                 "chrome.rdf")
        if os.path.exists(chromeRdf):
            os.remove(chromeRdf)
    if "register" in actions:
        # add the new line
        log.info("appending %r to '%s'", regLine, installedChromeTxt)
        newLines.append(regLine)

        # If the file does not exist then it should be created (NOTE:
        # that in weird circumstances, like when an install-image is
        # being built, the chrome *directory* might have to be created
        # as well)
        print "registering '%s' chrome unit" % chromeUnitUrn
        if not os.path.isdir(os.path.dirname(installedChromeTxt)):
            Mkdir(os.path.dirname(installedChromeTxt))
        fout = open(installedChromeTxt, 'w')
        fout.write("".join(newLines))
        fout.close()


#---- script mainline 

if __name__ == '__main__':
    # Setup logging.
    logging.basicConfig()

    chromeUnitUrn = None            # e.g. urn:mozilla:package:komodo
    chromeUnitRootDirName = None    # chrome path to root of chrome 
                                    # unit (i.e. to contents.rdf file)
    chromeDirName = None            # root of installed Mozilla chrome dir
    # E.g.,
    #   chromeUnitUrn='urn:mozilla:package:jaguar'
    #   chromeUnitRootDirName='jaguar\\content'
    #   chromeDirName='D:\\trentm\\as\\Apps\\Mozilla-devel\\build\\moz-20030429-ko26-release-perf-tools\\mozilla\\dist\\bin\\chrome'
    #   jarring=1
    chromeUnitUrn, chromeUnitRootDirName, chromeDirName, jarring = sys.argv[1:]
    jarring = int(jarring)   # if left as a string "0" == true, don't want that

    Register(chromeUnitUrn, chromeUnitRootDirName, chromeDirName, jarring)
    if jarring:
        # The jar file has to be created/updated before calling
        # 'regchrome' otherwise regchrome will silently NOT register the
        # element.
        log.debug("creating/updating jar for %s", chromeUnitUrn)
        oldDir = os.getcwd()
        try:
            first, rest = chromeUnitRootDirName.split(os.sep, 1)
            cwd = os.path.join(chromeDirName, first)
            log.debug("cd '%s'", cwd)
            os.chdir(cwd)

            cmd = "zip -r -q %s *" % os.path.join(os.pardir, first+".jar")
            log.info("running '%s' in '%s'", cmd, cwd) 
            retval = os.system(cmd)
            if retval:
                log.error("error running '%s'", cmd)
                sys.exit(retval)
        finally:
            os.chdir(oldDir)
    log.info("running 'regchrome'")
    os.system('regchrome')

    # presumably a raised exception will signal any error
    sys.exit(0)



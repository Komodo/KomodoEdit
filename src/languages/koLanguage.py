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

# -*- python -*-
import sys
import os
from os.path import join, splitext
import glob
import fnmatch
import re
import logging
import operator
from pprint import pprint, pformat

from xpcom import components, nsError, ServerException, COMException, _xpcom
from xpcom.components import classes as Cc, interfaces as Ci
import xpcom.server
from xpcom.server import WrapObject, UnwrapObject
from koTreeView import TreeView
import which

import koXMLTreeService

from zope.cachedescriptors.property import LazyClassAttribute

log = logging.getLogger('koLanguage')
#log.setLevel(logging.DEBUG)

class KoLanguageItem:
    _com_interfaces_ = [components.interfaces.koIHierarchyItem]
    _reg_contractid_ = "@activestate.com/koLanguageItem;1"
    _reg_clsid_ = "{33532bc1-302a-4b2d-ad14-13c5eadf4d93}"
    
    def __init__(self, language, key):
        self.language = language
        self.name = language
        self.key = key
        
    def get_available_types(self):
        return components.interfaces.koIHierarchyItem.ITEM_STRING

    def get_item_string(self):
        return self.language

    def get_container(self):
        return 0

class KoLanguageContainer:
    _com_interfaces_ = [components.interfaces.koIHierarchyItem]
    _reg_contractid_ = "@activestate.com/koLanguageContainer;1"
    _reg_clsid_ = "{878ed885-6274-4c07-9668-a9a01a0ae09c}"
    
    def __init__(self, label, languages):
        self.name = label
        self.languages = languages
    
    def getChildren(self):
        return self.languages

    def get_available_types(self):
        return 0
        return components.interfaces.koIHierarchyItem.ITEM_STRING

    def get_item_string(self):
        return 0
        return self.label

    def get_container(self):
        return 1


# The LanguageRegistryService keeps track of which languages/services
# are available.  It is used by packages of services to inform the
# system of their presence, and is used internally by the other
# language services classes to get information on the services
# available.
class KoLanguageRegistryService:
    _com_interfaces_ = [components.interfaces.koILanguageRegistryService,
                        components.interfaces.nsIObserver]
    _reg_contractid_ = "@activestate.com/koLanguageRegistryService;1"
    _reg_clsid_ = "{4E76795E-CC92-47c6-8801-C9ACFC1B02E3}"

    # 'Primary' languages are those that the Komodo UI "cares" more about.
    # Mainly it means that they show up at the top-level in the "View As
    # Language" menulists.
    _primaryLanguageNames = {}    # use dict for lookup speed
    
    # 'Internal' languages are those that the user shouldn't see as a language
    # name choice directly. E.g. "Rx", "Regex".
    _internalLanguageNames = {}   # use dict for lookup speed

    _defaultLanguageExtensions = {}
    _defaultFileAssociations = {}

    _namespaceMap = {}
    _publicIdMap = {}
    _systemIdMap = {}
    
    # Language-specific patterns that will identify the language based on
    # a match against the head of the document.
    #
    # Note that some shebang "line" matches require more than the first
    # line so pattern should be prepared to deal with that.
    # XXX this belongs in language services
    shebangPatterns = []
    
    # Mapping of local variable mode names (typically Emacs mode name)
    # to the appropriate language name in this registry.
    # - All we need to note here are exceptions in the naming scheme,
    #   like "mode: C" which corresponds to Komodo's C++ language.
    _modeName2LanguageName = {}

    # Cached services - saved on the class.
    _globalPrefSvc = None
    _globalPrefs = None

    # Lazily loaded class variables.
    @LazyClassAttribute
    def _globalPrefSvc(self):
        return components.classes["@activestate.com/koPrefService;1"].\
                    getService(components.interfaces.koIPrefService)
    @LazyClassAttribute
    def _globalPrefs(self):
        return self._globalPrefSvc.prefs
    
    def __init__(self):
        self.__initPrefs()
        self._globalPrefSvc = components.classes["@activestate.com/koPrefService;1"].\
                            getService(components.interfaces.koIPrefService)
        self._globalPrefs = self._globalPrefSvc.prefs

        self.__languageFromLanguageName = {} # e.g. "Python": <koILanguage 'Python'>
        
        # Accesskey (the Alt+<letter/number> keyboard shortcut to select a menu
        # item on Windows and Linux) for this language in menulists of language
        # names. Not every language has (or should have) one.
        self.__accessKeyFromLanguageName = {}
        
        # File association data. This data comes from a few places:
        # - the 'factoryFileAssociations' preference (the factory set
        #   of file associations)
        # - the 'fileAssociationDiffs' preference (site/user changes to the
        #   factory set)
        # - the 'defaultExtension' attribute of all registered languages
        #   (src/languages/ko*Language.py and any installed UDL-based
        #   language extensions) unless the given pattern is already used
        self.__languageNameFromPattern = {} # e.g. "*.py": "Python"
        # Used for creating user assocs diff.
        self.__factoryLanguageNameFromPattern = {}
        self.__patternsFromLanguageName = None  # e.g. "Python": ["*.py", "*.pyw"]
        # E.g. ".py": "Python", "Makefile": "Makefile", "Conscript": "Perl";
        # for faster lookup.
        self.__languageNameFromExtOrBasename = None
        # Other file associations that don't fit the ExtOrBasename style.
        self.__languageNameFromOther = None

        # XXX get from prefs?
        self.defaultLanguage = "Text"

        # This is here because the addon manager is asynchronous which really
        # cramps us later when we try to synchronously check to see
        # if a particular extension is available.
        self._preloadAddonEnabledStatus()

        self.registerLanguages()
        self._resetFileAssociationData() # must be after .registerLanguages()

    def observe(self, aSubject, aTopic, someData):
        if aTopic == "fileAssociationDiffs":
            self.__languageNameFromPattern = None
            self.__languageNameFromExtOrBasename = None
            self.__languageNameFromOther = {}
            self.__patternsFromLanguageName = None
            self._resetFileAssociationData()

    def _resetFileAssociationData(self):
        self.__languageNameFromPattern = {}
        self.__languageNameFromExtOrBasename = {}
        self.__languageNameFromOther = {}
        self.__factoryLanguageNameFromPattern = {}
        self.__patternsFromLanguageName = {}

        # Load 'factoryFileAssociations' pref.
        factoryFileAssociationsRepr \
            = self._globalPrefs.getStringPref("factoryFileAssociations")
        for pattern, languageName in eval(factoryFileAssociationsRepr).items():
            self._addOneFileAssociation(pattern, languageName)

        # Apply fallback default extensions from all registered languages.
        for defaultExtension, languageName in self._defaultLanguageExtensions.items():
            self._addOneFileAssociation('*'+defaultExtension, languageName,
                                        override=False)
        for pattern, languageName in self._defaultFileAssociations.items():
            self._addOneFileAssociation(pattern, languageName,
                                        override=False)

        # Make a copy of the current association set before applying
        # user/site-level changes so we can compare against it latter to know
        # what changes (if any) the user made.
        self.__factoryLanguageNameFromPattern \
            = self.__languageNameFromPattern.copy()

        # Load 'fileAssociationDiffs' pref.
        if self._globalPrefs.hasStringPref("fileAssociationDiffs"):
            fileAssociationDiffsRepr \
                = self._globalPrefs.getStringPref("fileAssociationDiffs")
            try:
                for action, pattern, languageName in eval(fileAssociationDiffsRepr):
                    if action == '+':
                        self._addOneFileAssociation(pattern, languageName)
                    elif action == '-':
                        self._removeOneFileAssociation(pattern, languageName)
                    else:
                        log.warn("unexpected action in 'fileAssociationDiffs' "
                                 "entry (skipping): %r",
                                 (action, pattern, languageName))
            except (SyntaxError, ValueError), ex:
                log.exception("error loading 'fileAssociationDiffs' "
                              "(skipping): %s", fileAssociationDiffsRepr)

    def _removeOneFileAssociation(self, pattern, languageName):
        if languageName == self.__languageNameFromPattern.get(pattern):
            log.debug("remove '%s' -> '%s' file association", pattern,
                      languageName)
            self.__languageNameFromPattern.pop(pattern)
            self.__languageNameFromOther.pop(pattern, None)
            self.__patternsFromLanguageName[languageName].remove(pattern)

            # Don't use splitext, as we want all extensions, not just the last
            # one, e.g. 'foo.django.html' > ('foo', 'django.html') - bug 97967.
            pattern_split = pattern.split('.', 1)
            base = pattern_split[0]
            ext = pattern_split[1] if len(pattern_split) > 1 else ''
            if base == '*' and ext and "*" not in ext:  # i.e. pattern == "*.FOO"
                if languageName == self.__languageNameFromExtOrBasename.get(ext.lower()):
                    del self.__languageNameFromExtOrBasename[ext.lower()]
            elif '*' not in pattern:  # e.g. "Conscript", "Makefile"
                if languageName == self.__languageNameFromExtOrBasename.get(pattern.lower()):
                    del self.__languageNameFromExtOrBasename[pattern.lower()]
            else:
                # Everything else that doesn't fit into the above two cases.
                if languageName == self.__languageNameFromOther.get(pattern.lower()):
                    del self.__languageNameFromOther[pattern]

    def _addOneFileAssociation(self, pattern, languageName, override=True):
        """Add one file association to the internal data structures.

            "pattern" is the association pattern (e.g. "*.py")
            "languageName" is the language name (e.g. "Python")
            "override" is an optional boolean (default True) indicating
                whether this setting should override existing settings. This
                option is here so ko*Language.py components can specify a
                fallback "*.py" extension pattern for their filetypes, but
                the associations in the "fileAssociations" pref still wins.
        """
        if not override and pattern in self.__languageNameFromPattern:
            if languageName != self.__languageNameFromPattern[pattern]:
                log.debug("KoLanguageRegistryService: not using default '%s' "
                          "pattern for '%s' language (already mapped to '%s')",
                          pattern, languageName,
                          self.__languageNameFromPattern[pattern])
            return
        #elif not override:
        #    print "using fallback defaultExtension: '%s' -> '%s'" \
        #          % (pattern, languageName)

        self.__languageNameFromPattern[pattern] = languageName

        if languageName not in self.__patternsFromLanguageName:
            self.__patternsFromLanguageName[languageName] = []
        self.__patternsFromLanguageName[languageName].append(pattern)

        # Don't use splitext, as we want all extensions, not just the last
        # one, e.g. 'foo.django.html' > ('foo', 'django.html') - bug 97967.
        pattern_split = pattern.split('.', 1)
        base = pattern_split[0]
        ext = pattern_split[1] if len(pattern_split) > 1 else ''
        if base == '*' and ext and "*" not in ext:  # i.e. pattern == "*.FOO"
            self.__languageNameFromExtOrBasename[ext.lower()] = languageName
        elif '*' not in pattern:  # e.g. "Conscript", "Makefile"
            self.__languageNameFromExtOrBasename[pattern.lower()] = languageName
        else:
            # Everything else that doesn't fit into the above two cases.
            self.__languageNameFromOther[pattern] = languageName

    _addonsEnabled = {}

    def _preloadAddonEnabledStatus(self):
        # bug 94778: the addon manager is async, so it needs to be
        # pre-populated at startup-time
        try:
            addonMgr = components.classes["@activestate.com/platform/addons/addon-manager;1"]. \
                        getService(components.interfaces.koamIAddonManager)
            def addonListCallback(addons):
                for addon in addons:
                    self._addonsEnabled[addon.id] = addon.isActive
            addonMgr.getAllAddons(addonListCallback)
        except:
            log.exception("Failed to work with addons")

    def addonIsEnabled(self, id, default=False):
        if id in self._addonsEnabled:
            return self._addonsEnabled[id]

        if os.environ.has_key("KO_PYXPCOM_PROFILE"):
            # The addonMgr does not work well with the profiler, so we just
            # let all addons be enabled when profiling is enabled.
            self._addonsEnabled[id] = True
            return True

        try:
            addonMgr = components.classes["@activestate.com/platform/addons/addon-manager;1"]. \
                        getService(components.interfaces.koamIAddonManager)
            def addonCallback(addon):
                if addon is not None:
                    self._addonsEnabled[id] = addon.isActive
                else:
                    self._addonsEnabled[id] = default
            addonMgr.getAddonByID(id, addonCallback)
        except COMException:
            log.warn("addonIsEnabled:: unable to obtain Addon Manager")
            # Not available in the test environment.
            self._addonsEnabled[id] = default
        return default

    def getLanguageHierarchy(self):
        """Return the structure used to define the language name menulist
        used in various places in the Komodo UI.
        """
        primaries = []
        others = []
        for languageName in self.__languageFromLanguageName:
            if languageName in self._internalLanguageNames:
                continue
            elif self._primaryLanguageNames.get(languageName):
                primaries.append(languageName)
            else:
                others.append(languageName)

        # Sort by language name - case insensitive.
        primaries.sort(key=lambda x: x.lower())
        others.sort(key=lambda x: x.lower())

        otherContainer = KoLanguageContainer('Other',
            [KoLanguageItem(ln, self.__accessKeyFromLanguageName.get(ln, ""))
             for ln in others])
        primaryContainer = KoLanguageContainer('',
            [KoLanguageItem(ln, self.__accessKeyFromLanguageName.get(ln, ""))
             for ln in primaries]
            + [otherContainer])
        return primaryContainer

    def changeLanguageStatus(self, languageName, status):
        lang = self.getLanguage(languageName)
        lang.primary = status
        if status:
            self._primaryLanguageNames[languageName] = True
        else:
            try:
                del self._primaryLanguageNames[languageName]
            except KeyError:
                pass

    def getLanguageNames(self):
        languageNames = self.__languageFromLanguageName.keys()
        languageNames.sort()
        languageNames = [name for name in languageNames
                         if name not in self._internalLanguageNames]
        return languageNames
    
    def patternsFromLanguageName(self, languageName):
        if self.__patternsFromLanguageName is None:
            self._resetFileAssociationData()
        return self.__patternsFromLanguageName.get(languageName, [])

    def registerLanguages(self):
        """registerLanguages
        
        Registers the languages listed in the "komodo-language-info" category..
        """
        from urllib import unquote
        from json import loads

        for entry in _xpcom.GetCategoryEntries("komodo-language-info"):
            lang, json_data = [unquote(x) for x in entry.split(" ", 1)]
            try:
                lang_data = loads(json_data)
            except:
                log.error("Unable to load komodo-language-info for %s %r", lang, json_data)
            else:
                self._registerLanguageData(lang, lang_data)

    def _registerLanguageData(self, lang, data):
        assert (lang not in self.__languageFromLanguageName), \
               "Language '%s' already registered" % (lang)
        log.info("registering language [%s]", lang)

        # Register the name, the instance will be instantiated on demand.
        self.__languageFromLanguageName[lang] = None
        
        if "accessKey" in data:
            self.__accessKeyFromLanguageName[lang] = data["accessKey"]
        if data.get("internal"):
            self._internalLanguageNames[lang] = True
        if "defaultExtension" in data:
            defaultExtension = data["defaultExtension"]
            existingLang = self._defaultLanguageExtensions.get(defaultExtension)
            if not defaultExtension.startswith('.'):
                log.warn("'%s': skipping unexpected defaultExtension for "
                         "language '%s': it must begin with '.'",
                         defaultExtension, lang)
            else:
                self._defaultLanguageExtensions[defaultExtension] = lang
        for ext in data.get("extraFileAssociations", []):
            existingLang = self._defaultFileAssociations.get(ext)
            if existingLang:
                if existingLang != lang:
                    log.warn("ext pattern %r, lang %s - already "
                             "registered to lang %s", ext, lang,
                             existingLang)
            else:
                self._defaultFileAssociations[ext] = lang
        for pattern, flags in data.get("shebangPatterns", []):
            self.shebangPatterns.append((lang, re.compile(pattern, flags)))
        for ns in data.get("namespaces", []):
            self._namespaceMap[ns] = lang
        for id in data.get("publicIdList", []):
            self._publicIdMap[id] = lang
        for id in data.get("systemIdList", []):
            self._systemIdMap[id] = lang

        # Mode - so that we can tell that, for example:
        #     -*- mode: javascript -*-
        # means language name "JavaScript".
        modeNames = set(data.get("modeNames", []))
        modeNames.add(lang)
        for modeName in modeNames:
            self._modeName2LanguageName[modeName.lower()] = lang

        # Update primary field based on user preference.
        prefname = "languages/%s/primary" % (lang,)
        prefdefault = bool(int(data.get("primary", 0)))
        if self._globalPrefs.getBoolean(prefname, prefdefault):
            self._primaryLanguageNames[lang] = True

    ##
    # @deprecated since Komodo 9.0.0
    #
    def registerLanguage(self, language):
        import warnings
        warnings.warn("registerLanguage is deprecated - no longer needed",
                      category=DeprecationWarning)

        name = language.name
        assert not self.__languageFromLanguageName.has_key(name), \
               "Language '%s' already registered" % (name)
        log.info("registering language [%s]", name)
        
        self.__languageFromLanguageName[name] = language
        language = UnwrapObject(language)
        self.__accessKeyFromLanguageName[name] = language.accessKey

        # Update fields based on user preferences:
        primaryLanguagePref = "languages/%s/primary" % (language.name,)
        if self._globalPrefs.hasPref(primaryLanguagePref):
            language.primary = self._globalPrefs.getBoolean(primaryLanguagePref)

        # So that we can tell that, for example:
        #     -*- mode: javascript -*-
        # means language name "JavaScript".
        if language.modeNames:
            for modeName in language.modeNames:
                self._modeName2LanguageName[modeName.lower()] = name
        else:
            self._modeName2LanguageName[name.lower()] = name
        if language.primary:
            self._primaryLanguageNames[name] = True
        if language.internal:
            self._internalLanguageNames[name] = True
        for pat in language.shebangPatterns:
            self.shebangPatterns.append((name, pat))
        for ns in language.namespaces:
            self._namespaceMap[ns] = name
        for id in language.publicIdList:
            self._publicIdMap[id] = name
        for id in language.systemIdList:
            self._systemIdMap[id] = name


    def getLanguage(self, language):
        # return a koILanguage for language.  Create it if it does not
        # exist yet.
        if not language: language=self.defaultLanguage
        
        if language not in self.__languageFromLanguageName:
            log.warn("Asked for unknown language: %r", language)
            if language != self.defaultLanguage:
                return self.getLanguage(self.defaultLanguage)
            # Trouble if we can't load the default language.
            return None

        if self.__languageFromLanguageName[language] is None:
            contractid = "@activestate.com/koLanguage?language=%s;1" \
                         % (language.replace(" ", "%20"))
            self.__languageFromLanguageName[language] = components.classes[contractid] \
                    .createInstance(components.interfaces.koILanguage)

        return self.__languageFromLanguageName[language]

    def suggestLanguageForFile(self, basename, os_path_basename=os.path.basename):
        if self.__languageNameFromPattern is None:
            self._resetFileAssociationData()

        # First try to look up the language name from the file extension or
        # plain basename: faster.  We use the longest possible extension so
        # we can match things like *.django.html
        basename = os_path_basename(basename) # want a basename, not a path
        basename = basename.lower()
        exts = basename.split(".")[1:]
        if len(exts) >= 2:
            # Bug 97967: use the longest compounded extension first, 
            #            until we're down to the final extension.
            # e.g. "foo.blatz.html.erb" => ['.blatz.html.erb', '.html.erb',
            #                               '.erb']
            # so .html.erb => RHTML if there is a '*.html.erb' association.
            exts = ['.'.join(exts[i:]) for i in range(len(exts))]

        for ext in exts:
            lang = self.__languageNameFromExtOrBasename.get(ext)
            if lang is not None:
                #print "suggestLanguageForFile: '%s' -> '%s'" % (ext, lang)
                return lang

        lang = self.__languageNameFromExtOrBasename.get(basename)
        if lang is not None:
            #print "suggestLanguageForFile: '%s' -> '%s'" % (basename, lang)
            return lang

        #print "Unknown file %r" % (basename, )
        # Next, try each registered filename glob pattern: slower.  Use the
        # longest pattern first
        for pattern, lang in self.__languageNameFromOther.items():
            if fnmatch.fnmatch(basename, pattern):
                self.__languageNameFromExtOrBasename[basename] = lang
                #print "suggestLanguageForFile: %r %r -> '%s'" % (basename, pattern, lang)
                return lang

        # Remember it for next time.
        if exts:
            #print "suggestLanguageForFile: No lang for ext: %r" % (ext.lower(), )
            self.__languageNameFromExtOrBasename[exts[-1]] = ''
        else:
            #print "suggestLanguageForFile: No lang for basename: %r" % (basename, )
            self.__languageNameFromExtOrBasename[basename] = ''

        return ''  # indicates that we don't know the lang name

    def getFileAssociations(self):
        """Return the list of the file associations:
            <pattern> -> <language name>
        
        - They are returned as two separate lists for simplicity of passing
          across XPCOM.
        - The list is sorted.
        """
        associations = [(p, ln) for (p, ln) in self.__languageNameFromPattern.items()]
        associations.sort()
        return ([p  for p,ln in associations],
                [ln for p,ln in associations])

    def createFileAssociationPrefString(self, patterns, languageNames):
        """Create a pref string from the given set of file associations.
        
        Typically called by the "File Associations" preferences panel.
        Instead of saving the full associations list in the user's prefs, we
        just save a diff against the "factory" associations list.
        """
        #TODO: Warn/die if any duplicate patterns: indicates bug in caller.

        # Massage data for faster lookup.
        #       {'a': 1, 'b': 2}   ->   {('a', 1): True, ('b', 2): True}
        factoryAssociations = dict(
            ((k,v), True) for k,v in self.__factoryLanguageNameFromPattern.items()
        )
        associations = dict(
            ((k,v), True) for k,v in zip(patterns, languageNames)
        )

        # Calculate the diffs. ('p' == pattern, 'ln' == language name)
        additions = [('+', p, ln) for (p, ln) in associations.keys()
                                   if (p, ln) not in factoryAssociations]
        deletions = [('-', p, ln) for (p, ln) in factoryAssociations.keys()
                                   if (p, ln) not in associations]
        diffs = additions + deletions
        return repr(diffs)

    def saveFileAssociations(self, patterns, languageNames):
        """Save the given set of file associations."""
        assocPref = self.createFileAssociationPrefString(patterns, languageNames)
        self._globalPrefs.setStringPref("fileAssociationDiffs", assocPref)

    def _sendStatusMessage(self, msg, timeout=3000, highlight=1):
        observerSvc = components.classes["@mozilla.org/observer-service;1"]\
                      .getService(components.interfaces.nsIObserverService)
        sm = components.classes["@activestate.com/koStatusMessage;1"]\
             .createInstance(components.interfaces.koIStatusMessage)
        sm.category = "language_registry"
        sm.msg = msg
        sm.timeout = timeout     # 0 for no timeout, else a number of milliseconds
        sm.highlight = highlight # boolean, whether or not to highlight
        try:
            observerSvc.notifyObservers(sm, "status_message", None)
        except COMException, e:
            # do nothing: Notify sometimes raises an exception if (???)
            # receivers are not registered?
            pass

    emacsLocalVars1_re = re.compile("-\*-\s*(.*?)\s*-\*-")
    # This regular expression is intended to match blocks like this:
    #    PREFIX Local Variables: SUFFIX
    #    PREFIX mode: Tcl SUFFIX
    #    PREFIX End: SUFFIX
    # Some notes:
    # - "[ \t]" is used instead of "\s" to specifically exclude newlines
    # - "(\r\n|\n|\r)" is used instead of "$" because the sre engine does
    #   not like anything other than Unix-style line terminators.
    emacsLocalVars2_re = re.compile(r"^(?P<prefix>(?:[^\r\n|\n|\r])*?)[ \t]*Local Variables:[ \t]*(?P<suffix>.*?)(?:\r\n|\n|\r)(?P<content>.*?\1End:)",
                                    re.IGNORECASE | re.MULTILINE | re.DOTALL)
    def _getEmacsLocalVariables(self, head, tail):
        """Return a dictionary of emacs local variables.
        
            "head" is a sufficient amount of text from the start of the file.
            "tail" is a sufficient amount of text from the end of the file.
        
        Parsing is done according to this spec (and according to some
        in-practice deviations from this):
            http://www.gnu.org/software/emacs/manual/html_chapter/emacs_33.html#SEC485
        Note: This has moved to:
            http://www.gnu.org/software/emacs/manual/emacs.html#File-Variables
            
        A ValueError is raised is there is a problem parsing the local
        variables.
        """
        localVars = {}

        # Search the head for a '-*-'-style one-liner of variables.
        if head.find("-*-") != -1:
            match = self.emacsLocalVars1_re.search(head)
            if match:
                localVarsStr = match.group(1)
                if '\n' in localVarsStr:
                    raise ValueError("local variables error: -*- not "
                                     "terminated before end of line")
                localVarStrs = [s.strip() for s in localVarsStr.split(';') if s.strip()]
                if len(localVarStrs) == 1 and ':' not in localVarStrs[0]:
                    # While not in the spec, this form is allowed by emacs:
                    #   -*- Tcl -*-
                    # where the implied "variable" is "mode". This form is only
                    # allowed if there are no other variables.
                    localVars["mode"] = localVarStrs[0].strip()
                else:
                    for localVarStr in localVarStrs:
                        try:
                            variable, value = localVarStr.strip().split(':', 1)
                        except ValueError:
                            raise ValueError("local variables error: malformed -*- line")
                        # Lowercase the variable name because Emacs allows "Mode"
                        # or "mode" or "MoDe", etc.
                        localVars[variable.lower()] = value.strip()

        # Search the tail for a "Local Variables" block.
        match = self.emacsLocalVars2_re.search(tail)
        if match:
            prefix = match.group("prefix")
            suffix = match.group("suffix")
            lines = match.group("content").splitlines(0)
            #print "prefix=%r, suffix=%r, content=%r, lines: %s"\
            #      % (prefix, suffix, match.group("content"), lines)
            # Validate the Local Variables block: proper prefix and suffix
            # usage.
            for i in range(len(lines)):
                line = lines[i]
                if not line.startswith(prefix):
                    raise ValueError("local variables error: line '%s' "
                                     "does not use proper prefix '%s'"
                                     % (line, prefix))
                # Don't validate suffix on last line. Emacs doesn't care,
                # neither should Komodo.
                if i != len(lines)-1 and not line.endswith(suffix):
                    raise ValueError("local variables error: line '%s' "
                                     "does not use proper suffix '%s'"
                                     % (line, suffix))
            # Parse out one local var per line.
            for line in lines[:-1]: # no var on the last line ("PREFIX End:")
                if prefix: line = line[len(prefix):] # strip prefix
                if suffix: line = line[:-len(suffix)] # strip suffix
                line = line.strip()
                try:
                    variable, value = line.split(':', 1)
                except ValueError:
                    raise ValueError("local variables error: missing colon "
                                     "in local variables entry: '%s'" % line)
                # Do NOT lowercase the variable name, because Emacs only
                # allows "mode" (and not "Mode", "MoDe", etc.) in this block.
                localVars[variable] = value.strip()

        return localVars

    def guessLanguageFromFullContents(self, fileNameLanguage, buffer, koDoc):
        langs, modelineLangs, shebangLangs = \
               self.guessLanguageFromContents(buffer[:1000],
                                              buffer[-1000:],
                                              returnDetails=True)
        if not modelineLangs and not shebangLangs:
            # Deal with variants of languages here.
            if fileNameLanguage == "Python":
                newLang = self._distinguishPythonVersion(buffer, koDoc)
                if newLang:
                    langs.insert(0, newLang)
            elif fileNameLanguage == "JavaScript":
                newLang = self._distinguishJavaScriptOrNode(buffer)
                if newLang:
                    langs.insert(0, newLang)
        return langs
        
    _htmldoctype_re = re.compile('<!DOCTYPE\s+html',
                                re.IGNORECASE)
    def guessLanguageFromContents(self, head, tail, returnDetails=False):
        """Guess the language (e.g. Perl, Tcl) of a file from its contents.
        
            "head" is a sufficient amount of text from the start of the file
                where "sufficient" is undefined (although, realistically
                at least the first few lines should be passed in to get good
                coverage).
            "tail" is a sufficient amount of text from the end of the file,
                where "sufficient" is as above. (Usually the tail of the
                document is where Emacs-style local variables. Emacs'
                documentation says this block should be "near the end of
                the file, in the last page.")

        This method returns a list of possible languages with the more
        likely, or more specific, first. If no information can be gleaned an
        empty list is returned.
        """
        langs = []
        modelineLangs = []
        shebangLangs = []

        # Specification of the language via Emacs-style local variables
        # wins, so we check for it first.
        #   http://www.gnu.org/manual/emacs-21.2/html_mono/emacs.html#SEC486
        if self._globalPrefs.getBooleanPref("emacsLocalModeVariableDetection"):
            # First check for one-line local variables.
            # - The Emacs spec says this has to be in the _first_ line,
            #   but in practice this seems to be "near the top".
            try:
                localVars = self._getEmacsLocalVariables(head, tail)
            except ValueError, ex:
                self._sendStatusMessage(str(ex))
            else:
                if localVars.has_key("mode"):
                    mode = localVars["mode"]
                    try:
                        langName = self._modeName2LanguageName[mode.lower()]
                    except KeyError:
                        log.warn("unknown emacs mode: '%s'", mode)
                    else:
                        langs = [langName]
                        modelineLangs = [langName]

        # Detect if this is an XML file.
        if self._globalPrefs.getBooleanPref('xmlDeclDetection') and \
            (not langs or 'XML' in langs):
            # it may be an XHTML file
            lhead = head.lower()
            if lhead.startswith(u'<?xml'):
                langs.append("XML")

            try:
                # find the primary namespace of the first node
                tree = koXMLTreeService.getService().getTreeForContent(head)
                if tree and tree.root is not None:
                    ns = tree.namespace(tree.root)
                    #print "XML NS [%s]" % ns
                    if ns in self._namespaceMap:
                        #print "language is [%s]" % self._namespaceMap[ns]
                        langs.append(self._namespaceMap[ns])
    
                # use the doctype decl if one exists
                if tree and tree.doctype:
                    #print "XML doctype [%s]" % repr(tree.doctype)
                    if tree.doctype[2] in self._publicIdMap:
                        langs.append(self._publicIdMap[tree.doctype[2]])
                    if tree.doctype[3] in self._systemIdMap:
                        langs.append(self._systemIdMap[tree.doctype[3]])
                    if tree.doctype[0].lower() == "html":
                        langs.append("HTML")
                elif self._htmldoctype_re.search(lhead):
                    langs.append("HTML5")
            except Exception, e:
                # log this, but keep on going, it's just a failure in xml
                # parsing and we can live without it.  bug 67251
                log.exception(e)
            langs.reverse()
            #print "languages are %r"%langs

        # Detect Django content - ensuring the add-on is enabled.
        addDjangoLikeNames = False
        if not langs or langs[0] in ("HTML", "HTML5", "XHTML"):
            # Sniff the html contents for Django tags.
            if "{%" in head and "%}" in head:
                if "{{" in head or "}}" in head:
                    # Multiple tag styles - it's Django.
                    addDjangoLikeNames = True
                elif head.count("{%") >= 2 and head.count("%}") >= 2:
                    # Multiple tag usage - it's Django.
                    addDjangoLikeNames = True
        if addDjangoLikeNames:
            for langName in ["Django", "Twig", "Smarty"]:
                if self.addonIsEnabled(langName.lower() + "_language@ActiveState.com"):
                    langs.append(langName)

        # Detect the type from a possible shebang line.
        if (self._globalPrefs.getBooleanPref('shebangDetection') and
            not langs and head.startswith(u'#!')):
            for language, pattern in self.shebangPatterns:
                if pattern.match(head):
                    shebangLangs.append(language)
            if len(shebangLangs) > 1:
                self._sendStatusMessage("language determination error: "
                    "ambiguous shebang (#!) line: indicates all of '%s'"
                    % "', '".join(shebangLangs))
            else:
                langs = shebangLangs

        if returnDetails:
            return langs, modelineLangs, shebangLangs
        else:
            return langs
        
    _jsDistinguisher = None
    def _distinguishJavaScriptOrNode(self, buffer):
        currentProject = components.classes["@activestate.com/koPartService;1"]\
            .getService(components.interfaces.koIPartService).currentProject
        if currentProject:
            if currentProject.prefset.getBoolean("preferJavaScriptOverNode", False):
                return "JavaScript"

            prefset = currentProject.prefset
            if prefset.hasPref("currentInvocationLanguage") \
               and prefset.getStringPref("currentInvocationLanguage") == "Node.js":
                return "Node.js"
        elif self._globalPrefs.getBoolean("preferJavaScriptOverNode", False):
            return "JavaScript"
        if not buffer:
            return "JavaScript"
        nodeJSAppInfo = components.classes["@activestate.com/koAppInfoEx?app=NodeJS;1"].\
                        getService(components.interfaces.koIAppInfoEx)
        if not nodeJSAppInfo.executablePath:
            return "JavaScript"
        import pythonVersionUtils
        if self._jsDistinguisher is None:
            self._jsDistinguisher = pythonVersionUtils.JavaScriptDistinguisher()
        if self._jsDistinguisher.isNodeJS(buffer):
            return "Node.js"
        return "JavaScript"

    _pythonNameByVersion = {2: "Python", 3: "Python3"}
    def _distinguishPythonVersion(self, buffer, koDoc):
        """
        If the user has an installation for only one of the Python
        versions, favor that.  Otherwise, analyze the buffer.
        """
        import pythonVersionUtils
        python2 = self._getPython2Path(koDoc)
        python3 = self._getPython3Path(koDoc)
        # If the buffer's empty, favor v2 over v3.
        if (not python2) == (not python3):
            # Either we have both, or neither, so we need to do
            # further analysis.
            isPython3 = pythonVersionUtils.isPython3(buffer)
            if isPython3:
                versionNo = 3
            else:
                versionNo = 2
        elif python2:
            versionNo = 2
        else:
            versionNo = 3
        return self._pythonNameByVersion[versionNo]

    def _getPython2Path(self, koDoc):
        python2Path = koDoc.getEffectivePrefs().getStringPref("pythonDefaultInterpreter")
        if python2Path and os.path.isfile(python2Path):
            return python2Path
        python2Info = components.classes["@activestate.com/koAppInfoEx?app=%s;1"
                                        % 'Python'] \
                        .getService(components.interfaces.koIAppInfoEx)
        python2Path = python2Info.executablePath
        if not python2Path or not os.path.exists(python2Path):
            try:
                python2Path = which.which("python")
            except which.WhichError:
                python2Path = None
        return python2Path

    def _getPython3Path(self, koDoc):
        python3Path = koDoc.getEffectivePrefs().getStringPref("python3DefaultInterpreter")
        if python3Path and os.path.isfile(python3Path):
            return python3Path
        python3Info = components.classes["@activestate.com/koAppInfoEx?app=%s;1"
                                        % 'Python3'] \
                        .getService(components.interfaces.koIAppInfoEx)
        python3Path = python3Info.executablePath
        if not python3Path or not os.path.exists(python3Path):
            try:
                python3Path = which.which("python3")
            except which.WhichError:
                python3Path = None
        return python3Path

    def __initPrefs(self):
        self.__prefs = components \
                       .classes["@activestate.com/koPrefService;1"] \
                       .getService(components.interfaces.koIPrefService)\
                       .prefs
        # Observers will be QI'd for a weak-reference, so we must keep the
        # observer alive ourself, and must keep the COM object alive,
        # _not_ just the Python instance!!!
        # XXX - this is a BUG in the weak-reference support.
        # It should NOT be necessary to do this, as the COM object is
        # kept alive by the service manager.  I suspect that this bug
        # happens due to the weak-reference being made during
        # __init__.  FIXME!
        self._observer = xpcom.server.WrapObject(self,
                                      components.interfaces.nsIObserver)
        self.__prefs.prefObserverService.addObserver(self._observer,
                                                     'fileAssociationDiffs',
                                                     True)


# Used for the Primary Languages tree widget in 
# pref-languages.xul/js.
# Based on KoCodeIntelCatalogsTreeView
class KoLanguageStatusTreeView(TreeView):
    _com_interfaces_ = [components.interfaces.koILanguageStatusTreeView,
                        components.interfaces.nsITreeView]
    _reg_clsid_ = "{6e0068df-0b51-47ae-9195-8309b52eb78c}"
    _reg_contractid_ = "@activestate.com/koLanguageStatusTreeView;1"
    _reg_desc_ = "Komodo Language Status list tree view"
    _col_id = "languageStatus-status"
    _prefix = "languageStatus-"

    def __init__(self):
        TreeView.__init__(self) # for debug logging: , debug="languageStatus")
        self._rows = []
        # Atoms for styling the checkboxes.
        atomSvc = components.classes["@mozilla.org/atom-service;1"].\
                  getService(components.interfaces.nsIAtomService)
        self._sortColAtom = atomSvc.getAtom("sort-column")
        self._filter = self._filter_lc = ""
        
    def init(self):
        self._sortData = (None, None)
        self._loadAllLanguages()
        self._reload()
        self._wasChanged = False

    def _loadAllLanguages(self):
        self._allRows = []
        langRegistry = components.classes["@activestate.com/koLanguageRegistryService;1"].getService(components.interfaces.koILanguageRegistryService)
        langRegistry = UnwrapObject(langRegistry)
        langNames = langRegistry.getLanguageNames()
        for langName in langNames:
            isPrimary = langRegistry._primaryLanguageNames.get(langName, False)
            self._allRows.append({'name':langName,
                                  'name_lc':langName.lower(),
                                  'status':isPrimary,
                                  'origStatus':isPrimary})

    def _reload(self):
        oldRowCount = len(self._rows)
        self._rows = []
        for row in self._allRows:
            if not self._filter or self._filter_lc in row['name_lc']:
                self._rows.append(row)
        if self._sortData == (None, None):
            self._rows.sort(key=lambda r: (r['name_lc']))
        else:
            # Allow for sorting by both name and status
            sort_key, sort_is_reversed = self._sortData
            self._do_sort(sort_key, sort_is_reversed)

        if self._tree:
            self._tree.beginUpdateBatch()
            newRowCount = len(self._rows)
            self._tree.rowCountChanged(oldRowCount, newRowCount - oldRowCount)
            self._tree.invalidate()
            self._tree.endUpdateBatch()

    def save(self, prefs):
        if not self._wasChanged:
            return
        langRegistry = UnwrapObject(Cc["@activestate.com/koLanguageRegistryService;1"]
                                      .getService(Ci.koILanguageRegistryService))
        for row in self._rows:
            langName, status, origStatus = row['name'], row['status'], row['origStatus']
            if status != origStatus:
                langRegistry.changeLanguageStatus(langName, status)
                # Update the pref
                primaryLanguagePref = "languages/%s/primary" % (langName,)
                prefs.setBoolean(primaryLanguagePref, bool(status))
        self.notifyObservers(None, 'primary_languages_changed', '')

    @components.ProxyToMainThread
    def notifyObservers(self, subject, topic, data):
        obsSvc = Cc["@mozilla.org/observer-service;1"]\
                   .getService(Ci.nsIObserverService)
        obsSvc.notifyObservers(subject, topic, data)

    def toggleStatus(self, row_idx):
        """Toggle selected state for the given row."""
        self._rows[row_idx]["status"] = not self._rows[row_idx]["status"]
        self._wasChanged = True
        if self._tree:
            self._tree.invalidateRow(row_idx)
        

    def set_filter(self, filter):
        self._filter = filter
        self._filter_lc = self._filter.lower()
        self._reload()

    def get_filter(self):
        return self._filter

    def get_sortColId(self):
        sort_key = self._sortData[0]
        if sort_key is None:
            return None
        else:
            return "languageStatus-" + sort_key
        
    def get_sortDirection(self):
        return self._sortData[1] and "descending" or "ascending"
        
    def get_rowCount(self):
        return len(self._rows)

    def getCellValue(self, row_idx, col):
        assert col.id == self._col_id
        return self._rows[row_idx]["status"] and "true" or "false"
    

    def setCellValue(self, row_idx, col, value):
        assert col.id == self._col_id
        self._wasChanged = True
        self._rows[row_idx]["status"] = (value == "true" and True or False)
        if self._tree:
            self._tree.invalidateRow(row_idx)

    def getCellText(self, row_idx, col):
        if col.id == self._col_id:
            return ""
        else:
            try:
                key = col.id[len("languageStatus-"):]
                return self._rows[row_idx][key]
            except KeyError, ex:
                raise ValueError("getCellText: unexpected col.id: %r" % col.id)

    def isEditable(self, row_idx, col):
        if col.id == self._col_id:
            return True
        else:
            return False

    def getColumnProperties(self, col, properties=None):
        # Mozilla 22+ does not have a properties argument.
        if properties is None:
            return "sort-column"
        if col.id[len("languageStatus-"):] == self._sortData[0]:
            properties.AppendElement(self._sortColAtom)

    def isSorted(self):
        return self._sortData != (None, None)

    def cycleHeader(self, col):
        sort_key = col.id[len("languageStatus-"):]
        old_sort_key, old_sort_is_reversed = self._sortData
        if sort_key == old_sort_key:
            sort_is_reversed = not old_sort_is_reversed
            self._rows.reverse()
        else:
            sort_is_reversed = False
            self._do_sort(sort_key, sort_is_reversed)
        self._sortData = (sort_key, sort_is_reversed)
        if self._tree:
            self._tree.invalidate()

    def _do_sort(self, sort_key, sort_is_reversed):
        if sort_key == 'status':
            self._rows.sort(key=lambda r: (not r['status'],
                                           r['name_lc']),
                            reverse=sort_is_reversed)
        else:
            self._rows.sort(key=lambda r: r['name_lc'],
                            reverse=sort_is_reversed)


# Local Variables:
# mode: Python
# End:

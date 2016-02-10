# Copyright 2016 ActiveState Software Inc. See LICENSE.txt for license details.
"""
Pulls the latest Angular.js library from the internet and parses that library's
documentation into a Komodo API catalog.
jsdoc and yuidoc cannot be used because Angular has decided to use their own
documentation language flavor.
"""

import re
import urllib

from codeintel2.gencix_utils import *

import logging
logging.basicConfig(level=logging.INFO)

# Retrieve Angular source.
angular_file = "angular.js"
if not os.path.exists(angular_file):
    angular_url = "https://ajax.googleapis.com/ajax/libs/angularjs/1.4.9/angular.js"
    logging.info("Retrieving Angular from '%s'", angular_url)
    f = open(angular_file, "wb")
    f.write(urllib.urlopen(angular_url).read())
    f.close()
else:
    logging.info("Found existing Angular ('%s')", angular_file)

# Extract documentation from Angular.
ignore = ['module', 'directive', 'event', 'filter', 'input']
version = None
docs = {}
for doc in re.findall('/\*\*(.+?)\*/', open(angular_file).read(), re.S):
    if not version:
        # Extract the Angular version, which is in the first doc block.
        version = re.compile('@license.+?v([0-9.]+)').search(doc).group(1)
    if "@ngdoc" in doc and "@name" in doc:
        kind = re.search('@ngdoc\s+(\w+)', doc).group(1)
        if kind in ignore: continue
        name = re.search('@name\s+([^\s]+)', doc).group(1)
        if kind not in docs:
            docs[kind] = {}
        docs[kind][name] = doc

# Print some statistics.
logging.info("Angular version is %s", version)
for kind in sorted(docs.keys()):
    logging.info("There are %s %ss.", len(docs[kind]), kind)

# Start converting the documentation into CIX objects.
cix_root = createCixRoot(name="AngularJS-%s" % version,
                         description="HTML enhanced for web apps!")
cix_file = createCixFile(cix_root, "AngularJS", lang="JavaScript")
cix_module = createCixModule(cix_file, "AngularJS-%s" % version, lang="JavaScript")

def get_namespace(scope, namespaces):
    """
    Retrieves a given namespace in the given scope, creating namespaces as
    necessary.
    @param scope The scope to search.
    @param namespaces Array of namespaces to retrieve. For example, the
        `angular.Module` namespace would be ['angular', 'Module'].
    """
    for name in namespaces:
        if not name in scope.names:
            logging.info("Adding namespace '%s.%s'", scope.get('name'), name)
            scope = createCixNamespace(scope, name)
        else:
            scope = scope.names[name]    
    return scope

def set_description(scope, doc):
    """
    Extracts an item's description and assigns that description to the given
    scope.
    @param scope The scope to assign a description to (e.g. function, class, or
        variable).
    @param doc The JavaScript doc block to extract a description from.
    """
    desc = re.search('^\s*\*\s*@description\s*(.+?)\s*\*(?:\s*@|/)', doc,
                     re.M | re.S)
    if desc:
        patt = re.compile('^\s*\*\s*', re.M)
        setCixDoc(scope, patt.sub('', desc.group(1)))
    else:
        logging.debug("No @description for '%s'", scope.get('name'))

def add_function(scope, name, doc):
    """
    Adds a named function along with its documentation to the given scope.
    @param scope The scope to add the function to.
    @param name The name of the function to add.
    @param doc The JavaScript doc block to parse and attach to the function
        being added.
    """
    logging.info("Adding function '%s.%s'", scope.get('name'), name)
    scope = createCixFunction(scope, name)
    # Description.
    set_description(scope, doc)
    # Function parameters/arguments.
    args = []
    for type, arg, desc in re.findall('^\s*\*\s*@param\s+{([^}]+)}\s+(\w+)\s+(.+?)\s*\*(?:\s*@|/)', doc, re.M):
        addCixArgument(scope, arg, type, desc)
        args.append(arg)
    # Return value.
    ret = re.search('^\s*\*\s*@returns\s+{([^}]+)}', doc, re.M)
    if ret:
        setCixSignature(scope, '%s(%s) => %s' % (name, ','.join(args), ret.group(1)))
        addCixReturns(scope, ret.group(1))
    else:
        setCixSignature(scope, '%s(%s)' % (name, ','.join(args)))

# Create functions.
logging.info("Adding functions.")
for full_name in sorted(docs['function'].keys()):
    scope = get_namespace(cix_module, full_name.split('.')[:-1])
    add_function(scope, full_name.split('.')[-1], docs['function'][full_name])

def add_class(scope, name, doc):
    """
    Adds a named class along with its documentation to the given scope.
    @param scope The scope to add the class to.
    @param name The name of the class to add.
    @param doc The JavaScript doc block to parse and attach to the class being
        added.
    """
    logging.info("Adding class '%s.%s'", scope.get('name'), name)
    scope = createCixClass(scope, name)
    set_description(scope, doc)

# Create providers, services, and types.
logging.info("Adding providers.")
for name in sorted(docs['provider'].keys()):
    add_class(cix_module, name, docs['provider'][name])
logging.info("Adding services.")
for name in sorted(docs['service'].keys()):
    add_class(cix_module, name, docs['service'][name])
logging.info("Adding types.")
for full_name in sorted(docs['type'].keys()):
    scope = get_namespace(cix_module, full_name.split('.')[:-1])
    add_class(scope, full_name.split('.')[-1], docs['type'][full_name])

def get_class(scope, klass):
    """
    Retrieves a given class in the given scope, creating parent classes as
    necessary.
    @param scope The scope to search.
    @param klass The full name of the class as a string.
    """
    for name in klass.split('.')[:-1]:
        if not name in scope.names:
            logging.warn("Unknown namespace '%s.%s'; adding", scope.get('name'), name)
            scope = createCixNamespace(scope, name)
        else:
            scope = scope.names[name]    
    klass = klass.split('.')[-1]
    if not klass in scope.names:
        logging.warn("Unknown class '%s'; adding", klass)
        scope = createCixClass(scope, klass)
    else:
        scope = scope.names[klass]
    return scope

def add_variable(scope, name, doc):
    """
    Adds a named variable along with its documentation to the given scope.
    @param scope The scope to add the variable to.
    @param name The name of the variable to add.
    @param doc The JavaScript doc block to parse and attach to the variable
        being added.
    """
    logging.info("Adding variable '%s.%s'", scope.get('name'), name)
    scope = createCixVariable(scope, name)
    set_description(scope, doc)

# Create methods, properties, and objects.
logging.info("Adding methods.")
for full_name in sorted(docs['method'].keys()):
    klass, name = full_name.split('#')
    scope = get_class(cix_module, klass)
    add_function(scope, name, docs['method'][full_name])
logging.info("Adding properties.")
for full_name in sorted(docs['property'].keys()):
    klass, name = full_name.split('#')
    scope = get_class(cix_module, klass)
    add_variable(scope, name, docs['property'][full_name])
logging.info("Adding objects.")
for full_name in sorted(docs['object'].keys()):
    scope = get_namespace(cix_module, full_name.split('.')[:-1])
    add_variable(scope, full_name.split('.')[-1], docs['object'][full_name])

# Output the CIX file.
cix_filename = "angular-%s.cix" % version
logging.info("Writing CIX to '%s'" % cix_filename)
f = open(cix_filename, 'wb')
f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
prettify(cix_root) # pretty-print XML
ElementTree(cix_root).write(f)
f.close()

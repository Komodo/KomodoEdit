# Copyright 2016 ActiveState Software Inc. See LICENSE.txt for license details.
# Requires yuidoc (npm install yuidocjs).
"""
Pulls the latest Ember.js library from the internet, parses that library's
documentation into JSON via yuidoc, and transforms the JSON into a Komodo API
catalog.
"""

import json
import os
import re
import urllib

from codeintel2.gencix_utils import *

import logging
logging.basicConfig(level=logging.INFO)

yuidoc = "node_modules/.bin/yuidoc"
if not os.path.exists(yuidoc):
    logging.fatal("'%s' not found", yuidoc)
    exit(1)

# Retrieve Ember source.
ember_file = "ember.js"
if not os.path.exists(ember_file):
    ember_url = "http://builds.emberjs.com/tags/v2.3.0/ember.prod.js"
    logging.info("Retrieving Ember from '%s'", ember_url)
    f = open(ember_file, "wb")
    f.write(urllib.urlopen(ember_url).read())
    f.close()
else:
    logging.info("Found existing Ember ('%s')", ember_file)

# Run yuidoc, which generates a json data output file.
data_file = "data.json"
if not os.path.exists(data_file):
    logging.info("Running yuidoc on '%s'", ember_file)
    if os.system("%s -n -T simple -p -o . ." % yuidoc) != 0:
        exit(1)
else:
    logging.info("Found existing yuidoc ('%s')", data_file)

# Load the json data output file.
logging.info("Processing output '%s'...", data_file)
data = json.load(open(data_file))

# Extract the Ember version and print some statistics.
version = re.compile('[0-9.]+').match(data['classes']['Ember']['version']).group()
logging.info("Ember version is %s", version)
logging.info("There are %d modules and %d classes", len(data['modules']),
                                                    len(data['classes']))

# Start converting the JSON data into CIX objects.
cix_root = createCixRoot(name="Ember-%s" % version,
                         description="A framework for creating ambitious web applications")
cix_file = createCixFile(cix_root, "Ember", lang="JavaScript")
cix_module = createCixModule(cix_file, "Ember-%s" % version, lang="JavaScript")

# Create classes (they will be filled in later).
for klass in sorted(data['classes'].keys()):
    info = data['classes'][klass]
    #if info.get('access', 'public') == 'private':
    #    logging.info("Skipping private class '%s'", klass)
    #    continue
    
    scope = cix_module
    namespaces = klass.split('.')
    for name in namespaces[:-1]:
        if name not in scope.names:
            logging.info("Adding namespace '%s.%s'", scope.get('name'), name)
            scope = createCixNamespace(scope, name)
        else:
            scope = scope.names[name]
    logging.info("Adding class '%s'", klass)
    scope = createCixClass(scope, namespaces[-1])
    if info.has_key('description'):
        setCixDoc(scope, info['description'])
    if info.has_key('extends'):
        addClassRef(scope, info['extends'])
    
# Fill in the classes.
for item in data['classitems']:
    #if item.get('access', 'public') == 'private': continue
    scope = cix_module
    for name in item['class'].split('.'):
        if name in scope.names:
            scope = scope.names[name]
        else:
            scope = None
            break
    if scope is None or not item.has_key('itemtype'):
        logging.warn("Cannot process '%s.%s'", item['class'],
                                               item.get('name', '(anonymous)'))
        continue
    
    logging.info("Processing %s '%s.%s'", item['itemtype'], item['class'],
                                          item['name'])
    if item['itemtype'] == 'method':
        scope = createCixFunction(scope, item['name'], item.get('access'))
        if item.has_key('description'):
            setCixDoc(scope, item['description'])
        args = item.get('params', [])
        for arg in args:
            addCixArgument(scope, arg['name'], arg.get('type'), arg['description'])
        if item.has_key('return'):
            addCixReturns(scope, item['return'].get('type'))
        if item.has_key('return') and item['return'].has_key('type'):
            setCixSignature(scope,
                            '%s(%s) => %s' % (item['name'],
                                              ','.join([arg['name'] for arg in args]),
                                              item['return']['type']))
        else:
            setCixSignature(scope, '%s(%s)' % (item['name'],
                                               ','.join([arg['name'] for arg in args])))
    elif item['itemtype'] == 'property' or item['itemtype'] == 'event':
        scope = createCixVariable(scope, name, item.get('type'),
                                  ' '.join([item['itemtype'], item.get('access')]))
        if item.has_key('description'):
            setCixDoc(scope, item['description'])
    else:
        logging.warn("Ignoring unknown attribute: %s", item['itemtype'])

# Output the CIX file.
cix_filename = "ember-%s.cix" % version
logging.info("Writing CIX to '%s'" % cix_filename)
f = open(cix_filename, 'wb')
f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
prettify(cix_root) # pretty-print XML
ElementTree(cix_root).write(f)
f.close()

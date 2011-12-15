// Copyright (c) 2000-2011 ActiveState Software Inc.
// See the file LICENSE.txt for licensing information.

/* koextgen lib defined here
 *
 * Defines the "ko.places" namespace.
 */
if (typeof(ko) == 'undefined') {
    var ko = {};
}
if (!('koextgen' in ko)) {
    ko.koextgen = {};
}
if (!('extensionLib' in ko.koextgen)) {
    ko.koextgen.extensionLib = {};
}
(function() {

this.os = Components.classes['@activestate.com/koOs;1'].
    getService(Components.interfaces.koIOs);
this.error = false;

this.getProjectPath = function(relative) {
    try {
        var prj_path = ko.interpolate.interpolateString('%p');
        var path = this.os.path.join(prj_path, relative);
        return path;
    } catch(e) {
        alert(e+"\n arg name: "+name);
        return "";
    }
}

this.getTemplateContents = function(basename, targetName) {
    var sepDir = (!targetName ? "" : (targetName + "/"));
    var uri = "chrome://koextgen/content/resources/" + sepDir + basename;
    return this.readFile(uri);
}

this.readFile = function(filename) {
    // read the template file
    try {
        var fileEx = Components.classes["@activestate.com/koFileEx;1"]
                .createInstance(Components.interfaces.koIFileEx);
        fileEx.URI = filename;
        fileEx.open('rb');
        var content = fileEx.readfile();
        fileEx.close();
        return content;
    } catch(e) {
        alert(e+"\narg filename: "+filename);
        return "";
    }
}

this.writeFile = function(filename, content) {
    try {
        var fileEx = Components.classes["@activestate.com/koFileEx;1"]
                .createInstance(Components.interfaces.koIFileEx);
        fileEx.URI = filename;
        fileEx.open('wb+');
        fileEx.puts(content);
        fileEx.close();
    } catch(e) {
        alert(e+"\narg filename: "+filename);
    }
}

this.updateProject = function(projectDirPath, targetName, vars) {
    try {
        var varEquivalents = {
          'creator': 'author_name',
          'ext_name': 'nice_name',
          'homepageURL': 'homepage'
        };
        var origContents;
        var rawPtn, newVars = {}, replVal;
        // Moz is picky about what can do in an extension name
        vars.name = vars.name.replace(/\W+/, "").toLowerCase();
        vars.id = vars.id.toLowerCase();
        for (var p in vars) {
            if (p in varEquivalents) {
                rawPtn = "%extension_" + varEquivalents[p] + "%";
            } else {
                rawPtn = "%extension_" + p + "%";
            }
            // Assume that all tagnames match /^%[\w_]+$/
            newVars[rawPtn] = [new RegExp(rawPtn, "g"), vars[p]];
        }
          
        var koFileEx = ko.projects.manager.currentProject.getFile();
        var basename = vars.name + "_overlay.xul";
        // The overlay goes in the contents dir
        var contentPath = this.os.path.join(projectDirPath, "content");
        if (!this.os.path.exists(contentPath)) {
            this.os.mkdir(contentPath);
        }

        var overlayPath = this.getProjectPath(this.os.path.join("content", basename));
        origContents = this.getTemplateContents("overlay.xul", targetName);
        this.writeFile(overlayPath, this.replaceAll(newVars, origContents));

        var this_ = this;
        var manifestPath;
        ["chrome.manifest", "chrome.p.manifest", "install.rdf"].forEach(
            function(fname) {
                origContents = this_.getTemplateContents(fname, targetName);
                manifestPath = this_.getProjectPath(fname);
                this_.writeFile(manifestPath, this_.replaceAll(newVars, origContents));
            });
        
    } catch(e) {
        this.error = e;
        return false;
    }
    return true;
}

this.replaceAll = function(orig_vars, str) {
    try {
        var ptn_string, pair, ptn, repl;
        for (ptn_string in orig_vars) {
            pair = orig_vars[ptn_string];
            str = str.replace(pair[0], pair[1]);
        }
        return str;
    } catch(e) {
        alert(e);
        return "";
    }
}

this.getNiceName = function(name) {
    return this.trim(name).replace(/[\W]/g,'').toLowerCase();
}

this.trim = function(str) {
    return str.replace(/^\s*/, '').replace(/\s*$/, '');
}

this.clone = function(obj) {
    var newobj = {};
    for(i in obj) {
        newobj[i] = obj[i];
    }
    return newobj;
}

this._dump = function(obj) {
    var str = '';
    for(i in obj) {
        str += i+': '+obj[i]+'\n';
    }
    return(str);
}

this._keys = function(obj) {
  var out = new Array();
  for(i in obj) {
    out.push(i);
  }
  return out;
}

}).apply(ko.koextgen.extensionLib);

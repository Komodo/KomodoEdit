/* JeffG Copyright (c) 2006 ActiveState Software
   See the file LICENSE.txt for licensing information. w00t. */

if (typeof(zendutils) == 'undefined') {
  var zendutils = {};
}

(function() {

// essential function

/**
 * Id
 * @param {String} strId the string id we're looking for
 * @returns {element}
 */

function Id(strId) {
  return document.getElementById(strId);
}

this.Id = Id;

// some xpcom services

var os = Components.classes['@activestate.com/koOs;1'].
  getService(Components.interfaces.koIOs);
var koDirs = Components.classes['@activestate.com/koDirs;1'].
  getService(Components.interfaces.koIDirs);

this.wizardURI = 'chrome://zendframework/content/zendMVCWizard.xul';
this.winOpts = "centerscreen,chrome,resizable,scrollbars,dialog=no,close,modal=yes";
this.picked_proj_path = false;
this.picked_fw_path = false;
this.hasFS = false;
this.hasFw = false;

var ANCHOR_MARKER = '!@#_anchor';
var CURRENTPOS_MARKER = '!@#_currentPos';

/**
 * openZendWizard
 * @param {object} args
 */

this.openZendWizard = function(args) {
  try {
    ko.windowManager.openDialog(
      this.wizardURI,
      'zend_dialog',
      this.winOpts,
      args
    );
  } catch(e) {
    ko.dialogs.internalError(e, 'Error: '+e);
  }
}

/**
 * onDialogLoad
 */

this.onZendLoad = function() {
  try {
    if(typeof(winArgs) !== 'undefined') {
      
      this.Id('zend_project_location').value = winArgs.path;
      if(winArgs.hasFS) {
        this.Id('zend_has_fs_desc').setAttribute('hidden', false);
        var fwPath = this.getFwPath(winArgs.path);
        
        if(this.hasZendFw(fwPath)) {
          this.Id('zend_framework_location').value = fwPath;
          this.Id('Zend:toggle_fw_default_path').hidden = false;
          this.Id('zendfw_use_default_path').checked = true;
        }
      }
      this.validate();
    }
    
  } catch(e) {
    ko.dialogs.internalError(e, 'Error: '+e);
  }
}

/**
 * getFwPath: description
 * @param {String} path
 * @returns {String}
 */

this.getFwPath = function(path) {
  var tmparr = [path, 'library', 'Zend'];
  return os.path.joinlist(tmparr.length, tmparr);
}

/**
 * locationToggle
 * @param {Event} evt
 */

this.toggleProjCheckbox = function() {
  try {
    var checkbox = this.Id('zend_use_default_path');
    if (checkbox.hasAttribute('checked')) {
      this.picked_proj_path = this.Id('zend_project_location').value;
      this.Id('zend_project_location').value = winArgs.path;
      this.Id('Zend:pick_proj_path').setAttribute('disabled', true);
    } else {
      this.Id('Zend:pick_proj_path').removeAttribute('disabled');
      if(this.picked_proj_path !== false) {
        this.Id('zend_project_location').value = this.picked_proj_path;
      }
    }
  } catch(e) {
    ko.dialogs.internalError(e, 'Error in toggle: '+e);
  }
}

/**
 * toggleFwCheckbox
 */

this.toggleFwCheckbox = function() {
  try {
    //alert('in fw toggle');
    var checkbox = this.Id('zendfw_use_default_path');
    if(checkbox.hasAttribute('checked')) {
      this.Id('Zend:pick_fw_path').setAttribute('disabled', true);
    } else {
      this.Id('Zend:pick_fw_path').removeAttribute('disabled');
      if(this.picked_fw_path) {
        this.Id('zend_framework_location').value = this.picked_fw_path;
      } else {
        var p = this.getFwPath(this.Id('zend_project_location').value);
        this.Id('zend_framework_location').value = p;
      }
      
    }
  } catch(e) {
    ko.dialogs.internalError(e, 'Error in toggle: '+e);
  }
}

//var getDir = ko.filepicker.browseForDir;

/**
 * browseProjDir: description
 */

this.browseProjDir = function() {
  try {
    var prefName = "zendutils.browseDir"
    var default_dir = ko.filepicker.internDefaultDir(prefName);
    var newDir = ko.filepicker.getFolder(default_dir);
    if(newDir) {
      ko.filepicker.internDefaultDir(prefName, newDir);
      this.Id('zend_project_location').value = newDir;
      this.picked_proj_path = newDir;
      this.validate();
    }
  } catch(e) {
    ko.dialogs.internalError(e, 'Error: '+e);
  }
}



/**
 * browseLibDir: description
 */

this.browseLibDir = function() {
  try {
    var prefName = "zendutils.browseDir"
    var default_dir = ko.filepicker.internDefaultDir(prefName);
    var newDir = ko.filepicker.getFolder(default_dir);
    if (newDir && this.hasZendFw(newDir)) {
      ko.filepicker.internDefaultDir(prefName, newDir);
      this.Id('zend_framework_location').value = newDir;
      this.picked_fw_path = newDir;
      this.validate();
    } else {
      ko.dialogs.alert('The chosen directory does not seem to contain the Zend Framework:\n'+newDir);
    }
  } catch(e) {
    ko.dialogs.internalError(e, 'Error: '+e);
  }
}

/**
 * validate
 */

this.validate = function() {
  try {
    var projLoc = this.Id('zend_project_location').value;
    if(this.isZendProject(projLoc)) {
      this.hasFS = true;
      this.Id('zend_has_fs_desc').setAttribute('hidden', false);
    } else {
      this.hasFS = false;
      this.Id('zend_has_fs_desc').setAttribute('hidden', true);
    }
    
    if(this.Id('zendfw_use_default_path').checked == true) {
      this.Id('zend_framework_location').value = this.getFwPath(projLoc);
    }
    
    var vcmd = document.getElementById('Zend:form_validated');
    if(this.hasValidPath('zend_project_location')) {
      vcmd.removeAttribute('disabled');
    } else {
      vcmd.setAttribute('disabled', true);
    }
  } catch(e) {
    ko.dialogs.internalError(e, 'Error in toggle: '+e);
  }
}

/**
 * hasValidPath
 * @param strId
 */

this.hasValidPath = function(strId) {
  var path = this.Id(strId).value;
  if(os.path.exists(path)) {
    return true;
  }
  return false;
}

/**
 * save: saves the prefs, runs scaffold()
 */

this.save = function() {
  try {
    // somehow save path to includedirs
    var zend_include_path = this.Id('zend_framework_location').value;
    
    if(zend_include_path && this.hasZendFw(zend_include_path)) {
      winArgs.zendFwPath = zend_include_path;
    }
    
    var zend_proj_path = this.Id('zend_project_location').value;
    this.hasFS = this.isZendProject(zend_proj_path);
    
    winArgs.hasFS = this.hasFS;
    if(!winArgs.hasFs) {
      winArgs.scaffold = true;
      
      if (this.picked_proj_path !== false) {
        winArgs.projPath = this.picked_proj_path;
      } else {
        winArgs.projPath = winArgs.path;
      }
    } else { // no scaffolding
      winArgs.scaffold = false;
    }
    window.close();
  } catch(e) {
    ko.dialogs.internalError(e, 'Error: '+e);
  }
}

/**
 * addReplaceZendFwPath(): adds the fw path to the project prefs, replacingand
 * existing fw path if it is there
 * @param {String} newVal
 */

this.addReplaceZendFwPath = function(newVal) { // newVal is definitely a Zend framework path
  try{
    
    var project = ko.projects.manager.currentProject;
    var prefset = project.prefset;
    var newPref = '';
    var pref = prefset.getStringPref('phpExtraPaths');
    if (pref !== '') {
      //ko.utils.print('got pref: '+pref);
      var pref_arr = pref.split(os.pathsep);
      if (pref_arr.length == 1) { // only 1 path?
        if(zendutils.hasZendFw(pref)) {  // replacement
          newPref = newVal;
        } else { 
          newPref = pref + os.pathsep + newVal;
        }
      } else {
        for(i in pref_arr) {
          if(pref_arr[i] !== '' && !zendutils.hasZendFw(pref_arr[i])) {
            newPref += pref_arr[i] + os.pathsep;
          }
        }
        newPref += newVal;
      }
    } else { // no existing pref
      newPref = newVal;
    }
    prefset.setStringPref('phpExtraPaths', newPref);
  } catch(e) {
    ko.dialogs.internalError(e, 'Error: '+e);
  }
}

/* -- Some local utilities -- */

this.layoutData = {
  'application'     : {
    'controllers': true,
    'views': {
      'scripts': true,
      'helpers': true,
      'filters': true
    },
    'models': true
  },
  'library'         : {'Zend': false},
  'public'          : true
};

/**
 * isZendProject: try to sniff out if the supplied path contains an existing zend project
 * @param {String} path
 * @returns {bool}
 */

this.isZendProject = function(path) {
  var out = new Array();
  if (os.path.exists(path)) {
    var list = os.listdir(path, out);
    for (i in this.layoutData) {
      if (_has(list, i)) {
        out.push(list[i]);
      }
    }
  }
  
  if (out.length == 3) {
    if (out[0] == 'application' && out[1] == 'library' && out[2] == 'public') {
      return true;
    }
  }
  return false;
}

/**
 * hasZendFw
 * @param {String} path should be <dir>/library/Zend
 */

this.hasZendFw = function (path) {
  var versionPath = os.path.join(path, 'Version.php');
  if(os.path.exists(path) && os.path.isfile(versionPath)) {
    return true;
  }
  return false;
}

/**
 * findAll: description
 * @param {String} rx
 * @param {String} text
 * @returns {Array}
 */

this.findAll = function(rx, text) {
  rx = new RegExp(rx, "g");
  var out = new Array();
  while((match = rx.exec(text)) !== null) {
    out.push(match);
  }
  return out;
}

/**
 * _has
 * @param {Array} arr
 * @param {String} dir
 */

function _has(arr, key) {
  for (i in arr) {
    if (arr[i] == key) {
      return true;
    }
  }
  return false;
}

/**
 * makeLayout
 * @param {object} layout
 * @param {String} root
*/

function makeLayout(layout, root) {
  if(!os.path.exists(root)) {
    return false;
  }
  for(i in layout) { // at top level
    if(layout[i] !== false) {
      _makeLayout(i, layout[i], root);
    }
  }
  return true;
}

/**
 * _makeLayout : create a filesystem layout
 * @param {String} name
 * @param {object} obj
 * @param {String} root
 */

function _makeLayout(name, obj, root) {
  var path = os.path.join(root, name);
  if (!os.path.exists(path) && obj !== false) {
    os.mkdir(path);
    if (typeof(obj) == 'object') {
      for (i in obj) {
        _makeLayout(i, obj[i], path);
      }
    }
  } 
}

/**
 * scaffold: runs makeLayout and adds in the default views and controllers
 */

this.scaffold = function(projPath) {
  try {
    makeLayout(this.layoutData, projPath);
    
    var project = ko.projects.manager.currentProject;
    var bootstrapPath = getFilePath('bootstrap', 'bootstrap.php', projPath);

    // add the bootstrap file
    var bsSnpt = ko.projects.findPart('snippet', 'BootstrapStub', '*', project);
    var bootstrapText = deMarkerIfy(bsSnpt.value);
    _newFile(bootstrapPath, bootstrapText);
    
    // add the index.php file
    var indexPath = getFilePath('index', 'index.php', projPath);
    var indexSnpt = ko.projects.findPart('snippet', 'IndexStub', '*', project);
    var indexText = deMarkerIfy(indexSnpt.value);
    _newFile(indexPath, indexText);
    
    _addController('index', projPath);
    _addView('index', 'index', projPath);
  } catch(e) {
    ko.dialogs.internalError(e, 'Error in scaffold: '+e);
  }
}

/**
 * setLiveDir: description
 * @param {String} path
 */

this.setLiveDir = function(path) {
  var project = ko.projects.manager.currentProject;
  var prefs = project.prefset;
  prefs.setStringPref("import_dirname", path);
}

/**
 * addView: adds a view to the current app based on user input
 */

this.addView = function() {
  var args = ko.dialogs.prompt2(
    'To add a view script, you need to supply the controller and the action:',
    'Controller:',
    'index',
    'Action:',
    'index',
    'Add a view script'
  );
  if(args && args.length == 2) {
    _addView(args[0], args[1]);
  }
}

/**
 * _addView: implementation, can be used by automation scripts
 * @param {String} controller
 * @param {String} action
 * @param {String} projPath optional
 */

function _addView(controller, action, projPath) {
  try {
    var project = ko.projects.manager.currentProject;
    if(typeof(projPath) == 'undefined') {
      projPath = project.importDirectoryLocalPath || project.importDirectoryURI;
    }
    var snpt = ko.projects.findPart('snippet', 'ZendView', '*', project);
    var origTxt = snpt.value;
    var newView = tabstopReplacer(action, origTxt);
    var viewFile = _fixViewPath(action) + '.phtml';
    viewFile = getFilePath('views', viewFile, projPath, _fixViewPath(controller.toLowerCase()));
    var viewPath = os.path.dirname(viewFile);
    if(!os.path.exists(viewPath)) {
      os.mkdir(viewPath);
    }
    _newFile(viewFile, newView);
  } catch(e) {
    ko.dialogs.internalError(e, 'Error: '+e);
  } 
}

/**
 * _newFile
 * @param path
 */

function _newFile(path, text, fileType /*=PHP*/) {
  if(typeof(fileType) == 'undefined') {
    fileType = 'PHP';
  }
  
  if(!os.path.exists(path)) {
    ko.views.manager.doNewViewAsync(fileType, 'editor', function(view) {
      view.koDoc.buffer = text;
      view.koDoc.new_line_endings = view.koDoc.EOL_LF;
      view.koDoc.existing_line_endings = view.koDoc.EOL_LF;
      view.saveAsURI(path);
    });
  } else {
    ko.dialogs.alert('The file '+os.path.basename(path)
                     + ' already exists at the loaction '
                     + os.path.dirname(path));
  }
}

/**
 * addController: adds a new controller to the project
 */

this.addController = function() {
  var name = ko.dialogs.prompt('New Controller name');
  if(name) {
    _addController(name);
  }
}

/**
 * _addController
 * @param name
 */

function _addController(name, projPath) {
  try {
    var project = ko.projects.manager.currentProject;
    if(typeof(projPath) == 'undefined') {
      projPath = project.importDirectoryLocalPath || project.importDirectoryURI;
    }
    var snpt = ko.projects.findPart('snippet', 'ZendController', '*', project);
    var snptTxt = snpt.value;
    var newController = tabstopReplacer(name, snptTxt);
    var controllerFile = capitalize(name) + 'Controller.php';
    var controllerPath = getFilePath('controllers', controllerFile, projPath);
    _newFile(controllerPath, newController);
  } catch(e) {
    ko.dialogs.internalError(e, 'Error: '+e);
  }
}

/**
 * getFilePath()
 * @param {String} type
 * @param {String} fileName
 * @param {String} projPath
 * @param {String} folderName
 */

function getFilePath(type, fileName, projPath, folderName) {
  try {
    var arr = new Array();
    switch(type) {
      case "controllers":
        arr = [projPath, 'application', type, fileName];
        break;
      case "views":
        arr = [projPath, 'application', type, 'scripts', folderName, fileName];
        break;
      case "bootstrap":
        arr = [projPath, 'application', fileName];
        break;
      case "index":
        arr = [projPath, 'public', fileName];
        break;
    }
    var ret = os.path.joinlist(arr.length, arr);
    return ret;
  } catch(e) {
    ko.dialogs.internalError(e, 'Error in getFilePath: '+e);
  }
  return false
}

/**
 * tabstopReplacer - replace tabstops in the snippet with our user-supplied name
 * @param {String} arg
 * @param {String} text
 */

function tabstopReplacer(arg, text) {
  var keys = getTabstopKeys(text);
  var args = [];
  for(i=0;i<keys.length;i++) {
    // is the first char of the string in caps?
    if(/^[A-Z]/.test(keys[i])) {
      args.push(capitalize(arg));
    } else {
      args.push(arg.toLowerCase());
    }
  }
  var rx = new RegExp(/\[\[\%tabstop\:[\S\ ]+?\]\]/g);
  var newStr = text;
  if(!rx.test(text)) { // detect the tabstops
    return false;
  } else {
    for (i=0;i<keys.length;i++) {
      // create the specific string we're replacing
      var target = "\[\[\%tabstop\:"+keys[i]+"\]\]";
      newStr = newStr.replace(target, args[i]);
    }
  }
  var viewData = ko.interpolate.getViewData(window);
  var istrings = ko.interpolate.interpolate(
                        window,
                        [], // codes are not bracketed
                        [newStr], // codes are bracketed
                        arg,
                        viewData);
  newStr = deMarkerIfy(istrings[0]); // take out cursor pos markers
  return newStr;
}

/**
 * deMarkerIfy
 * @param {String} str
 */

function deMarkerIfy(Str) {
  var newStr = Str.replace(CURRENTPOS_MARKER, '');
  newStr = newStr.replace(ANCHOR_MARKER, '');
  return newStr;
}

/**
 * capitalize - only works for first word, doesn't split words.
 * @param {String} str
 */

function capitalize(str) {
  var first = str.substring(0,1);
  var rest = str.substring(1, str.length);
  return first.toUpperCase() + rest.toLowerCase();
}

/**
 * getTabstopKeys - gets all the tabstop keys form the text
 * @param {String} text
 */

function getTabstopKeys(text) {
  var keyArr = findAll(/\[\[\%tabstop\:([\w\ ]+?)\]\]/g, text);
  var keys = [];
  for (i in keyArr) {
    keys.push(keyArr[i][1]);
  }
  return keys;
}

/**
 * findAll - kinda like in Python
 * @param {RegExp} rx - but it might not be
 * @param {String} text
 */

function findAll(rx, text) {
  var match = false;
  rx = new RegExp(rx);
  var out = new Array();
  while((match = rx.exec(text)) !== null) {
    out.push(match);
  }
  return out;
}

/**
 * _fixViewPath
 * @param {String} str
 */

function _fixViewPath(name) {
  var outname = '';
  name = name.replace(/[\.\_]/g, '-');
  for(i=0; i<name.length;i++) {
    var tmp = name[i];
    if(/[A-Z]/.test(tmp)) {
      //this is a capital
      tmp = '-'+tmp.toLowerCase();
    }
    outname += tmp;
  }
  
  return outname.replace(/[\-]{2,9}/g, '-');
}

/**
 * nicePath
 * @param {String} raw
 * @returns {String}
 */

function nicePath(raw) {
  var out = trim(raw);
  out = out.replace(/[\s]/g, '_');
  if (out.length == 0) {
    return false;
  }
  return out;
}

/**
 * trim: trims leading and trailing whitespace
 * @param {String} str
 */

function trim(str) {
  return str.replace(/^[\s]+/, '').replace(/[\s]+$/, '');
}

}).apply(zendutils);

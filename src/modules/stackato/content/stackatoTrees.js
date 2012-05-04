// Copyright (c) 2000-2011 ActiveState Software Inc.
// See the file LICENSE.txt for licensing information.

/**
 *
 * stackatoTrees.js -- JS code for the trees for the Stackato interface
 *
 */

var log;
if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.stackato)=='undefined') {
    ko.stackato = {};
}
if (typeof(ko.stackato.trees)=='undefined') {
    ko.stackato.trees = {};
}

var widgets = {};
(function() {

var log = ko.logging.getLogger("stackato.trees");
var gCurrTree =  null;
var gStackatoPrefs = null;

function cmpFields(a, b) {
    if (a < b) return -1;
    if (a > b) return 1;
    return 0;
}
function cmpFieldsOverNames(a, b, names) {
    for each (var name in names) {
        var res = cmpFields(a[name], b[name]);
        if (res != 0) return res;
    }
    return 0;
}

this.GenericTree = function() {
    xtk.hierarchicalTreeView.apply(this);
};
this.GenericTree.prototype = new xtk.hierarchicalTreeView();
this.GenericTree.prototype.contructor = this.GenericTree;
this.GenericTree.prototype.getCellText = function(row, column) {
    var col_id = column.id
    var s  = ">> getCellText:" + row + ", " + col_id;
    //dump(s + "\n");
    try {
        return this._rows[row].fields[col_id];
    } catch(ex) {
        dump(s + ": " + ex + "\n");
        return ""
    }    
};
this.GenericTree.prototype.getRow = function(index) {
    return this._rows[index];
};
this.GenericTree.prototype.clear = function() {
    this.setTreeRows([]);
};
this.GenericTree.prototype.getNames = function() {
    var name = this.treeName + "_name";
    return this._rows.map(function(a) a.fields[name]);
};
this.GenericTree.prototype.getNameAtIndex = function(index) {
    var name = this.treeName + "_name";
    return this._rows[index].fields[name];
};
this.GenericTree.prototype.getIndexForName = function(name) {
    var fieldName = this.treeName + "_name";
    var rows = this._rows;
    for (var i = 0; i < rows.length; i++) {
        if (rows[i].fields[fieldName] == name) return i;
    }
    return -1;
};


/////////////////////////////////////////////////////////////

this.ApplicationRow = function(newLevel) {
    this.treeName = ""
    this.level = newLevel;
    this.isContainer = false;
    this.state = xtk.hierarchicalTreeView.STATE_CLOSED;
    this.hasChildren = false;
    this.children = [];
    this.propertyNames = {};
    this.data = {}; // Used by the client to store info like paths
};

this.ApplicationRow.prototype.getChildren = function() {
    if (!this.hasChildren) {
        return [];
    }
    var numKids = this.children.uris.length;
    if (!numKids) {
        return [];
    }
    var newRows = [];
    var newRow;
    var children = this.children;
    var newLevel = this.level + 1;
    for (var i = 0; i < numKids; i++) {
        newRow = new ko.stackato.trees.ApplicationRow(newLevel);
        newRow.fields = {
            'name': '',
            'health': '',
            'num_instances': '',
            'serviceName': children.services[i],
            'url': children.uris[i],
            'env_name': children.env_names[i],
            'env_value': children.env_values[i]
        };
        newRows.push(newRow);
    }
    return newRows;
};

this.ApplicationsTree = function(prefs) {
    gStackatoPrefs = prefs;
    ko.stackato.trees.GenericTree.apply(this);
    this.showingEnvironment = false;
    this.envVarData = {}; // appName => [list of envNames, list of envValues]
};
this.ApplicationsTree.prototype = new this.GenericTree();
this.ApplicationsTree.prototype.contructor = this.ApplicationsTree;

this.ApplicationsTree.prototype.setEnvironmentValueStatus =  function(status) {
    this.showingEnvironment = status;
}

this.ApplicationsTree.prototype.setStackatoPrefs =  function(prefs) {
    
};

this.ApplicationsTree.prototype._evenOutSetChildren = function(row, uris, services, env_names, env_values) {
    this._evenOut([uris, services, env_names, env_values]);
    if (uris.length) {
        row.isContainer = true;
        row.hasChildren = true;
        row.children = {
          uris: uris,
          services: services,
          env_names: env_names,
          env_values: env_values
        };
    } else {
        row.isContainer = false;
        row.hasChildren = false;
        delete row.children;
    }
};

this.ApplicationsTree.prototype.setData = function(results) {
    var newRow, rows = [];
    var appName;
    var env_names, env_values, data, item, uris, services;
    for each (item in results) {
        appName = item.name;
        if (this.envVarData[appName]) {
            data = this.envVarData[appName]
            env_names =  data[0].concat([]);
            env_values = data[1].concat([]);
        } else {
            env_names = [""];
            env_values = [""];
        }
        newRow = new ko.stackato.trees.ApplicationRow(0);
        item.services.sort();
        item.uris.sort();
        newRow.fields = {
            'name': appName,
            'health': item.state,
            'num_instances': item.instances, // .numRunningInstances ?
            'serviceName': item.services.shift() || "",
            'url':         item.uris.shift()     || "",
            'env_name':    env_names.shift()     || "",
            'env_value':   env_values.shift()    || ""
        };
        if (item.services.length || item.uris.length) {
            uris = item.uris;
            services = item.services;
            this._evenOutSetChildren(newRow, uris, services, env_names, env_values);
        }
        rows.push(newRow);
    }
    rows.sort(this.sortRows);
    this.setTreeRows(rows);
    var appPrefs = gStackatoPrefs.getPref("apps");
    // See which names need to be expanded.
    for (var i = rows.length - 1; i >= 0; i--) {
        var row = rows[i];
        var appName = row.fields.name;
        if (appName
            && appPrefs.hasPref(appName)) {
            var appPref = appPrefs.getPref(appName);
            if (appPref.hasPref("row.state")
                && (appPref.getLongPref("row.state")
                    == xtk.hierarchicalTreeView.STATE_OPENED)
                && row.state != xtk.hierarchicalTreeView.STATE_OPENED) {
                this.doToggleOpenState(i);
            }
        }
    }
};

this.ApplicationsTree.prototype.addEnvironmentData = function(appName, results){
    var env_names = [];
    var env_values = [];
    var i;
    results.sort();
    for each (var envvar in results) {
            i = envvar.indexOf("=");
            if (i == -1) {
                env_names.push(envvar);
                env_values.push("");
            } else {
                env_names.push(envvar.substr(0, i));
                env_values.push(envvar.substr(i + 1));
            }
        }
    this.envVarData[appName] = [env_names, env_values];
    var index, row;
    [index, row] = this.getMainRowForApp(appName);
    if (!row) {
        return;
    }
    if (!row.hasChildren && env_names.length == 0) {
        // No change
        row.fields.env_name = "";
        row.fields.env_value = "";
    } else {
        row.fields.env_name = env_names.shift();
        row.fields.env_value = env_values.shift();
        var uris, services;
        var rowHadChildren, numChildren;
        if (row.children) {
            [uris, services] = [row.children.uris || [],
                                row.children.services || []];
            rowHadChildren = true;
            numChildren = uris.length;
        } else {
            [uris, services] = [[], []];
        }
        this._evenOutSetChildren(row, uris, services, env_names, env_values);
        if (row.hasChildren) {
            if (!rowHadChildren) {
                this.tree.invalidateRow(index); // To draw the twisty.
            } else if (row.state == xtk.hierarchicalTreeView.STATE_OPENED) {
                // Get toggle to handle all the logic.
                this.doToggleOpenState(index);
                this.doToggleOpenState(index);
            }
        } else if (rowHadChildren) {
            // have to delete the obsolete child rows.
            this._rows.splice(index + 1, numChildren);
            this.tree.rowCountChanged(index + 1, -numChildren);
            this.tree.invalidateRow(index); // To redraw the twisty.
        }
    }
};

this.ApplicationsTree.prototype.removeEnvValuesFromTree = function() {
    var appNames = this.getNames();
    var index, row;
    var uris, services, env_names, env_values;
    for each (var appName in appNames) {
            [index, row] = this.getMainRowForApp(appName);
            if (!row || !row.hasChildren) {
                continue;
            }
            var children = row.children;
            env_names = children.env_names;
            env_values = children.env_values;
            services = children.services;
            uris = children.uris;
            for (var i = 0; i < uris.length; i++) {
                env_names[i] = "";
                env_values[i] = "";
            }
            this._spliceNullEnds([uris, services, env_names, env_values]);
            if (row.state == xtk.hierarchicalTreeView.STATE_OPENED) {
                this.doToggleOpenState(index);
                this.doToggleOpenState(index);
            }
        }
};

this.ApplicationsTree.prototype.sortRows = function(a, b) {
    return cmpFieldsOverNames(a.fields, b.fields,
                              ['name', 'health', 'num_instances', 'serviceName', 'url']);
};

this.ApplicationsTree.prototype.getNames = function() {
    return this._rows.map(function(a) a.fields["name"]).
                      filter(function(b) b);
};

this.ApplicationsTree.prototype.getURLs = function(appName) {
    return this._rows.map(function(a) a.fields["url"]).
                      filter(function(b) b);
};

this.ApplicationsTree.prototype.getParticularFieldForApp = function(appName, fieldName) {
    var hits = [], data, i, lim = this._rows.length, collectHits = false;
    for (i = 0; i < lim; i++) {
        data = this._rows[i].fields;
        if (data.name) {
            if (collectHits) {
                break;
            } else if (data.name == appName) {
                collectHits = true;
                hits.push(data[fieldName]);
            }
        } else if (collectHits) {
            hits.push(data[fieldName]);
        }
    }
    return hits;
};

this.ApplicationsTree.prototype.getURLsForApp = function(appName) {
    return this.getParticularFieldForApp(appName, "url");
};

this.ApplicationsTree.prototype.getServicesForApp = function(appName) {
    return this.getParticularFieldForApp(appName, "serviceName");
};

this.ApplicationsTree.prototype.getAppForServiceName = function(serviceName) {
    for each (var row in this._rows) {
            if (row.level == 0) {
                if (row.fields.serviceName == serviceName
                    || (row.isContainer
                        && row.children.services.indexOf(serviceName) != -1)) {
                    return row.fields.name;
                }
            }
        }
    return null;
};

this.ApplicationsTree.prototype.getMainRow = function(idx) {
    // In case the user clicked on a child row of a main row,
    // work our way up to the app.  Throw an exception if idx < 0 (unlikely).
    var i, data;
    for (i = idx; i >= 0; i--) {
        data = this._rows[i].fields;
        if (data.name) {
            return this._rows[i];
        }
    }
    throw new Error("No main row for index " + idx);
};

this.ApplicationsTree.prototype.getMainRowForApp = function(appName) {
    var i, row;
    var lim = this._rows.length;
    for (i = 0; i < lim; i++) {
        row = this._rows[i];
        if (row.fields.name == appName) {
            return [i, row];
        }
    }
    throw new Error("No main row for appName " + appName);
};

this.ApplicationsTree.prototype.getAppNameForRow = function(idx) {
    return this.getMainRow(idx).fields.name;
};

this.ApplicationsTree.prototype._evenOut = function(arraySet) {
    var lengths = arraySet.map(function(a) a.length);
    var maxLen = lengths.reduce(function(accum, value) value > accum ? value : accum);
    var i, lim = arraySet.length, a, diff;
    for (i = 0; i < lim; i++) {
        a = arraySet[i];
        diff = maxLen - lengths[i];
        for (; diff > 0; --diff) {
            a.push("");
        }
    }
    this._spliceNullEnds(arraySet);
};

this.ApplicationsTree.prototype._spliceNullEnds = function(arraySet) {
    var i, j, k, numArrays = arraySet.length, len, a, diff, nullStart = -1;
    var len = arraySet[0].length; // assume all items are the same length;
    for (i = len - 1; i >= 0; i--) {
        for (j = 0; j < numArrays; j++) {
            if (arraySet[j][i]) {
                if (i < len - 1) {
                    arraySet.forEach(function(a) a.splice(i + 1));
                }
                return;
            }
        }
    }
    // If all the first items are empty, zap them all
    if (!arraySet.some(function(a) a[0])) {
        arraySet.forEach(function(a) a.splice(0));
    }
        
};

this.ApplicationsTree.prototype.doToggleOpenState = function(index) {
    // bypass setting the pref.
    xtk.hierarchicalTreeView.prototype.toggleOpenState.call(this, index);
};

this.ApplicationsTree.prototype.toggleOpenState = function(index) {
    xtk.hierarchicalTreeView.prototype.toggleOpenState.call(this, index);
    var row = this._rows[index];
    var appName = row.fields.name;
    var appPrefs = gStackatoPrefs.getPref("apps");
    if (appPrefs.hasPref(appName)) {
        appPrefs.getPref(appName).setLongPref("row.state", row.state);
    }
};

/////////////////////////////////////////////////////////////////////////////

this.ServicesTree = function() {
    ko.stackato.trees.GenericTree.apply(this);
    this.treeName = ""
};
this.ServicesTree.prototype = new this.GenericTree();
this.ServicesTree.prototype.contructor = this.ServicesTree;
this.ServicesTree.prototype.sortRows = function(a, b) {
    var fieldNames = [gCurrTree.treeName + '_name',
                      gCurrTree.treeName + '_type',
                      gCurrTree.treeName + '_version'];
    var descName = gCurrTree.treeName + '_description';
    if (descName in a.fields) {
        fieldNames.push(descName);
    }
    return cmpFieldsOverNames(a.fields, b.fields, fieldNames);
};


this.ServicesSystemTree = function() {
    ko.stackato.trees.ServicesTree.apply(this);
    this.treeName = "servicesSystemTree"
};
this.ServicesSystemTree.prototype = new this.ServicesTree();
this.ServicesSystemTree.prototype.contructor = this.ServicesSystemTree;
this.ServicesSystemTree.prototype.setData = function(data) {
    var newRow, rows = [];
    for (var dbTypeName in data) { // keys: 'key-value', 'database'
        var dbTypeSet = data[dbTypeName];
        for (var dbName in dbTypeSet) { // keys: 'mongodb', 'postgresql', etc.
            var dbNameSet = dbTypeSet[dbName];
            for (var versionName in dbNameSet) { // keys: '1.8', etc.
                var versionValue = dbNameSet[versionName];
                newRow = new ko.stackato.trees.ApplicationRow(0);
                newRow.fields = {};
                newRow.fields[this.treeName + '_name'] = versionValue.vendor;
                newRow.fields[this.treeName + '_type'] = versionValue.type;
                newRow.fields[this.treeName + '_version'] = versionValue.version;
                newRow.fields[this.treeName + '_description'] = versionValue.description;
                rows.push(newRow);
            }
        }
    }
    gCurrTree = this; // js hack
    rows.sort(this.sortRows);
    this.setTreeRows(rows);
};


this.ServicesProvisionedTree = function() {
    ko.stackato.trees.ServicesTree.apply(this);
    this.treeName = "servicesProvisionedTree";
};
this.ServicesProvisionedTree.prototype = new this.ServicesTree();
this.ServicesProvisionedTree.prototype.contructor = this.ServicesProvisionedTree;

this.ServicesProvisionedTree.prototype.setData = function(data) {
    var newRow, rows = [];
    for each (var item in data) {
        newRow = new ko.stackato.trees.ApplicationRow(0);
        newRow.fields = {};
        newRow.fields[this.treeName + '_name'] = item.name;
        newRow.fields[this.treeName + '_type'] = item.type;
        newRow.fields[this.treeName + '_version'] = item.version;
        newRow.fields[this.treeName + '_vendor'] = item.vendor;
        rows.push(newRow);
    }
    gCurrTree = this; // js hack
    rows.sort(this.sortRows);
    this.setTreeRows(rows);
};

this.ServicesTreeManager = function() {
    this.servicesProvisionedTree = new ko.stackato.trees.ServicesProvisionedTree();
    this.servicesSystemTree =      new ko.stackato.trees.ServicesSystemTree();
};

this.ServicesTreeManager.prototype = {
    setData: function(results) {
        this.servicesProvisionedTree.setData(results.provisioned);
        this.servicesSystemTree.setData(results.system);
    },
    __EOF__: null
};

/////////////////////////////////////////////////////////////////////////////

this.FrameworksTree = function() {
    ko.stackato.trees.GenericTree.apply(this);
    this.treeName = "frameworksTree";
};
this.FrameworksTree.prototype = new this.GenericTree();
this.FrameworksTree.prototype.contructor = this.FrameworksTree;

this.FrameworksTree.prototype.setData =  function(results) {
    var newRow, rows = [];
    var names;
    // The format of 'stackato frameworks --json' changed going
    // into client version 1.2
    if (('length' in results) && (0 in results)) {
        names = results;
    } else {
        names = [];
        for (var p in results) {
            names.push(p);
        }
    }
    for each (var item in names) {
        newRow = new ko.stackato.trees.ApplicationRow(0);
        newRow.fields = {
            'frameworksTree_name': item
        };
        rows.push(newRow);
    }
    rows.sort(this.sortRows);
    this.setTreeRows(rows);
};

this.FrameworksTree.prototype.sortRows = function(a, b) {
    return cmpFieldsOverNames(a.fields, b.fields, ['frameworksTree_name']);
};

/////////////////////////////////////////////////////////////////////////////

this.RuntimesTree = function() {
    ko.stackato.trees.GenericTree.apply(this);
    this.treeName = "runtimesTree";
};
this.RuntimesTree.prototype = new this.GenericTree();
this.RuntimesTree.prototype.contructor = this.RuntimesTree;

this.RuntimesTree.prototype.setData =  function(data) {
    var item, newRow, runtimeName, rows = [];
    for (runtimeName in data) {
        item  = data[runtimeName];
        newRow = new ko.stackato.trees.ApplicationRow(0);
        newRow.fields = {};
        newRow.fields[this.treeName + '_name'] = item.name;
        newRow.fields[this.treeName + '_description'] = item.description;
        newRow.fields[this.treeName + '_version'] = item.version
        rows.push(newRow);
    }
    gCurrTree = this;
    rows.sort(this.sortRows);
    this.setTreeRows(rows);
};

this.RuntimesTree.prototype.sortRows = function(a, b) {
    return cmpFieldsOverNames(a.fields, b.fields,
                              [gCurrTree.treeName + '_name',
                               gCurrTree.treeName + '_version',
                               gCurrTree.treeName + '_description']);
};

this.RuntimesTree.prototype.getRuntimeNames = function() {
    var name = this.treeName + "_name";
    return this._rows.map(function(a) a.fields[name]);
};

/////////////////////////////////////////////////////////////////////////////

this.TargetsTree = function() {
    ko.stackato.trees.GenericTree.apply(this);
    this.treeName = "targetsTree";
};
this.TargetsTree.prototype = new this.GenericTree();
this.TargetsTree.prototype.contructor = this.TargetsTree;

this.TargetsTree.prototype.setData =  function(data) {
    var target, authKey, newRow, rows = [];
    for (target in data) {
        newRow = new ko.stackato.trees.ApplicationRow(0);
        newRow.fields = {};
        newRow.fields[this.treeName + '_target'] = target;
        newRow.fields[this.treeName + '_authorization'] = data[target];
        rows.push(newRow);
    }
    gCurrTree = this;
    rows.sort(this.sortRows);
    this.setTreeRows(rows);
};

this.TargetsTree.prototype.sortRows = function(a, b) {
    return cmpFieldsOverNames(a.fields, b.fields,
                              [gCurrTree.treeName + '_target',
                               gCurrTree.treeName + '_authorization']);
};

this.TargetsTree.prototype.getTargetNames = function() {
    var name = this.treeName + "_target";
    return this._rows.map(function(a) a.fields[name]);
};

/////////////////////////////////////////////////////////////////////////////

}).apply(ko.stackato.trees);

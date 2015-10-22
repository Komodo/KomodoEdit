/* Copyright (c) 2000-2006 ActiveState Software Inc.

/* Use this sample to explore editing JavaScript with Komodo. */

function myfunc() {
    this.classVar1 = "MyFunc";
}

myfunc.prototype.list = function()
{
    // Do whatever you do
}

myfunc.prototype.strFunc = function(s /* s is a string */)
{
    var copyOfS = s;
    if (this.classVar1 == s) {
        this.classVar1 = copyOfS;
    }
    // Do whatever you do
}

var mf = new myfunc();
var s = mf.classVar1;
mf.list();
mf.strFunc(s);

// This is our custom view, based on the treeview interface
function treeView(table,columns,rowcount)
{
    this.table               = table;    // our table
    this.columns             = columns;  // our cols
    this.rowCount            = rowcount; // our counter
    this.treebox             = null;
    this.getCellText         = function(row,column){ return this.table[row][this.columns[column][0]]; };
    // Watch this, it thinks this is a subclass as treebox is not defined yet
    this.setTree             = function(treebox){ this.treebox=treebox; };
    this.isContainer         = function(row){ return false; };
    this.isSeparator         = function(row){ return false; };
    this.isSorted            = function(row){ return false; };
    this.getLevel            = function(row){ return 0; };
    this.getImageSrc         = function(row,col){ return null; };
    this.getRowProperties    = function(row,props){};
    this.getCellProperties   = function(row,col,props){};
    this.getColumnProperties = function(colid,col,props){};
}

//Moz 1.8
var treeView2 = {
    rowCount : 10000,
    treebox : null,
    getCellText : function(row,column){
      if (column.id == "namecol") return "Row "+row;
      else return "February 18";
    },
    setTree: function(treebox){ this.treebox = treebox; },
    isContainer: function(row){ return false; },
    isSeparator: function(row){ return false; },
    isSorted: function(){ return false; },
    getLevel: function(row){ return 0; },
    getImageSrc: function(row,col){ return null; },
    getRowProperties: function(row,props){},
    getCellProperties: function(row,col,props){},
    getColumnProperties: function(colid,col,props){}
};

var partTreeView = {
    setTree: function(treebox){ this.treebox = treebox; },
    isContainer: function(row){ return false; },
    isSeparator: function(row){ return false; },
    isSorted: function(){ return false; }
};


// This should be same as assigning a variable name
// aDict and aDict2 should be exactly the same
// TM: Do not turn into class... punt
var aDict = {
    "element1": [ 1, "one" ],
    "element2": [ 2, "two" ],
    "element3": [ 3, "three" ]
};
// TM: Punting for now (turn into a variable with internal class)
/*
 <variable name="partTreeView">
    <class>
        <function name="setTree" .../>
        ...
    </class>
 </variable>
*/
var aDict2 = {
    element1: [ 1, "one" ],
    element2: [ 2, "two" ],
    element3: [ 3, "three" ]
};

// Code Folding:
//   - Click the "-" and "+" symbols in the left margin.
//   - Use View/Fold to collapse or expand all blocks.

// Syntax Coloring:
//   - Language elements are colored according to the Fonts and Colors
//     preference.

// Background Syntax Checking:
//   - Syntax errors are underlined in red.
//   - Syntax warnings are underlined in green.
//   - Position the cursor over the underline to view the error or warning
//     message.

// Code Browsing:
//   1. If necesssary, enable Komodo's code intelligence (Edit|Preferences|Code Intelligence).
//   2. Select View|Tabs|Code Browser.
//   3. On the Code tab, click the plus sign next to "javascript_sample.js".
//   4. If necessary, display the Code Description pane by clicking the
//      "Show/Hide Description" button at the bottom of the Code Browser.
//   5. Select "validateForm". The Code Description pane indicates that the file
//      contains one function, validateForm(form).

// More:
//   - Press 'F1' to view the Komodo User Guide.


function otherfunc() {
    this.classVar2 = "OtherFunc";
}

// Defining function prototype for different class
myfunc.prototype.separateFunc = function()
{
    // Do whatever you do
}

// Similar to myfunc.prototype.strFunc
otherfunc.prototype.strFunc = function(s /* s is a string */)
{
    var copyOfS = s;
    if (this.classVar2 == s) {
        this.classVar2 = copyOfS;
    }
    // Do whatever you do
}

var _of = new otherfunc();
var s2 = _of.classVar2;
_of.list();
_of.strFunc(s2);

var foo = function() { };


/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */

// Globals
Components.utils.import("resource://gre/modules/Services.jsm");

const nsIScriptableDateFormat = Components.interfaces.nsIScriptableDateFormat;
const nsScriptableDateFormat_CONTRACTID = "@mozilla.org/intl/scriptabledateformat;1";
const nsIAtomService = Components.interfaces.nsIAtomService;
const nsAtomService_CONTRACTID = "@mozilla.org/atom-service;1";

var gDateService = null;

function numMatchingChars(str1, str2) {
  var minLength = Math.min(str1.length, str2.length);
  for (var i = 0; ((i < minLength) && (str1[i] == str2[i])); i++);
  return i;
}

function sortFilename(a, b) {
  if (a.cachedName < b.cachedName) {
    return -1;
  } else {
    return 1;
  }
}

function sortSize(a, b) {
  if (parseInt(a.cachedSize) < parseInt(b.cachedSize)) {
    return -1;
  } else if (parseInt(a.cachedSize) > parseInt(b.cachedSize)) {
    return 1;
  } else {
    return 0;
  }
}

function sortDate(a, b) {
  if (a.cachedDate < b.cachedDate) {
    return -1;
  } else if (a.cachedDate > b.cachedDate) {
    return 1;
  } else {
    return 0;
  }
}

function formatDate(date) {
  if (date > (4000000000000)) {
    // Year is greater than 2096 - bug 82484.
    return "(Unknown date)";
  }
  var modDate = new Date(date);
    if (!modDate.getFullYear()) return 0;
  return gDateService.FormatDateTime("", gDateService.dateFormatShort,
                                     gDateService.timeFormatSeconds,
                                     modDate.getFullYear(), modDate.getMonth()+1,
                                     modDate.getDate(), modDate.getHours(),
                                     modDate.getMinutes(), modDate.getSeconds());
}

function filebrowseview() {
  this.mSingleSelect = false;
  this.mShowHiddenFiles = false;
  this.mDirectoryFilter = false;
  this.mFileList = [];
  this.mDirList = [];
  this.mFilteredFiles = [];
  this.mCurrentFilter = ".*";
  /* mNotifySelectionChanges - internal variable to allow the tree to       */
  /*                           temporarily disable selection notifications. */
  this.mNotifySelectionChanges = true;
  this.mSelection = null;
  this.mSelectionCallback = null;
  this.mTree = null;
  this.mReverseSort = false;
  this.mSortType = 0;
  this.mTotalRows = 0;

  if (!gDateService) {
    gDateService = Components.classes[nsScriptableDateFormat_CONTRACTID]
      .getService(nsIScriptableDateFormat);
  }

  var atomService = Components.classes[nsAtomService_CONTRACTID]
                      .getService(nsIAtomService);
  this.mDirectoryAtom = atomService.getAtom("remotefolder");
  this.mFileAtom = atomService.getAtom("remotefile");

  // Mozilla 22 changed the way tree properties work.
  if ((parseInt(Services.appinfo.platformVersion)) < 22) {
    this.getCellProperties = this.getCellPropertiesMoz21AndOlder;
  }
}

/* class constants */

filebrowseview.SORTTYPE_NAME = 1;
filebrowseview.SORTTYPE_SIZE = 2;
filebrowseview.SORTTYPE_DATE = 3;

filebrowseview.prototype = {

  /* readonly attribute long rowCount; */
  set rowCount(c) { throw new Error("readonly property"); },
  get rowCount() { return this.mTotalRows; },

  /* attribute nsITreeSelection selection; */
  set selection(s) { this.mSelection = s; },
  get selection() { return this.mSelection; },

  set selectionCallback(f) { this.mSelectionCallback = f; },
  get selectionCallback() { return this.mSelectionCallback; },

  set singleSelect(f) { this.mSingleSelect = f; },
  get singleSelect() { return this.mSingleSelect; },

  /* nsISupports methods */

  /* void QueryInterface(in nsIIDRef uuid,
     [iid_is(uuid),retval] out nsQIResult result); */
  QueryInterface: function(iid) {
    if (!iid.equals(Components.interfaces.nsITreeView) &&
        !iid.equals(Components.interfaces.nsISupports)) {
          throw Components.results.NS_ERROR_NO_INTERFACE;
        }
    return this;
  },

  /* nsITreeView methods */

  /* void getRowProperties(in long index, in nsISupportsArray properties); */
  getRowProperties: function(index, properties) { },

  /* void getCellProperties(in long row, in DOMElement column); */
  getCellProperties: function(row, column) {
    if (column.id != "FilenameColumn")
      return;
    if (row < this.mDirList.length)
      return "remotefolder";
    else if ((row - this.mDirList.length) < this.mFilteredFiles.length)
      return "remotefile";
  },

  /* void getCellProperties(in long row, in wstring colID, in nsISupportsArray properties); */
  getCellPropertiesMoz21AndOlder: function(row, column, properties) {
    if (column.id != "FilenameColumn")
      return;
    if (row < this.mDirList.length)
      properties.AppendElement(this.mDirectoryAtom);
    else if ((row - this.mDirList.length) < this.mFilteredFiles.length)
      properties.AppendElement(this.mFileAtom);
  },

  /* void getColumnProperties(in wstring colID, in nsIDOMElement colElt,
     in nsISupportsArray properties); */
  getColumnProperties: function(colID, colElt, properties) { },

  /* boolean isContainer(in long index); */
  isContainer: function(index) { return false; },

  /* boolean isContainerOpen(in long index); */
  isContainerOpen: function(index) { return false;},

  /* boolean isContainerEmpty(in long index); */
  isContainerEmpty: function(index) { return false; },

  /* boolean isSorted (); */
  isSorted: function() { return (this.mSortType > 0); },

  /* boolean canDrop (in long index, in long orientation); */
  canDrop: function(index, orientation) { return false; },

  /* void drop (in long row, in long orientation); */
  drop: function(row, orientation) { },

  /* long getParentIndex(in long rowIndex); */
  getParentIndex: function(rowIndex) { return -1; },

  /* boolean hasNextSibling(in long rowIndex, in long afterIndex); */
  hasNextSibling: function(rowIndex, afterIndex) {
    return (afterIndex < (this.mTotalRows - 1));
  },

  /* long getLevel(in long index); */
  getLevel: function(index) { return 0; },

  /* boolean isSeparator(in long index); */
  isSeparator: function(index) { return 0; },

  /* wstring getCellText(in long row, in wstring colID); */
  getCellText: function(row, column) {
    var colID = column.id;
    /* we cache the file size and last modified dates -
       this function must be very fast since it's called
       whenever the cell needs repainted */
    var file, isdir = false;
    if (row < this.mDirList.length) {
      isdir = true;
      file = this.mDirList[row];
    } else if ((row - this.mDirList.length) < this.mFilteredFiles.length) {
      file = this.mFilteredFiles[row - this.mDirList.length];
    } else {
      return "";
    }

    if (colID == "FilenameColumn") {
      if (!("cachedName" in file)) {
        file.cachedName = file.file.leafName;
      }
      return file.cachedName;
    } else if (colID == "LastModifiedColumn") {
      if (!("cachedDate" in file)) {
        // perhaps overkill, but lets get the right locale handling
        file.cachedDate = file.file.lastModifiedTime;
        file.cachedDateText = formatDate(file.cachedDate);
      }
      return file.cachedDateText;
    } else if (colID == "FileSizeColumn") {
      if (isdir) {
        return "";
      } else {
        if (!("cachedSize" in file)) {
          file.cachedSize = String(file.file.fileSize);
        }
      }
      return file.cachedSize;
    }
    return "";
  },

  /* void setTree(in nsITreeBoxObject tree); */
  setTree: function(tree) { this.mTree = tree; },

  /* void toggleOpenState(in long index); */
  toggleOpenState: function(index) { },

  /* void cycleHeader(in wstring colID, in nsIDOMElement elt); */
  cycleHeader: function(colID, elt) { },

  /* void selectionChanged(); */
  selectionChanged: function() {
    if (this.mNotifySelectionChanges && this.mSelectionCallback) {
        var fileList = this.getSelectedFiles();
        this.mSelectionCallback(fileList);
    }
  },

  /* void cycleCell(in long row, in wstring colID); */
  cycleCell: function(row, colID) { },

  /* boolean isEditable(in long row, in wstring colID); */
  isEditable: function(row, colID) {
      return false;
  },

  /* void setCellText(in long row, in wstring colID, in wstring value); */
  setCellText: function(row, colID, value) {},

  /* void performAction(in wstring action); */
  performAction: function(action) { },

  /* void performActionOnRow(in wstring action, in long row); */
  performActionOnRow: function(action, row) { },

  /* void performActionOnCell(in wstring action, in long row, in wstring colID); */
  performActionOnCell: function(action, row, colID) { },

  /* AString getImageSrc(in long row, in wstring colID); */
  getImageSrc: function(row, colID) {},

  /* private attributes */

  /* attribute boolean showHiddenFiles */
  set showHiddenFiles(s) {
    this.mShowHiddenFiles = s;
    this.setDirectory(this.mDirectoryPath);
  },

  get showHiddenFiles() { return this.mShowHiddenFiles; },

  /* attribute boolean showOnlyDirectories */
  set showOnlyDirectories(s) {
    this.mDirectoryFilter = s;
    this.filterFiles();
  },

  get showOnlyDirectories() { return this.mDirectoryFilter; },

  /* readonly attribute short sortType */
  set sortType(s) { throw new Error("readonly property"); },
  get sortType() { return this.mSortType; },

  /* readonly attribute boolean reverseSort */
  set reverseSort(s) { throw new Error("readonly property"); },
  get reverseSort() { return this.mReverseSort; },

  /* private methods */
  sort: function(sortType, reverseSort, forceSort) {
    if (sortType == this.mSortType && reverseSort != this.mReverseSort && !forceSort) {
      this.mDirList.reverse();
      this.mFilteredFiles.reverse();
    } else {
      var compareFunc, i;

      /* We pre-fetch all the data we are going to sort on, to avoid
         calling into C++ on every comparison */

      switch (sortType) {
      case 0:
        /* no sort has been set yet */
        return;
      case filebrowseview.SORTTYPE_NAME:
        for (i = 0; i < this.mDirList.length; i++) {
          if (!this.mDirList[i].cachedName) this.mDirList[i].cachedName = this.mDirList[i].file.leafName;
        }
        for (i = 0; i < this.mFilteredFiles.length; i++) {
          if (!this.mFilteredFiles[i].cachedName) this.mFilteredFiles[i].cachedName = this.mFilteredFiles[i].file.leafName;
        }
        compareFunc = sortFilename;
        break;
      case filebrowseview.SORTTYPE_SIZE:
        for (i = 0; i < this.mDirList.length; i++) {
          if (!this.mDirList[i].cachedSize) this.mDirList[i].cachedSize = this.mDirList[i].file.fileSize;
        }
        for (i = 0; i < this.mFilteredFiles.length; i++) {
          if (!this.mFilteredFiles[i].cachedSize) this.mFilteredFiles[i].cachedSize = this.mFilteredFiles[i].file.fileSize;
        }
        compareFunc = sortSize;
        break;
      case filebrowseview.SORTTYPE_DATE:
        for (i = 0; i < this.mDirList.length; i++) {
            if (!this.mDirList[i].cachedDate) {
              this.mDirList[i].cachedDate = this.mDirList[i].file.lastModifiedTime;
              this.mDirList[i].cachedDateText = formatDate(this.mDirList[i].cachedDate);
            }
        }
        for (i = 0; i < this.mFilteredFiles.length; i++) {
            if (!this.mFilteredFiles[i].cachedDate) {
              this.mFilteredFiles[i].cachedDate = this.mFilteredFiles[i].file.lastModifiedTime;
              this.mFilteredFiles[i].cachedDateText = formatDate(this.mFilteredFiles[i].cachedDate);
            }
        }
        compareFunc = sortDate;
        break;
      default:
        throw new Error("Unsupported sort type " + sortType);
        break;
      }
      this.mDirList.sort(compareFunc);
      this.mFilteredFiles.sort(compareFunc);
    }

    this.mSortType = sortType;
    this.mReverseSort = reverseSort;
    if (this.mTree) {
      this.mTree.beginUpdateBatch();
      this.mTree.invalidate();
      this.mTree.endUpdateBatch();
    }
  },
  rowCountChanged: function(start, newsize) {
    this.mTree.beginUpdateBatch();
    this.mTree.rowCountChanged(start, newsize);
    this.mTree.invalidate();
    this.mTree.endUpdateBatch();
  },
  clearList: function() {
    this.mDirectoryPath = "";
    this.mFileList = [];
    this.mDirList = [];
    this.mFilteredFiles = [];
    this.rowCountChanged(0,0);
  },
  setDirectory: function(directory) {
    var dir = newFile(directory)
    // An error has occured if newFile returns null
    if (dir) {
      this.mDirectoryPath = directory;
      this.mFileList = [];
      this.mDirList = [];
  
      dir.followLinks = false;
      dir.init(directory);
      this.mDirList = dir.directories; // XXX this.mShowHiddenFiles
  
      if (!this.mDirectoryFilter) this.mFileList = dir._filelist;
  
      //time = new Date() - time;
      //dump("load time: " + time/1000 + " seconds\n");
  
      this.mFilteredFiles = [];
  
      if (this.mTree) {
        var oldRows = this.mTotalRows;
        this.mTotalRows = this.mDirList.length;
        if (this.mDirList.length != oldRows) {
          this.rowCountChanged(0, this.mDirList.length - oldRows);
        }
      }
  
      //time = new Date();
  
      this.filterFiles();
  
      //time = new Date() - time;
      //dump("filter time: " + time/1000 + " seconds\n");
      //time = new Date();
  
      this.sort(this.mSortType, this.mReverseSort);
  
      //time = new Date() - time;
      //dump("sort time: " + time/1000 + " seconds\n");

      this.unSelectAll();
      this.mTree.scrollToRow(0);
    }
  },

  setFilter: function(filter) {
    // The filter may contain several components, i.e.:
    // *.html; *.htm
    // First separate it into its components
    var filterList = filter.split(/;[ ]*/);

    if (filterList.length == 0) {
      // this shouldn't happen
      return;
    }

    // Transform everything in the array to a regexp
    var filterStr = "";
    for (var i = 0; i < filterList.length; i++) {
      // * becomes .*, and we escape all .'s with \
      if (filterList[i] == "*.*") {
          filterList[i] = ".*";
      } else {
          var tmp = filterList[i].replace(/\./g, "\\.");
          filterList[i] = tmp.replace(/\*/g, ".*");
          //shortestPrefix = shortestPrefix.substr(0, numMatchingChars(shortestPrefix, filterList[i]));
      }
      filterStr += "("+filterList[i]+")";
      if (i < filterList.length -1) { filterStr += "|"; }
    }
    //filterStr += "/";

    this.mCurrentFilter = new RegExp(filterStr, "i");
    this.mFilteredFiles = [];

    if (this.mTree) {
      var rowDiff = -(this.mTotalRows - this.mDirList.length);
      this.mTotalRows = this.mDirList.length;
      this.rowCountChanged(this.mDirList.length, rowDiff);
    }
    this.filterFiles();
    this.sort(this.mSortType, this.mReverseSort, true);
  },

  filterFiles: function() {
    for(var i = 0; i < this.mFileList.length; i++) {
      var file = this.mFileList[i];
      var leafName = file.file.leafName;
      if (/*(this.mShowHiddenFiles || !file.file.isHidden) &&*/ this.mCurrentFilter.test(leafName)) {
          //leafName.search(this.mCurrentFilter) == 0) {
        this.mFilteredFiles[this.mFilteredFiles.length] = file; //{ file : file };
      }
    }

    this.mTotalRows = this.mDirList.length + this.mFilteredFiles.length;

    // Tell the tree how many rows we just added
    if (this.mTree) {
      this.mTree.rowCountChanged(this.mDirList.length, this.mFilteredFiles.length);
    }
  },
  selectEntryByNameType: function(name, isDir) {
      var start = 0;
      var tree = document.getElementById("directoryTree");
      if (!isDir) start = this.mDirList.length;
        for (var index=start; index < this.mTotalRows; index++) {
            if (isDir && index < this.mDirList.length) {
                if (name == this.mDirList[index].file.leafName) {
                    this.mSelection.select(index);
                    tree.treeBoxObject.scrollToRow(index);
                    return true;
                }
            } else if (!isDir && (index - this.mDirList.length) < this.mFilteredFiles.length) {
                if (name == this.mFilteredFiles[index - this.mDirList.length].file.leafName) {
                    this.mSelection.select(index);
                    tree.treeBoxObject.scrollToRow(index);
                    return true;
                }
            }
        }
      return false;
  },
  getSelectedFile: function() {
    if (0 <= this.mSelection.currentIndex) {
      if (this.mSelection.currentIndex < this.mDirList.length) {
        return this.mDirList[this.mSelection.currentIndex].file;
      } else if ((this.mSelection.currentIndex - this.mDirList.length) < this.mFilteredFiles.length) {
        return this.mFilteredFiles[this.mSelection.currentIndex - this.mDirList.length].file;
      }
    }

    return null;
  },
  getSelectedFiles: function() {
    var fileList = new Array();
    if (this.mSelection.currentIndex < 0) {
      return fileList;
    }
    var currentFile = this.getSelectedFile();
    var haveDir = false;
    // only allow one directory selection
    if (this.mSingleSelect || (currentFile && currentFile.isDirectory)) {
        // deselect all other selections except the current one
        if (currentFile) {
            this.mSelection.select(this.mSelection.currentIndex);
            fileList.push(currentFile);
        }
    } else {
        for (var index=0; index < this.mTotalRows; index++) {
            if (this.mSelection.isSelected(index)) {
                if (index < this.mDirList.length) {
                    fileList.push(this.mDirList[index].file);
                    haveDir = true;
                } else if ((index - this.mDirList.length) < this.mFilteredFiles.length) {
                    // we can only select files or directories, not both
                    if (haveDir) {
                        // deselect this entry
                        this.mSelection.toggleSelect(index);
                    } else {
                        fileList.push(this.mFilteredFiles[index - this.mDirList.length].file);
                    }
                }
            }
        }
    }
    return fileList;
  },
  unSelectAll: function() {
    this.mNotifySelectionChanges = false;
    try {
        this.mSelection.clearSelection();
        // Need to also reset the currentIndex.
        this.mSelection.currentIndex = -1;
    } finally {
        this.mNotifySelectionChanges = true;
    }
  }
}


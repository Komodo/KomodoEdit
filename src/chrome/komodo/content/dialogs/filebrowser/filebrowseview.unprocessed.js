/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

// Globals
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
}

/* class constants */

filebrowseview.SORTTYPE_NAME = 1;
filebrowseview.SORTTYPE_SIZE = 2;
filebrowseview.SORTTYPE_DATE = 3;

filebrowseview.prototype = {

  /* readonly attribute long rowCount; */
  set rowCount(c) { throw "readonly property"; },
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
    if (!iid.equals(nsITreeView) &&
        !iid.equals(nsISupports)) {
          throw Components.results.NS_ERROR_NO_INTERFACE;
        }
    return this;
  },

  /* nsITreeView methods */

  /* void getRowProperties(in long index, in nsISupportsArray properties); */
  getRowProperties: function(index, properties) { },

  /* void getCellProperties(in long row, in wstring colID, in nsISupportsArray properties); */
  getCellProperties: function(row, column, properties) {
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

    if (column.id == "FilenameColumn") {
      if (!("cachedName" in file)) {
        file.cachedName = file.file.leafName;
      }
      return file.cachedName;
    } else if (column.id == "LastModifiedColumn") {
      if (!("cachedDate" in file)) {
        // perhaps overkill, but lets get the right locale handling
        file.cachedDate = file.file.lastModifiedTime;
        file.cachedDateText = formatDate(file.cachedDate);
      }
      return file.cachedDateText;
    } else if (column.id == "FileSizeColumn") {
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
    if (this.mSelectionCallback) {
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
  set sortType(s) { throw "readonly property"; },
  get sortType() { return this.mSortType; },

  /* readonly attribute boolean reverseSort */
  set reverseSort(s) { throw "readonly property"; },
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
        throw("Unsupported sort type " + sortType);
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
    // This function is used to make sure all tree items are unselected.
    // Just setting the currentIndex to -1 does not work, as some items
    // will still be highlighted.
    // XXX - I think this tree view is a little buggy - ToddW.
    for (var index=0; index < this.mTotalRows; index++) {
        if (this.mSelection.isSelected(index)) {
            this.mSelection.toggleSelect(index);
        }
    }
    this.mSelection.currentIndex = -1;
  }
}


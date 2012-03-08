/**
 * Fake nsITreeBoxObject
 */

function TreeColumns() {}

function TreeBoxObject(aView) {
    this.columns = new TreeColumns();
    this.view = aView;
    this.focused = false;
    this.treeBody = null;
    this.rowHeight = 1;
    this.rowWidth = 1;
    this.horizontalPosition = 0;
    this.selectionRegion = null;
}

TreeBoxObject.prototype.getFirstVisibleRow =
function TreeBoxObject_getFirstVisibleRow() {
};

TreeBoxObject.prototype.getLastVisibleRow =
function TreeBoxObject_getLastVisibleRow() {
};

TreeBoxObject.prototype.getPageLength =
function TreeBoxObject_getPageLength() {
};

TreeBoxObject.prototype.ensureRowIsVisible =
function TreeBoxObject_ensureRowIsVisible(index) {
};

TreeBoxObject.prototype.ensureCellIsVisible =
function TreeBoxObject_ensureCellIsVisible(row, col) {
};

TreeBoxObject.prototype.scrollToRow =
function TreeBoxObject_scrollToRow(index) {
};

TreeBoxObject.prototype.scrollByLines =
function TreeBoxObject_scrollByLines(numLines) {
};

TreeBoxObject.prototype.scrollByPages =
function TreeBoxObject_scrollByPages(numPages) {
};

TreeBoxObject.prototype.scrollToCell =
function TreeBoxObject_scrollToCell(row, col) {
};

TreeBoxObject.prototype.scrollToColumn =
function TreeBoxObject_scrollToColumn(col) {
};

TreeBoxObject.prototype.scrollToHorizontalPosition =
function TreeBoxObject_scrollToHorizontalPosition(horizontalPosition) {
};

TreeBoxObject.prototype.invalidate =
function TreeBoxObject_invalidate() {
};

TreeBoxObject.prototype.invalidateColumn =
function TreeBoxObject_invalidateColumn(col) {
};

TreeBoxObject.prototype.invalidateRow =
function TreeBoxObject_invalidateRow(index) {
};

TreeBoxObject.prototype.invalidateCell =
function TreeBoxObject_invalidateCell(row, col) {
};

TreeBoxObject.prototype.invalidateRange =
function TreeBoxObject_invalidateRange(startIndex, endIndex) {
};

TreeBoxObject.prototype.invalidateColumnRange =
function TreeBoxObject_invalidateColumnRange(startIndex, endIndex, col) {
};

TreeBoxObject.prototype.getRowAt =
function TreeBoxObject_getRowAt(x, y) {
};

TreeBoxObject.prototype.getCellAt =
function TreeBoxObject_getCellAt(x, y, row, col, childElt) {
};

TreeBoxObject.prototype.getCoordsForCellItem =
function TreeBoxObject_getCoordsForCellItem(row, col, element, x, y, width, height) {
};

TreeBoxObject.prototype.isCellCropped =
function TreeBoxObject_isCellCropped(row, col) {
};

TreeBoxObject.prototype.rowCountChanged =
function TreeBoxObject_rowCountChanged(index, count) {
};

TreeBoxObject.prototype.beginUpdateBatch =
function TreeBoxObject_beginUpdateBatch() {
};

TreeBoxObject.prototype.endUpdateBatch =
function TreeBoxObject_endUpdateBatch() {
};

TreeBoxObject.prototype.clearStyleAndImageCaches =
function TreeBoxObject_clearStyleAndImageCaches() {
};


ko.TreeBoxObject = TreeBoxObject;

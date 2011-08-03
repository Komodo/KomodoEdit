
xtk = {}
xtk.dataTreeView = function dataTreeView(initial_rows) {
    if (!initial_rows) {
        this._rows = [];
    } else {
        this._rows = initial_rows;
    }
}
xtk.dataTreeView.prototype = {
    setTreeRows : function(rows) {
        this._rows = rows;
    }
}

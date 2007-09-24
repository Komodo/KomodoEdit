// Enumerable.sortBy => this.map().sort().pluck()
var Enumerable = {
    sortBy: function(iterator) {
        return this.map(function(value, index) {
            return {value: value, criteria: iterator(value, index)};
        }).sort(function(left, right) {
            var a = left.criteria, b = right.criteria;
            return a < b ? -1 : a > b ? 1 : 0;
        }).pluck('value');
    }
}

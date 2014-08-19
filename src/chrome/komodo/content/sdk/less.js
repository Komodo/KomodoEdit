// Todo: Move less into its own dedicated module rather than wrapping it

var {Cu}  = require("chrome");
var {koLess} = Cu.import("chrome://komodo/content/library/less.js", {});
module.exports = koLess;

/**
 * You can access this module with:
 */
var vm = {};

/**
 * vm.runInThisContext() compiles code, runs it and returns the result.
 * Running code does not have access to local scope, but does have access
 * to the current global object.
 * @param code
 * @param options
 */
vm.runInThisContext = function(code, options) {}

/**
 * vm.runInNewContext compiles code, contextifies sandbox if passed or
 * creates a new contextified sandbox if it&#39;s omitted, and then runs
 * the code with the sandbox as the global object and returns the result.
 * @param code
 * @param sandbox
 * @param options
 */
vm.runInNewContext = function(code, sandbox, options) {}

/**
 * A class for holding precompiled scripts, and running them in specific
 * sandboxes.
 * @constructor
 */
vm.Script = function() {}

/**
 * Similar to vm.runInThisContext but a method of a precompiled Script
 * object.
 * @param options
 */
vm.Script.prototype.runInThisContext = function(options) {}

/**
 * Similar to vm.runInNewContext but a method of a precompiled Script
 * object.
 * @param sandbox
 * @param options
 */
vm.Script.prototype.runInNewContext = function(sandbox, options) {}

/**
 * Creating a new Script compiles code but does not run it. Instead, the
 * created vm.Script object represents this compiled code. This script can
 * be run later many times using methods below. The returned script is not
 * bound to any global object. It is bound before each run, just for that
 * run.
 * @param code
 * @param options
 */
vm.Script.prototype.Script = function(code, options) {}

/**
 * Similar to vm.runInContext but a method of a precompiled Script object.
 * @param contextifiedSandbox
 * @param options
 */
vm.Script.prototype.runInContext = function(contextifiedSandbox, options) {}

/**
 * If given a sandbox object, will "contextify" that sandbox so that it can
 * be used in calls to vm.runInContext or script.runInContext. Inside
 * scripts run as such, sandbox will be the global object, retaining all
 * its existing properties but also having the built-in objects and
 * functions any standard [global object][2] has. Outside of scripts run by
 * the vm module, sandbox will be unchanged.
 * @param sandbox
 */
vm.createContext = function(sandbox) {}

/**
 * Returns whether or not a sandbox object has been contextified by calling
 * vm.createContext on it.
 * @param sandbox
 * @returns whether or not a sandbox object has been contextified by calling vm.createContext on it
 */
vm.isContext = function(sandbox) {}

/**
 * vm.runInContext compiles code, then runs it in contextifiedSandbox and
 * returns the result. Running code does not have access to local scope.
 * The contextifiedSandbox object must have been previously contextified
 * via vm.createContext; it will be used as the global object for code.
 * @param code
 * @param contextifiedSandbox
 * @param options
 */
vm.runInContext = function(code, contextifiedSandbox, options) {}

/**
 * vm.runInDebugContext compiles and executes code inside the V8 debug
 * context.
 * @param code
 */
vm.runInDebugContext = function(code) {}

exports = vm;


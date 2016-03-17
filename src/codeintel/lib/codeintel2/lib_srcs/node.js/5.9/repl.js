/**
 * A Read-Eval-Print-Loop (REPL) is available both as a standalone program
 * and easily includable in other programs. The REPL provides a way to
 * interactively run JavaScript and see the results. It can be used for
 * debugging, testing, or just trying things out.
 */
var repl = {};

/**
 * Returns and starts a REPLServer instance, that inherits from [Readline
 * Interface][]. Accepts an "options" Object that takes the following
 * values:
 * @param options
 * @returns and starts a REPLServer instance, that inherits from Readline Interface
 */
repl.start = function(options) {}

/**
 * This inherits from [Readline Interface][] with the following events:
 * @constructor
 */
repl.REPLServer = function() {}

/**
 * Makes a command available in the REPL. The command is invoked by typing
 * a .
 * @param keyword {String}
 * @param cmd {Object|Function}
 */
repl.REPLServer.prototype.defineCommand = function(keyword, cmd) {}

/**
 * Like [readline.prompt][] except also adding indents with ellipses when
 * inside blocks. The preserveCursor argument is passed to
 * [readline.prompt][]. This is used primarily with defineCommand. It&#39;s
 * also used internally to render each prompt line.
 * @param preserveCursor {Boolean}
 */
repl.REPLServer.prototype.displayPrompt = function(preserveCursor) {}

/** @__local__ */ repl.REPLServer.__events__ = {};

/**
 * Emitted when the user exits the REPL in any of the defined ways. Namely,
 * typing .exit at the repl, pressing Ctrl+C twice to signal SIGINT, or
 * pressing Ctrl+D to signal &#39;end&#39; on the input stream. Example of
 * listening for exit:
 */
repl.REPLServer.__events__.exit = function() {};

/**
 * Emitted when the REPL&#39;s context is reset. This happens when you type
 * .clear. If you start the repl with { useGlobal: true } then this event
 * will never be emitted. Example of listening for reset:
 * @param context
 */
repl.REPLServer.__events__.reset = function(context) {};

exports = repl;


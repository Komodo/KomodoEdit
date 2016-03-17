/**
 * This module contains utilities for handling and transforming file paths.
 * Almost all these methods perform only string transformations.
 */
var path = {};

/**
 * Normalize a string path, taking care of &#39;..&#39; and &#39;.&#39;
 * parts.
 * @param p
 */
path.normalize = function(p) {}

/**
 * Resolves to to an absolute path.
 * @param from 
 * @param to
 */
path.resolve = function(from , to) {}

/**
 * Join all arguments together and normalize the resulting path.
 * @param path1
 * @param path2
 */
path.join = function(path1, path2) {}

/**
 * Return the last portion of a path. Similar to the Unix basename command.
 * @param p
 * @param ext
 */
path.basename = function(p, ext) {}

/**
 * Return the extension of the path, from the last &#39;.&#39; to end of
 * string in the last portion of the path. If there is no &#39;.&#39; in
 * the last portion of the path or the first character of it is
 * &#39;.&#39;, then it returns an empty string. Examples:
 * @param p
 */
path.extname = function(p) {}

/**
 * Return the directory name of a path. Similar to the Unix dirname
 * command.
 * @param p
 */
path.dirname = function(p) {}

/**
 * The platform-specific path delimiter, ; or &#39;:&#39;.
 */
path.delimiter = 0;

/**
 * Solve the relative path from from to to.
 * @param from
 * @param to
 */
path.relative = function(from, to) {}

/**
 * The platform-specific file separator. &#39;\\&#39; or &#39;/&#39;.
 */
path.sep = 0;

exports = path;


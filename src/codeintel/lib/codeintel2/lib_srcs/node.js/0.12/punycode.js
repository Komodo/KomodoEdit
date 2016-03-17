/**
 * Punycode.js is bundled with Node.js v0.6.2+. Use
 * require(&#39;punycode&#39;) to access it. (To use it with other Node.js
 * versions, use npm to install the punycode module first.)
 */
var punycode = {};

/**
 * Converts a Punycode string of ASCII-only symbols to a string of Unicode
 * symbols.
 * @param string
 */
punycode.decode = function(string) {}

/**
 * Converts a string of Unicode symbols to a Punycode string of ASCII-only
 * symbols.
 * @param string
 */
punycode.encode = function(string) {}

/**
 * Converts a Punycode string representing a domain name to Unicode. Only
 * the Punycoded parts of the domain name will be converted, i.e. it
 * doesn&#39;t matter if you call it on a string that has already been
 * converted to Unicode.
 * @param domain
 */
punycode.toUnicode = function(domain) {}

/**
 * Converts a Unicode string representing a domain name to Punycode. Only
 * the non-ASCII parts of the domain name will be converted, i.e. it
 * doesn&#39;t matter if you call it with a domain that&#39;s already in
 * ASCII.
 * @param domain
 */
punycode.toASCII = function(domain) {}

/**
 */
punycode.ucs2 = 0;

/**
 * A string representing the current Punycode.js version number.
 * @type {String}
 */
punycode.version = 0;

exports = punycode;


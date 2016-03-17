/**
 * Node.js Addons are dynamically-linked shared objects, written in C or
 * C++, that can be loaded into Node.js using the [require()][require]
 * function, and used just as if they were an ordinary Node.js module. They
 * are used primarily to provide an interface between JavaScript running in
 * Node.js and C/C++ libraries.
 */
var addons = {};

/**
 * Each of the examples illustrated in this document make direct use of the
 * Node.js and V8 APIs for implementing Addons. It is important to
 * understand that the V8 API can, and has, changed dramatically from one
 * V8 release to the next (and one major Node.js release to the next). With
 * each change, Addons may need to be updated and recompiled in order to
 * continue functioning. The Node.js release schedule is designed to
 * minimize the frequency and impact of such changes but there is little
 * that Node.js can do currently to ensure stability of the V8 APIs.
 */
addons.js = 0;

exports = addons;


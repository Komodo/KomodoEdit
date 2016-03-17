/**
 * The assert module provides a simple set of assertion tests that can be
 * used to test invariants. The module is intended for internal use by
 * Node.js, but can be used in application code via
 * require(&#39;assert&#39;). However, assert is not a testing framework,
 * and is not intended to be used as a general purpose assertion library.
 */
var assert = {};

/**
 * Tests shallow, coercive inequality with the not equal comparison
 * operator ( != ).
 * @param actual
 * @param expected
 * @param message
 */
assert.notEqual = function(actual, expected, message) {}

/**
 * Asserts that the function block does not throw an error. See
 * [assert.throws()][] for more details.
 * @param block
 * @param error
 * @param message
 */
assert.doesNotThrow = function(block, error, message) {}

/**
 * Tests if value is truthy. It is equivalent to assert.equal(!!value,
 * true, message).
 * @param value
 * @param message
 */
assert.ok = function(value, message) {}

/**
 * Throws value if value is truthy. This is useful when testing the error
 * argument in callbacks.
 * @param value
 */
assert.ifError = function(value) {}

/**
 * Tests shallow, coercive equality between the actual and expected
 * parameters using the equal comparison operator ( == ).
 * @param actual
 * @param expected
 * @param message
 */
assert.equal = function(actual, expected, message) {}

/**
 * Tests for any deep inequality. Opposite of [assert.deepEqual()][].
 * @param actual
 * @param expected
 * @param message
 */
assert.notDeepEqual = function(actual, expected, message) {}

/**
 * Tests strict inequality as determined by the strict not equal operator (
 * !== ).
 * @param actual
 * @param expected
 * @param message
 */
assert.notStrictEqual = function(actual, expected, message) {}

/**
 * Throws an AssertionError. If message is falsy, the error message is set
 * as the values of actual and expected separated by the provided operator.
 * @param actual
 * @param expected
 * @param message
 * @param operator
 */
assert.fail = function(actual, expected, message, operator) {}

/**
 * Expects the function block to throw an error. If specified, error can be
 * a constructor, [RegExp][], or validation function.
 * @param block
 * @param error
 * @param message
 */
assert.throws = function(block, error, message) {}

/**
 * Tests strict equality as determined by the strict equality operator (
 * === ).
 * @param actual
 * @param expected
 * @param message
 */
assert.strictEqual = function(actual, expected, message) {}

/**
 * Tests for deep equality between the actual and expected parameters.
 * @param actual
 * @param expected
 * @param message
 */
assert.deepEqual = function(actual, expected, message) {}

/**
 * An alias of [assert.ok()][] .
 * @param value
 * @param message
 */
assert.assert = function(value, message) {}

/**
 * Generally identical to assert.deepEqual() with two exceptions. First,
 * primitive values are compared using the strict equality operator ( ===
 * ).
 * @param actual
 * @param expected
 * @param message
 */
assert.deepStrictEqual = function(actual, expected, message) {}

/**
 * Tests for deep strict inequality. Opposite of
 * [assert.deepStrictEqual()][].
 * @param actual
 * @param expected
 * @param message
 */
assert.notDeepStrictEqual = function(actual, expected, message) {}

exports = assert;


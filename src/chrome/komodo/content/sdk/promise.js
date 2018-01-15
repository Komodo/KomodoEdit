/**
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 */

/**
 * Wrapper for promise object, see {@link https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise}
 * 
 * The main difference in ours is it allows multiple callbacks
 *
 * @module ko/promise
 */

/**
 * @constructor module:ko/promise
 *
 * @param {Function} handler    `function(resolve, reject, each) {}`
 * 
 * @returns {module:ko/promise~Promise}     Instance of Promise
 * 
 * @example
 * var promise = new require("ko/promise")((resolve, reject, each))
 * {
 *     require("sdk/timers").setTimeout(() =>
 *     {
 *          each("foo");
 *          each("bar");
 *          resolve("done");
 *     }, 0);
 * });
 * 
 * promise.each(console.log);
 * promise.then(console.info);
 */
module.exports = function(handler)
{
    /**
     * @class Promise
     */

    var promise;
    var callbacks = [];

    var init = () =>
    {
        promise = new Promise(function(resolve, reject)
        {
            handler(resolve, reject, each);
        });
    };

    var each = (data) =>
    {
        for (let callback of callbacks)
            callback(data);
    };

    /**
     * @memberof module:ko/promise~Promise
     * 
     * @param {function}    callback    Invoked for each callback
     * 
     * @returns {this}      Returns the current Promise instance
     */
    this.each = (callback) =>
    {
        callbacks.push(callback);
        return this;
    };

    /**
     * @memberof module:ko/promise~Promise
     * 
     * @param {function}    onFulfilled    A Function called if the Promise is fulfilled. This function has one argument, the fulfillment value.
     * @param {function}    [onRejected]   A Function called if the Promise is rejected. This function has one argument, the rejection reason.
     * 
     * @returns {this}      Returns the current Promise instance
     */
    this.then = () =>
    {
        promise.then.apply(promise, arguments);
        return this;
    };

    /**
     * @memberof module:ko/promise~Promise
     * 
     * @param {function}    onRejected   A Function called if the Promise is rejected. This function has one argument, the rejection reason.
     * 
     * @returns {this}      Returns the current Promise instance
     */
    this.catch = () =>
    {
        promise.catch.apply(promise, arguments);
        return this;
    };

    init();

};

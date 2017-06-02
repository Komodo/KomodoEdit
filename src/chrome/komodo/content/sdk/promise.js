/**
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 * @overview -
 */

module.exports = function(handler)
{
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

    this.each = (callback) =>
    {
        callbacks.push(callback);
        return this;
    };

    this.then = () =>
    {
        promise.then.apply(promise, arguments);
        return this;
    };
    
    this.catch = () =>
    {
        promise.catch.apply(promise, arguments);
        return this;
    };

    init();

};

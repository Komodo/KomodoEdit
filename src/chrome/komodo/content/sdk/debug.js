/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 * @overview -
 */

/**
 * Some simple helper functions useful when debugging.
 *
 * This module will likely be merged into the [console] SDK soon.
 *
 * @module ko/debug
 */
(function() {
    
    /**
     * @function sizeof
     */
    this.sizeof = function(object, giveSummary = true, includeProto = false, includeGetters = false, processed = null)
    {
        processed = processed || [object];
        var summary = [];
        var _summary = [];
        var size = 0;
        var obSize = 0;

        switch (typeof object)
        {

            case 'boolean':
                size += 4;
                break;

            case 'number':
                size += 8;
                break;

            case 'string':
                size += 2 * object.length;
                break;

            case 'function':
                size += 2 * object.toString().length;
                break;

            case 'object':

                if (Object.prototype.toString.call(object) != '[object Array]') {
                    try {
                        size += 2 * Object.keys(object).toString().length;
                    } catch (e) {
                        return 0;
                    }
                }

                for (let key in object)
                {
                    try
                    {
                        let descriptor = Object.getOwnPropertyDescriptor(object, key);
                        if ( ! includeGetters && descriptor && descriptor.get)
                            continue; // nope, not dealing with getters
                    } catch (e) {}

                    let type;
                    try
                    {
                        if ( ! includeProto && ! object.hasOwnProperty(key)) continue;
                        type = typeof object[key];
                    }
                    catch(e)
                    {
                        if (giveSummary)
                            _summary.push([0, key + ": exception: " + e.message]);
                        continue;
                    }

                    if ( ! type || type == "object" && ! object[key])
                        continue; // don't care about nulls

                    let _processed = false;
                    let _size;

                    if (processed.indexOf(object[key]) != -1)
                        continue;

                    processed.push(object[key]);
                    _size = this.sizeof(object[key], false, false, includeGetters, processed);

                    if (giveSummary)
                        _summary.push([_size, key + ": " + _formatBytes(_size)]);

                    size += _size;
                    obSize += _size;
                }

                break;

        }

        if ( ! giveSummary) return size;

        _summary = _summary.sort((a,b) => { return a[0] < b[0]; });
        for (let entry of _summary)
            summary.push(entry[1]);

        summary.push("---------------------");
        summary.push("Self: " + _formatBytes(size - obSize));
        summary.push("Total: " + _formatBytes(size));
        return summary.join("\n");
    }
    
    var _formatBytes = function(bytes,decimals)
    {
       if(bytes == 0) return '0 Byte';
       var k = 1000;
       var dm = decimals + 1 || 3;
       var sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
       var i = Math.floor(Math.log(bytes) / Math.log(k));
       return (bytes / Math.pow(k, i)).toPrecision(dm) + ' ' + sizes[i];
    }
    
}).apply(module.exports);
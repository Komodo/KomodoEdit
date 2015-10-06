(function() {
    
    this.sizeof = function(object, giveSummary = true)
    {
        var processed = {};
        var summary = [];
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
                    size += 2 * Object.keys(object).toString().length
                }

                for (var key in object)
                {
                    try
                    {
                        let descriptor = Object.getOwnPropertyDescriptor(object, key);
                        if (descriptor && descriptor.get)
                            continue; // nope, not dealing with getters
                    } catch (e) {}
                    
                    let type;
                    try
                    {
                        if ( ! object.hasOwnProperty(key)) continue;
                        type = typeof object[key];
                    }
                    catch(e)
                    {
                        continue;
                    }
                    
                    if (type == "object" && ! object[key]) continue; // don't care about nulls
                    
                    if (type != "object" || ! ("__obj_processed" in object[key]))
                    {
                        try
                        {
                            if (type == "object")
                                object[key].__obj_processed = true
                                
                            let _size = this.sizeof(object[key], false);
                            
                            if (giveSummary)
                                summary.push(key + ": " + _formatBytes(_size));
                            
                            size += _size;
                            obSize += _size;
                        }
                        catch (e) {}
                    }
                }

                break;

        }

        if ( ! giveSummary) return size;

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
/*
 * An edited version of ejs.js.
 * It didn't work in the Komodo environment, so as long as I had to fix
 * things I decided to pull out all the web- and Ajax-oriented stuff we
 * don't need, and just leave in the EJS compiler and renderer.
 *
 * And for good measure, insert EJS into the ko.snippets namespace, 
 * to minimize global variables floating around.
 *
 * EJS claims the MIT license at http://code.google.com/p/embeddedjavascript
 * 
 */
if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.snippets)=='undefined') {
    ko.snippets = {};
}
(function(){
    
var rsplit = function(string, regex) {
    var result = regex.exec(string),retArr = [], first_idx, last_idx, first_bit;
    while (result != null)
    {
        first_idx = result.index; last_idx = regex.lastIndex;
        if ((first_idx) != 0)
        {
            first_bit = string.substring(0,first_idx);
            retArr.push(first_bit);
            string = string.slice(first_idx);
        }        
        retArr.push(result[0]);
        string = string.slice(result[0].length);
        result = regex.exec(string);    
    }
    if (! string == '')
    {
        retArr.push(string);
    }
    return retArr;
},
chop =  function(string){
    return string.substr(0, string.length - 1);
},
extend = function(d, s){
    for(var n in s){
        if(s.hasOwnProperty(n))  d[n] = s[n]
    }
}


var EJS = function(text) {
    var template = new EJS.Compiler(text, '<');
    template.compile();
    this.template = template;
};
ko.snippets.EJS = EJS;

/* @Prototype*/
EJS.prototype = {
    /**
     * Renders an object.
     * @param {Object} object data to be rendered
     * @param {Object} extra_helpers an object with additonal view helpers
     * @return {String} returns the result of the string
     */
    render : function(object, extra_helpers){
        object = object || {};
        this._extra_helpers = extra_helpers;
        var v = new EJS.Helpers(object, extra_helpers || {});
        return this.template.process.call(object, object,v);
    },
    out : function(){
        return this.template.out;
    }
};

/* @Static*/
EJS.Scanner = function(source, left, right) {
    
    extend(this,
        {left_delimiter:     left +'%',
         right_delimiter:     '%'+right,
         double_left:         left+'%%',
         double_right:      '%%'+right,
         left_equal:         left+'%=',
         left_comment:     left+'%#'})

    this.SplitRegexp = left=='[' ? /(\[%%)|(%%\])|(\[%=)|(\[%#)|(\[%)|(%\]\n)|(%\])|(\n)/ : new RegExp('('+this.double_left+')|(%%'+this.double_right+')|('+this.left_equal+')|('+this.left_comment+')|('+this.left_delimiter+')|('+this.right_delimiter+'\n)|('+this.right_delimiter+')|(\n)') ;
    
    this.source = source;
    this.stag = null;
    this.lines = 0;
};

EJS.Scanner.to_text = function(input){
    if(input == null || input === undefined)
        return '';
    if(input instanceof Date)
        return input.toDateString();
    if(input.toString) 
        return input.toString();
    return '';
};

EJS.Scanner.prototype = {
  scan: function(block) {
        //var scanline = this.scanline;
     var regex = this.SplitRegexp;
     if (this.source)
     {
          var source_split = rsplit(this.source, /\n/);
          for(var i=0; i<source_split.length; i++) {
              var item = source_split[i];
              this.scanline(item, regex, block);
         }
     }
  },
  scanline: function(line, regex, block) {
        this.lines++;
        var line_split = rsplit(line, regex);
        for(var i=0; i<line_split.length; i++) {
            var token = line_split[i];
            if (token != null) {
                try{
                    block(token, this);
                }catch(e){
                    throw {type: 'EJS.Scanner', line: this.lines};
                }
            }
        }
    }
};


EJS.Buffer = function(pre_cmd, post_cmd) {
    this.line = [];
    this.script = "";
    this.pre_cmd = pre_cmd;
    this.post_cmd = post_cmd;
    for (var i=0; i<this.pre_cmd.length; i++)
    {
        this.push(pre_cmd[i]);
    }
};
EJS.Buffer.prototype = {
    
  push: function(cmd) {
    this.line.push(cmd);
  },

  cr: function() {
    this.script += this.line.join('; ') + "\n";
    this.line = [];
  },

  close: function() {
    if (this.line.length > 0)
    {
        for (var i=0; i<this.post_cmd.length; i++){
            this.push(pre_cmd[i]);
        }
        this.script = this.script + this.line.join('; ');
        this.line = null;
    }
  }
     
};


EJS.Compiler = function(source, left) {
    this.pre_cmd = ['var ___ViewO = [];'];
    this.post_cmd = [];
    if (typeof source == 'string') {
        source = source.replace(/\r\n?/g, "\n");
    } else {
        source = "";
    }
    left = left || '<';
    var right = '>';
    var leftRegExp, rightRegExp;
    switch(left) {
        case '[':
            right = ']';
            leftRegExp = '\\[';
            rightRegExp = '\\]';
            break;
        case '<':
            leftRegExp = '<';
            rightRegExp = '>';
            break;
        default:
            throw left+' is not a supported delimiter';
            break;
    }
    // Remove newlines after <% ... %> blocks, leading space before the <%
    // [ \t]*(<%(?![=\#])[\s\S]*?%>)[ \t]*(?:$|\n)
    var ptn = new RegExp('('
                         + leftRegExp
                         + "%"
                         + "(?!=)"
                         + "[\\s\\S]*?"
                         + "%"
                         + rightRegExp
                         + ")[ \\t]*(?:$|\\n)", 'g');
    this.originalSource = source;
    var source2 = source.replace(ptn, '$1');
    this.source = source2;
    this.left = left;
    this.right = right;
    this.scanner = new EJS.Scanner(this.source, left, right);
};
EJS.Compiler.prototype = {
  gather: function() {
    var put_cmd = "___ViewO.push(";
    var insert_cmd = put_cmd;
    var buff = new EJS.Buffer(this.pre_cmd, this.post_cmd);        
    var content = '';
    var clean = function(content)
    {
        content = content.replace(/\\/g, '\\\\');
        content = content.replace(/\n/g, '\\n');
        content = content.replace(/\"/g,  '\\"');
        return content;
    };
    this.scanner.scan(function(token, scanner) {
        if (scanner.stag == null)
        {
            switch(token) {
                case '\n':
                    content += "\n";
                    buff.push(put_cmd + '"' + clean(content) + '");');
                    buff.cr();
                    content = '';
                    break;
                case scanner.left_delimiter:
                case scanner.left_equal:
                case scanner.left_comment:
                    scanner.stag = token;
                    if (content.length > 0)
                    {
                        buff.push(put_cmd + '"' + clean(content) + '")');
                    }
                    content = '';
                    break;
                case scanner.double_left:
                    content += scanner.left_delimiter;
                    break;
                default:
                    content += token;
                    break;
            }
        }
        else {
            switch(token) {
                case scanner.right_delimiter:
                    switch(scanner.stag) {
                        case scanner.left_delimiter:
                            if (content[content.length - 1] == '\n')
                            {
                                content = chop(content);
                                buff.push(content);
                                buff.cr();
                            }
                            else {
                                buff.push(content);
                            }
                            break;
                        case scanner.left_equal:
                            buff.push(insert_cmd + "(EJS.Scanner.to_text(" + content + ")))");
                            break;
                    }
                    scanner.stag = null;
                    content = '';
                    break;
                case scanner.double_right:
                    content += scanner.right_delimiter;
                    break;
                default:
                    content += token;
                    break;
            }
        }
    });
    if (content.length > 0)
    {
        // Could be content.dump in Ruby
        buff.push(put_cmd + '"' + clean(content) + '")');
    }
    buff.close();
    return buff;
  },
    
  compile: function() {
    var buff = this.gather(this.source);
    var code = this.out = buff.script + ";";
    var to_be_evaled = '/*'+name+'*/this.process = function(_CONTEXT,_VIEW) { try { with(_VIEW) { with (_CONTEXT) {'+code+" return ___ViewO.join('');}}}catch(e){e.lineNumber=null;throw e;}};";
    // Note that in the following code, the offsets for the revised line #
    // are sensitive to changes in the code below this point and where
    // "here.lineNumber" is calculated.  Needed because js eval gives line-numbers
    // based on the current file; new context isn't started with an eval.
    try {
        eval(to_be_evaled);
    } catch(e) {
        //dump("problem eval'ing snippet [\n" + to_be_evaled + "\n]: " + e + "\n");
        this.scanner = new EJS.Scanner(this.originalSource, this.left, this.right);
        buff = this.gather();
        code = buff.script + ";";
        var here;
        try {
            //dump("Original code:\n" + code + "\n");
            here = new Error();
            eval(code);
            //dump("???????????????? Original wouldn't throw an error\n");
            e.lineNumber -= (here.lineNumber - 9);
            throw e;
        } catch(e2) {
            //dump("Original threw error: " + e2 + "\n");
            here = new Error();
            e2.lineNumber -= (here.lineNumber - 6);
            throw e2;
        }
    }
  }
};

/**
 * @constructor
 * By adding functions to EJS.Helpers.prototype, those functions will be available in the
 * views.
 * @init Creates a view helper.  This function is called internally.  You should never call it.
 * @param {Object} data The data passed to the view.  Helpers have access to it through this._data
 */
EJS.Helpers = function(data, extras){
	this._data = data;
    this._extras = extras;
    extend(this, extras );
};
/* @prototype*/
EJS.Helpers.prototype = {
    /**
     * Renders a new view.  If data is passed in, uses that to render the view.
     * @param {Object} options standard options passed to a new view.
     * @param {optional:Object} data
     * @return {String}
     */
	view: function(options, data, helpers){
        if(!helpers) helpers = this._extras
		if(!data) data = this._data;
		return new EJS(options).render(data, helpers);
	},
    /**
     * For a given value, tries to create a human representation.
     * @param {Object} input the value being converted.
     * @param {Object} null_text what text should be present if input == null or undefined, defaults to ''
     * @return {String}
     */
	to_text: function(input, null_text) {
	    if(input == null || input === undefined) return null_text || '';
	    if(input instanceof Date) return input.toDateString();
		if(input.toString) return input.toString().replace(/\n/g, '<br />').replace(/''/g, "'");
		return '';
	}
};

})();

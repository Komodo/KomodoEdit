/*
Copyright (c) 2007 John Dyer (http://johndyer.name)
MIT style license
*/

if (!window.Refresh) Refresh = {};
if (!Refresh.Web) Refresh.Web = {};

Refresh.Web.ColorValuePicker = function(id, parent, settings) {
    this.id = id;
    this.parent = parent;
    this.onValuesChanged = null;

    this._hexInput = document.getElementById(this.id + '_Hex');
    this._rgbInput = document.getElementById(this.id + '_RGB');
    this._hslInput = document.getElementById(this.id + '_HSL');
    this._alphaInput = document.getElementById(this.id + "_A");

    // assign events

    // events
    var this_ = this;
    this._event_onHsvKeyUp = function(e) {
        this_._onHsvKeyUp(e);
    };
    this._event_onHsvBlur = function(e) {
        this_._onHsvBlur(e);
    };
    this._event_onRgbKeyUp = function(e) {
        this_._onRgbKeyUp(e);
    };
    this._event_onAlphaBlur = function(e) {
        this_._onAlphaBlur(e);
    };
    this._event_onRgbBlur = function(e) {
        this_._onRgbBlur(e);
    };
    this._event_onHexKeyUp = function(e) {
        this_._onHexKeyUp(e);
    };
    this._event_onHexBlur = function(e) {
        this_._onHexBlur(e);
    };
    this._event_onAlphaKeyUp = function(e) {
        this_._onAlphaKeyUp(e);
    };

    this._hexInput.addEventListener('keyup', this._event_onHexKeyUp, false);
    this._rgbInput.addEventListener('keyup', this._event_onRgbKeyUp, false);
    this._hslInput.addEventListener('keyup', this._event_onHsvKeyUp, false);
    this._alphaInput.addEventListener('keyup', this._event_onAlphaKeyUp, false);

    this._hexInput.addEventListener('blur', this._event_onHexBlur, false);
    this._rgbInput.addEventListener('blur', this._event_onRgbBlur, false);
    this._hslInput.addEventListener('blur', this._event_onHsvBlur, false);
    this._hslInput.addEventListener('blur', this._event_onAlphaBlur, false);

    this.color = new Refresh.Web.Color();

    // get an initial value
    if (this._hexInput.value !== '')
        this.color.setHex(this._hexInput.value);


    // set the others based on initial value
    this._hexInput.value = "#" + settings.color;
    this._rgbInput.value = 'rgba(' + [this.color.r,this.color.g,this.color.b,settings.alpha].join(',') + ')';
    this._hslInput.value = 'hsl(' + [this.color.h,this.color.s,this.color.v].join(',') + ')';
    this._alphaInput.value = settings.alpha;
};

Refresh.Web.ColorValuePicker.prototype = {
    _onHsvKeyUp: function(e) {
        if (e.target.value === '') return;
        this.validateHsv(e);
        this.setValuesFromHsv();
        if (this.onValuesChanged) this.onValuesChanged(this);
    },
    _onRgbKeyUp: function(e) {
        if (e.target.value === '') return;
        this.validateRgb(e);
        this.setValuesFromRgb();
        if (this.onValuesChanged) this.onValuesChanged(this);
    },
    _onHexKeyUp: function(e) {
        if (e.target.value === '') return;
        this.validateHex(e);
        this.setValuesFromHex();
        if (this.onValuesChanged) this.onValuesChanged(this);
    },
    _onAlphaKeyUp: function(e) {
        if (e.target.value === '') return;
        this.validateAlpha(e);
        this.setValuesFromAlpha();
        if (this.onValuesChanged) this.onValuesChanged(this);
    },
    _onHsvBlur: function(e) {
        if (e.target.value === '')
            this.setValuesFromRgb();
    },
    _onRgbBlur: function(e) {
        if (e.target.value === '')
            this.setValuesFromHsv();
    },
    _onHexBlur: function(e) {
        if (e.target.value === '')
            this.setValuesFromHex();
    },
    HexBlur: function(e) {
        if (e.target.value === '')
            this.setValuesFromHex();
    },
    _onAlphaBlur: function(e) {
        if (e.target.value === '')
            this.setValuesFromAlpha();
    },
    validateAlpha: function(e) {
        if (!this._keyNeedsValidation(e)) return e;
        if (e.target.value.indexOf(".") != -1 && e.target.value.length < 3) return null; // don't validate 0. things
        var alpha = parseFloat(e.target.value);
        alpha = this._setValueInRange(alpha, 0.0, 1.0, true);
        this._alphaInput.value = alpha;
        return null;
    },
    validateRgb: function(e) {
        if (!this._keyNeedsValidation(e)) return e;
        var rgb = this._rgbInput.value.split(/(?:rgba\(|\))/)[1].split(/\s*,\s*/);
        var _rgb = [];

        _rgb[0] = this._setValueInRange(rgb[0],0,255);
        _rgb[1] = this._setValueInRange(rgb[1],0,255);
        _rgb[2] = this._setValueInRange(rgb[2],0,255);
        _rgb[3] = this._setValueInRange(rgb[3],0.0,1.0,true);

        if (rgb.join() != _rgb.join())
            this._rgbInput.value = 'rgba(' + [_rgb[0],_rgb[1],_rgb[2],_rgb[3]].join(',') + ')';

        return null;
    },
    validateHsv: function(e) {
        if (!this._keyNeedsValidation(e)) return e;

        var hsv = this._hslInput.value.split(/(?:hsl\(|\))/)[1].split(/\s*,\s*/);
        var _hsv = [];

        _hsv[0] = this._setValueInRange(hsv[0],0,359);
        _hsv[1] = this._setValueInRange(hsv[1],0,100);
        _hsv[2] = this._setValueInRange(hsv[2],0,100);

        if (hsv.join() != _hsv.join())
            this._hslInput.value = 'hsl(' + [_hsv[0],_hsv[1],_hsv[2]].join(',') + ')';

        return null;
    },
    validateHex: function(e) {
        if (!this._keyNeedsValidation(e)) return e;
        var _hex = String(this._hexInput.value);
        var hex = _hex.toUpperCase();
        hex = hex.replace(/[^A-F0-9]/g, '');
        if (hex.length > 6) hex = hex.substring(0, 6);
        if (hex != _hex) this._hexInput.value = "#" + hex;
        return null;
    },
    _keyNeedsValidation: function(e) {

        if (e.keyCode == 9  || // TAB
            e.keyCode == 16  || // Shift
            e.keyCode == 38 || // Up arrow
            e.keyCode == 29 || // Right arrow
            e.keyCode == 40 || // Down arrow
            e.keyCode == 37 || // Left arrow
            (e.ctrlKey && (e.keyCode == 'c'.charCodeAt() || e.keyCode == 'v'.charCodeAt()) )
        ) return false;

        return true;
    },
    _setValueInRange: function(value,min,max,is_float) {
        if (typeof(is_float) === 'undefined') is_float = false;
        if (value === '' || isNaN(value))
            return min;
        if (is_float) {
            value = parseFloat(value);
        } else {
            value = parseInt(value);
        }
        if (value > max)
            return max;
        if (value < min)
            return min;

        return value;
    },
    setValuesFromRgb: function() {
        var rgb = this._rgbInput.value.split(/(?:rgba\(|\))/)[1].split(/\s*,\s*/);
        this.color.setRgb(rgb[0],rgb[1],rgb[2],rgb[3]);

        this._hexInput.value = "#" + this.color.hex;
        this._hslInput.value = 'hsl(' + [this.color.h,this.color.s,this.color.v].join(',') + ')';
        this.parent.setReturnColorMode("r", "setrgb");
    },
    setValuesFromHsv: function(prefer_hex) {
        if (typeof(prefer_hex) === 'undefined') prefer_hex = false;
        var hsv = this._hslInput.value.split(/(?:hsl\(|\))/)[1].split(/\s*,\s*/);
        this.color.setHsv(hsv[0],hsv[1],hsv[2]);
        var alpha = parseFloat(this._alphaInput.value);

        this._hexInput.value = "#" + this.color.hex;
        this._rgbInput.value = 'rgba(' + [this.color.r,this.color.g,this.color.b,alpha].join(',') + ')';
        if (prefer_hex) {
            this.parent.setReturnColorMode("h", "sethsv[hex]");
        } else {
            this.parent.setReturnColorMode("s", "sethsv");
        }
    },
    setValuesFromHex: function() {
        this.color.setHex(this._hexInput.value.substr(1));
        var alpha = parseFloat(this._alphaInput.value);

        this._rgbInput.value = 'rgba(' + [this.color.r,this.color.g,this.color.b,alpha].join(',') + ')';
        this._hslInput.value = 'hsl(' + [this.color.h,this.color.s,this.color.v].join(',') + ')';
        this.parent.setReturnColorMode("h", "sethex");
    },
    setValuesFromAlpha: function(hex) {
        if (typeof(hex) === "undefined" || hex === "undefined") hex = this._hexInput.value;
        if (hex[0] == "#") hex = hex.substring(1,7);
        var alpha = parseFloat(this._alphaInput.value);
        var rgb = Refresh.Web.ColorMethods.hexToRgb(hex);
        rgb = [rgb.r,rgb.g,rgb.b];
        this._rgbInput.value = "rgba(" + [rgb[0],rgb[1],rgb[2],alpha].join(',') + ")";
        this.color.setRgb(rgb[0],rgb[1],rgb[2],alpha);

        this._hexInput.value = "#" + hex;
        this._hslInput.value = 'hsl(' + [this.color.h,this.color.s,this.color.v].join(',') + ')';
        this.parent.setReturnColorMode("r", "setalpha");
    }
};

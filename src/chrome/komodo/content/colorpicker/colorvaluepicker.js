/*
Copyright (c) 2007 John Dyer (http://johndyer.name)
MIT style license
*/

if (!window.Refresh) Refresh = {};
if (!Refresh.Web) Refresh.Web = {};

Refresh.Web.ColorValuePicker = function(id) {
	this.id = id;

	this.onValuesChanged = null;

	this._hueInput = document.getElementById(this.id + '_Hue');
	this._valueInput = document.getElementById(this.id + '_Brightness');
	this._saturationInput = document.getElementById(this.id + '_Saturation');

	this._redInput = document.getElementById(this.id + '_Red');
	this._greenInput = document.getElementById(this.id + '_Green');
	this._blueInput = document.getElementById(this.id + '_Blue');

	this._hexInput = document.getElementById(this.id + '_Hex');

	// assign events

	// events
	var this_ = this;
	this._event_onHsvKeyUp = function(e) {
		this_._onHsvKeyUp(e);
	}
	this._event_onHsvBlur = function(e) {
		this_._onHsvBlur(e);
	}
	this._event_onRgbKeyUp = function(e) {
		this_._onRgbKeyUp(e);
	}
	this._event_onRgbBlur = function(e) {
		this_._onRgbBlur(e);
	}
	this._event_onHexKeyUp = function(e) {
		this_._onHexKeyUp(e);
	}

	// HSB
	this._hueInput.addEventListener('keyup', this._event_onHsvKeyUp, false);
	this._valueInput.addEventListener('keyup',this._event_onHsvKeyUp, false);
	this._saturationInput.addEventListener('keyup',this._event_onHsvKeyUp, false);
	this._hueInput.addEventListener('blur', this._event_onHsvBlur, false);
	this._valueInput.addEventListener('blur',this._event_onHsvBlur, false);
	this._saturationInput.addEventListener('blur',this._event_onHsvBlur, false);

	// RGB
	this._redInput.addEventListener('keyup', this._event_onRgbKeyUp, false);
	this._greenInput.addEventListener('keyup', this._event_onRgbKeyUp, false);
	this._blueInput.addEventListener('keyup', this._event_onRgbKeyUp, false);
	this._redInput.addEventListener('blur', this._event_onRgbBlur, false);
	this._greenInput.addEventListener('blur', this._event_onRgbBlur, false);
	this._blueInput.addEventListener('blur', this._event_onRgbBlur, false);

	// HEX
	this._hexInput.addEventListener('keyup', this._event_onHexKeyUp, false);
	
	this.color = new Refresh.Web.Color();
	
	// get an initial value
	if (this._hexInput.value != '')
		this.color.setHex(this._hexInput.value);
		
		
	// set the others based on initial value
	this._hexInput.value = this.color.hex;
	
	this._redInput.value = this.color.r;
	this._greenInput.value = this.color.g;
	this._blueInput.value = this.color.b;
	
	this._hueInput.value = this.color.h;
	this._saturationInput.value = this.color.s;
	this._valueInput.value = this.color.v;
}

Refresh.Web.ColorValuePicker.prototype = {
	_onHsvKeyUp: function(e) {
		if (e.target.value == '') return;
		this.validateHsv(e);
		this.setValuesFromHsv();
		if (this.onValuesChanged) this.onValuesChanged(this);
	},
	_onRgbKeyUp: function(e) {
		if (e.target.value == '') return;
		this.validateRgb(e);
		this.setValuesFromRgb();
		if (this.onValuesChanged) this.onValuesChanged(this);
	},
	_onHexKeyUp: function(e) {
		if (e.target.value == '') return;
		this.validateHex(e);
		this.setValuesFromHex();
		if (this.onValuesChanged) this.onValuesChanged(this);
	},
	_onHsvBlur: function(e) {
		if (e.target.value == '')
			this.setValuesFromRgb();
	},
	_onRgbBlur: function(e) {
		if (e.target.value == '')
			this.setValuesFromHsv();
	},
	HexBlur: function(e) {
		if (e.target.value == '')
			this.setValuesFromHsv();
	},
	validateRgb: function(e) {
		if (!this._keyNeedsValidation(e)) return e;
		this._redInput.value = this._setValueInRange(this._redInput.value,0,255);
		this._greenInput.value = this._setValueInRange(this._greenInput.value,0,255);
		this._blueInput.value = this._setValueInRange(this._blueInput.value,0,255);
		return null;
	},
	validateHsv: function(e) {
		if (!this._keyNeedsValidation(e)) return e;
		this._hueInput.value = this._setValueInRange(this._hueInput.value,0,359);
		this._saturationInput.value = this._setValueInRange(this._saturationInput.value,0,100);
		this._valueInput.value = this._setValueInRange(this._valueInput.value,0,100);
		return null;
	},
	validateHex: function(e) {
		if (!this._keyNeedsValidation(e)) return e;
		var hex = new String(this._hexInput.value).toUpperCase();
		hex = hex.replace(/[^A-F0-9]/g, '0');
		if (hex.length > 6) hex = hex.substring(0, 6);
		this._hexInput.value = hex;
		return null;
	},
	_keyNeedsValidation: function(e) {

		if (e.keyCode == 9  || // TAB
			e.keyCode == 16  || // Shift
			e.keyCode == 38 || // Up arrow
			e.keyCode == 29 || // Right arrow
			e.keyCode == 40 || // Down arrow
			e.keyCode == 37    // Left arrow
			||
			(e.ctrlKey && (e.keyCode == 'c'.charCodeAt() || e.keyCode == 'v'.charCodeAt()) )
		) return false;

		return true;
	},
	_setValueInRange: function(value,min,max) {
		if (value == '' || isNaN(value)) 		
			return min;
		
		value = parseInt(value);
		if (value > max) 
			return max;
		if (value < min) 
			return min;
		
		return value;
	},
	setValuesFromRgb: function() {
		this.color.setRgb(this._redInput.value, this._greenInput.value, this._blueInput.value);
		this._hexInput.value = this.color.hex;
		this._hueInput.value = this.color.h;
		this._saturationInput.value = this.color.s;
		this._valueInput.value = this.color.v;
	},
	setValuesFromHsv: function() {
		this.color.setHsv(this._hueInput.value, this._saturationInput.value, this._valueInput.value);		
		
		this._hexInput.value = this.color.hex;
		this._redInput.value = this.color.r;
		this._greenInput.value = this.color.g;
		this._blueInput.value = this.color.b;
	},
	setValuesFromHex: function() {
		this.color.setHex(this._hexInput.value);

		this._redInput.value = this.color.r;
		this._greenInput.value = this.color.g;
		this._blueInput.value = this.color.b;
		
		this._hueInput.value = this.color.h;
		this._saturationInput.value = this.color.s;
		this._valueInput.value = this.color.v;
	}
};

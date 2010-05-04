/*
Copyright (c) 2007 John Dyer (http://johndyer.name)
MIT style license
*/

if (typeof(Refresh) == 'undefined') window.Refresh = {};
if (typeof(Refresh.Web) == 'undefined') Refresh.Web = {};

Refresh.Web.Color = function(init) {	
	var color = {
		r: 0,
		g: 0,
		b: 0,
		
		h: 0,
		s: 0,
		v: 0,
		
		hex: '',
		
		setRgb: function(r, g, b) {
			this.r = r;
			this.g = g;
			this.b = b;
						
			var newHsv = Refresh.Web.ColorMethods.rgbToHsv(this);
			this.h = newHsv.h;
			this.s = newHsv.s;
			this.v = newHsv.v;
			
			this.hex = Refresh.Web.ColorMethods.rgbToHex(this);					
		},
		
		setHsv: function(h, s, v) {
			this.h = h;
			this.s = s;
			this.v = v;
			
			var newRgb = Refresh.Web.ColorMethods.hsvToRgb(this);
			this.r = newRgb.r;
			this.g = newRgb.g;
			this.b = newRgb.b;
			
			this.hex = Refresh.Web.ColorMethods.rgbToHex(newRgb);	
		},
		
		setHex: function(hex) {
			this.hex = hex;
			
			var newRgb = Refresh.Web.ColorMethods.hexToRgb(this.hex);
			this.r = newRgb.r;
			this.g = newRgb.g;
			this.b = newRgb.b;
			
			var newHsv = Refresh.Web.ColorMethods.rgbToHsv(newRgb);
			this.h = newHsv.h;
			this.s = newHsv.s;
			this.v = newHsv.v;			
		}
	};
	
	if (init) {
		if ("hex" in init)
			color.setHex(init.hex);
		else if ("r" in init)
			color.setRgb(init.r, init.g, init.b);
		else if ("h" in init)
			color.setHsv(init.h, init.s, init.v);			
	}
	
	return color;
};
Refresh.Web.ColorMethods = {
	hexToRgb: function(hex) {
		hex = this.validateHex(hex);

		var r='00', g='00', b='00';
		
		/*
		if (hex.length == 3) {
			r = hex.substring(0,1);
			g = hex.substring(1,2);
			b = hex.substring(2,3);
		} else if (hex.length == 6) {
			r = hex.substring(0,2);
			g = hex.substring(2,4);
			b = hex.substring(4,6);
		*/
		if (hex.length == 6) {
			r = hex.substring(0,2);
			g = hex.substring(2,4);
			b = hex.substring(4,6);	
		} else {
			if (hex.length > 4) {
				r = hex.substring(4, hex.length);
				hex = hex.substring(0,4);
			}
			if (hex.length > 2) {
				g = hex.substring(2,hex.length);
				hex = hex.substring(0,2);
			}
			if (hex.length > 0) {
				b = hex.substring(0,hex.length);
			}					
		}
		
		return { r:this.hexToInt(r), g:this.hexToInt(g), b:this.hexToInt(b) };
	},
	validateHex: function(hex) {
		hex = new String(hex).toUpperCase();
		hex = hex.replace(/[^A-F0-9]/g, '0');
		if (hex.length > 6) hex = hex.substring(0, 6);
		return hex;
	},
	webSafeDec: function (dec) {
		dec = Math.round(dec / 51);
		dec *= 51;
		return dec;
	},
	hexToWebSafe: function (hex) {
		var r, g, b;

		if (hex.length == 3) {
			r = hex.substring(0,1);
			g = hex.substring(1,1);
			b = hex.substring(2,1);
		} else {
			r = hex.substring(0,2);
			g = hex.substring(2,4);
			b = hex.substring(4,6);
		}
		return intToHex(this.webSafeDec(this.hexToInt(r))) + this.intToHex(this.webSafeDec(this.hexToInt(g))) + this.intToHex(this.webSafeDec(this.hexToInt(b)));
	},
	rgbToWebSafe: function(rgb) {
		return {r: this.webSafeDec(rgb.r), g: this.webSafeDec(rgb.g), b: this.webSafeDec(rgb.b) };
	},
	rgbToHex: function (rgb) {
		return this.intToHex(rgb.r) + this.intToHex(rgb.g) + this.intToHex(rgb.b);
	},
	intToHex: function (dec){
		var result = (parseInt(dec).toString(16));
		if (result.length == 1)
			result = ("0" + result);
		return result.toUpperCase();
	},
	hexToInt: function (hex){
		return(parseInt(hex,16));
	},
	rgbToHsv: function (rgb) {

		var r = rgb.r / 255;
		var g = rgb.g / 255;
		var b = rgb.b / 255;

		var hsv = {h:0, s:0, v:0};

		var min = 0
		var max = 0;

		if (r >= g && r >= b) {
			max = r;
			min = (g > b) ? b : g;
		} else if (g >= b && g >= r) {
			max = g;
			min = (r > b) ? b : r;
		} else {
			max = b;
			min = (g > r) ? r : g;
		}

		hsv.v = max;
		hsv.s = (max) ? ((max - min) / max) : 0;

		if (!hsv.s) {
			hsv.h = 0;
		} else {
			var delta = max - min;
			if (r == max) {
				hsv.h = (g - b) / delta;
			} else if (g == max) {
				hsv.h = 2 + (b - r) / delta;
			} else {
				hsv.h = 4 + (r - g) / delta;
			}

			hsv.h = parseInt(hsv.h * 60);
			if (hsv.h < 0) {
				hsv.h += 360;
			}
		}
		
		if (hsv.h >= 360) {
			hsv.h = 0;
		}
		hsv.s = parseInt(hsv.s * 100);
		hsv.v = parseInt(hsv.v * 100);

		return hsv;
	},
	hsvToRgb: function (hsv) {

		var rgb = {r:0, g:0, b:0};
		
		var h = hsv.h;
		var s = hsv.s;
		var v = hsv.v;

		if (s == 0) {
			if (v == 0) {
				rgb.r = rgb.g = rgb.b = 0;
			} else {
				rgb.r = rgb.g = rgb.b = parseInt(v * 255 / 100);
			}
		} else {
			if (h == 360) {
				h = 0;
			}
			h /= 60;

			// 100 scale
			s = s/100;
			v = v/100;

			var i = parseInt(h);
			var f = h - i;
			var p = v * (1 - s);
			var q = v * (1 - (s * f));
			var t = v * (1 - (s * (1 - f)));
			switch (i) {
				case 0:
					rgb.r = v;
					rgb.g = t;
					rgb.b = p;
					break;
				case 1:
					rgb.r = q;
					rgb.g = v;
					rgb.b = p;
					break;
				case 2:
					rgb.r = p;
					rgb.g = v;
					rgb.b = t;
					break;
				case 3:
					rgb.r = p;
					rgb.g = q;
					rgb.b = v;
					break;
				case 4:
					rgb.r = t;
					rgb.g = p;
					rgb.b = v;
					break;
				case 5:
					rgb.r = v;
					rgb.g = p;
					rgb.b = q;
					break;
			}

			rgb.r = parseInt(rgb.r * 255);
			rgb.g = parseInt(rgb.g * 255);
			rgb.b = parseInt(rgb.b * 255);
		}

		return rgb;
	}
};
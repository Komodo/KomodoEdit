/*
Copyright (c) 2007 John Dyer (http://johndyer.name)
MIT style license
*/

if (!window.Refresh) Refresh = {};
if (!Refresh.Web) Refresh.Web = {};

Refresh.Web.SlidersList = [];

Refresh.Web.Slider = function(elem, settings) {
	this._bar = elem;
	this.settings = {
		xMinValue: 0,
		xMaxValue: 100,
		yMinValue: 0,
		yMaxValue: 100,
		arrowImage: 'chrome://komodo/skin/images/colorpicker/rangearrows.gif'
	}
	if (settings) {
		if ('xMinValue' in settings)
			this.settings.xMinValue = settings.xMinValue;
		if ('xMaxValue' in settings)
			this.settings.xMaxValue = settings.xMaxValue;
		if ('yMinValue' in settings)
			this.settings.yMinValue = settings.yMinValue;
		if ('yMaxValue' in settings)
			this.settings.yMaxValue = settings.yMaxValue;
		if ('arrowImage' in settings)
			this.settings.arrowImage = settings.arrowImage;
	}

	this.xValue = 0;
	this.yValue = 0;

	// build controls
	this._arrow = document.createElement('img');
	this._arrow.border = 0;
	this._arrow.src = this.settings.arrowImage;
	this._arrow.margin = 0;
	this._arrow.padding = 0;
	this._arrow.style.position = 'absolute';
	this._arrow.style.top = '0px';
	this._arrow.style.left = '0px';
	document.body.appendChild(this._arrow);

	// attach 'this' to html objects
	var slider = this;
	
	this.setPositioningVariables();
	
	var this_ = this;
	this._event_docMouseMove = function(e) {
		this_._docMouseMove(e);
	}
	this._event_docMouseUp = function(e) {
		this_._docMouseUp(e);
	}
	this._event_barMouseDown = function(e) {
		this_._bar_mouseDown(e);
	}
	this._event_arrowMouseDown = function(e) {
		this_._arrow_mouseDown(e);
	}

	this._bar.addEventListener('mousedown', this._event_barMouseDown, false);
	this._arrow.addEventListener('mousedown', this._event_arrowMouseDown, false);

	// set initial position
	this.setArrowPositionFromValues();

	// fire events
	if(this.onValuesChanged)
		this.onValuesChanged(this);

	// final setup
	Refresh.Web.SlidersList.push(this);
	
}

Refresh.Web.Slider.prototype = {
	_bar: null,
	_arrow: null,

	setPositioningVariables: function() {
		// calculate sizes and ranges
		// BAR

		this._barWidth = this._bar.width;
		this._barHeight = this._bar.height;
		
		function cumulativeOffset(elem) {
			var valueT = 0, valueL = 0;
			do {
				valueT += elem.offsetTop  || 0;
				valueL += elem.offsetLeft || 0;
				elem = elem.offsetParent;
			} while (elem);
			return {left: valueL, top: valueT};
		}
		var pos = cumulativeOffset(this._bar);
		this._barTop = pos.top;
		this._barLeft = pos.left;
		
		this._barBottom = this._barTop + this._barHeight;
		this._barRight = this._barLeft + this._barWidth;

		// ARROW
		this._arrowWidth = this._arrow.width;
		this._arrowHeight = this._arrow.height;

		// MIN & MAX
		this.MinX = this._barLeft;
		this.MinY = this._barTop;

		this.MaxX = this._barRight;
		this.MinY = this._barBottom;
	},
	
	setArrowPositionFromValues: function(e) {
		this.setPositioningVariables();
		
		// sets the arrow position from XValue and YValue properties

		var arrowOffsetX = 0;
		var arrowOffsetY = 0;
		
		// X Value/Position
		if (this.settings.xMinValue != this.settings.xMaxValue) {

			if (this.xValue == this.settings.xMinValue) {
				arrowOffsetX = 0;
			} else if (this.xValue == this.settings.xMaxValue) {
				arrowOffsetX = this._barWidth-1;
			} else {

				var xMax = this.settings.xMaxValue;
				if (this.settings.xMinValue < 1)  {
					xMax = xMax + Math.abs(this.settings.xMinValue) + 1;
				}
				var xValue = this.xValue;

				if (this.xValue < 1) xValue = xValue + 1;

				arrowOffsetX = xValue / xMax * this._barWidth;

				if (parseInt(arrowOffsetX) == (xMax-1)) 
					arrowOffsetX=xMax;
				else 
					arrowOffsetX=parseInt(arrowOffsetX);

				// shift back to normal values
				if (this.settings.xMinValue < 1)  {
					arrowOffsetX = arrowOffsetX - Math.abs(this.settings.xMinValue) - 1;
				}
			}
		}
		
		// X Value/Position
		if (this.settings.yMinValue != this.settings.yMaxValue) {	
			
			if (this.yValue == this.settings.yMinValue) {
				arrowOffsetY = 0;
			} else if (this.yValue == this.settings.yMaxValue) {
				arrowOffsetY = this._barHeight-1;
			} else {
			
				var yMax = this.settings.yMaxValue;
				if (this.settings.yMinValue < 1)  {
					yMax = yMax + Math.abs(this.settings.yMinValue) + 1;
				}

				var yValue = this.yValue;

				if (this.yValue < 1) yValue = yValue + 1;

				var arrowOffsetY = yValue / yMax * this._barHeight;

				if (parseInt(arrowOffsetY) == (yMax-1)) 
					arrowOffsetY=yMax;
				else
					arrowOffsetY=parseInt(arrowOffsetY);

				if (this.settings.yMinValue < 1)  {
					arrowOffsetY = arrowOffsetY - Math.abs(this.settings.yMinValue) - 1;
				}
			}
		}

		this._setArrowPosition(arrowOffsetX, arrowOffsetY);

	},
	_setArrowPosition: function(offsetX, offsetY) {
		
		
		// validate
		if (offsetX < 0) offsetX = 0
		if (offsetX > this._barWidth) offsetX = this._barWidth;
		if (offsetY < 0) offsetY = 0
		if (offsetY > this._barHeight) offsetY = this._barHeight;	

		var posX = this._barLeft + offsetX;
		var posY = this._barTop + offsetY;

		// check if the arrow is bigger than the bar area
		if (this._arrowWidth > this._barWidth) {
			posX = posX - (this._arrowWidth/2 - this._barWidth/2);
		} else {
			posX = posX - parseInt(this._arrowWidth/2);
		}
		if (this._arrowHeight > this._barHeight) {
			posY = posY - (this._arrowHeight/2 - this._barHeight/2);
		} else {
			posY = posY - parseInt(this._arrowHeight/2);
		}
		this._arrow.style.left = posX + 'px';
		this._arrow.style.top = posY + 'px';	
	},
	_bar_mouseDown: function(e) {
		this._mouseDown(e);
	},
	
	_arrow_mouseDown: function(e) {
		this._mouseDown(e);
	},
	
	_mouseDown: function(e) {
		Refresh.Web.ActiveSlider = this;
		
		this.setValuesFromMousePosition(e);
		
		document.addEventListener('mousemove', this._event_docMouseMove, false);
		document.addEventListener('mouseup', this._event_docMouseUp, false);
		e.stopPropagation();
		e.preventDefault();
	},
	
	_docMouseMove: function(e) {

		this.setValuesFromMousePosition(e);
		e.stopPropagation();
		e.preventDefault();
	},
	
	_docMouseUp: function(e) {
		document.removeEventListener('mouseup', this._event_docMouseUp, false);
		document.removeEventListener('mousemove', this._event_docMouseMove, false);
		e.stopPropagation();
		e.preventDefault();
	},	
	
	setValuesFromMousePosition: function(e) {
		//this.setPositioningVariables();
		
	
		var docElement = document.documentElement;
		var mouse = {
		  x: e.pageX || (e.clientX + 
		    (docElement.scrollLeft || 0) -
		    (docElement.clientLeft || 0)),
		  y: e.pageY || (e.clientY + 
		    (docElement.scrollTop || 0) -
		    (docElement.clientTop || 0))
		};

		var relativeX = 0;
		var relativeY = 0;

		// mouse relative to object's top left
		if (mouse.x < this._barLeft)
			relativeX = 0;
		else if (mouse.x > this._barRight)
			relativeX = this._barWidth;
		else
			relativeX = mouse.x - this._barLeft + 1;

		if (mouse.y < this._barTop)
			relativeY = 0;
		else if (mouse.y > this._barBottom)
			relativeY = this._barHeight;
		else
			relativeY = mouse.y - this._barTop + 1;
			

		var newXValue = parseInt(relativeX / this._barWidth * this.settings.xMaxValue);
		var newYValue = parseInt(relativeY / this._barHeight * this.settings.yMaxValue);
		
		// set values
		this.xValue = newXValue;
		this.yValue = newYValue;	

		// position arrow
		if (this.settings.xMaxValue == this.settings.xMinValue)
			relativeX = 0;
		if (this.settings.yMaxValue == this.settings.yMinValue)
			relativeY = 0;		
		this._setArrowPosition(relativeX, relativeY);

		// fire events
		if(this.onValuesChanged)
			this.onValuesChanged(this);
	}	

}



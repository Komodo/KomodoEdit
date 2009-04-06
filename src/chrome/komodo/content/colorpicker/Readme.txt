Photoshop-like Color Picker
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Author:  John Dyer
License: MIT

This is a pure JavaScript PhotoShop-like color picker. The original author
of the code is "John Dyer", who posted the color picker and articles on his
website:
http://johndyer.name/post/2007/09/PhotoShop-like-JavaScript-Color-Picker.aspx

The color picker images are included in Komodo's "skin/images/colorpicker"
folder.

The original color picker code made use of Prototype (JavaScript library) for:
  1) Class.create syntax
  2) $() function
  3) Event.observe/stopObserving functionality
  4) positioning methods for the sliders

these Prototype methods were replaced with the equivalent pure JS functionality.

A simple XPCOM wrapper was created "xpcom_colorpicker.js" to provide the color
picker functionality through XPCOM.

The default Mozilla "colorpicker" element binding, which provides a swatch of
color buttons (50 or so colors) has been overriden to make use of this new
colorpicker dialog.

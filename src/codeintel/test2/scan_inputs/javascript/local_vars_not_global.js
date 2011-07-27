/* Make sure function-local variables do not leak into the global scope */
function myfunc(view) {
  var scimoz = view.scimoz;
  scimoz.anchor = 1;
  scimoz.currentPos = 2;
}

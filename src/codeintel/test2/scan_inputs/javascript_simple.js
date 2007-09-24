/* Copyright (c) 2000-2006 ActiveState Software Inc.

/* Use this sample to explore editing JavaScript with Komodo. */

function myfunc() {
    this.classVar1 = "MyFunc";
    this.num = 1;
}

myfunc.prototype.list = function()
{
    // Do whatever you do
}

myfunc.prototype.strFunc = function(s /* s is a string */)
{
    var copyOfS = s;
    if (this.classVar1 == s) {
        this.classVar1 = copyOfS;
    }
    this.num = 2;
    // Do whatever you do
}

var mf = new myfunc();
var s = mf.classVar1;
mf.list();
mf.num = 4;
mf.strFunc(s);
gNum = 5;


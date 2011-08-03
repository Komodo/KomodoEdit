// This should create a namespace if one does not already exist.
var mynamespace;
if (window)
{
    if (!mynamespace) mynamespace = {};
    mynamespace.foo = "foo";
}

const {classes: Cc, interfaces: Ci, utils: Cu} = Components;
Cu.import("resource://komodo-jstest/JSTest.jsm");
var {stringutils} = Cu.import("chrome://komodo/content/library/stringutils.js", {});

function StringUtilsTestCase() {}
StringUtilsTestCase.prototype.__proto__ = TestCase.prototype;

StringUtilsTestCase.prototype.test_getSubAttr =
    function StringUtilsTestCase_test_getSubAttr()
{
    // test for invalid input
    this.assertRaises(Cu.getGlobalForObject(stringutils).Error,
                      stringutils.getSubAttr,
                      ["value", "attrname"],
                      "stringutils.getSubAttr expected to throw on invalid value");

    // test basic inputs
    this.assertEquals(stringutils.getSubAttr("key: value", "key"), "value");
    this.assertEquals(stringutils.getSubAttr("key: value;", "key"), "value");

    // test for whitespace variations
    this.assertEquals(stringutils.getSubAttr("key:value", "key"), "value");
    this.assertEquals(stringutils.getSubAttr("key:value ", "key"), "value");
    this.assertEquals(stringutils.getSubAttr("key: value ", "key"), "value");
    this.assertEquals(stringutils.getSubAttr("key  : value ", "key"), "value");
    this.assertEquals(stringutils.getSubAttr("\nkey\n:\nvalue\n", "key"), "value");
    this.assertEquals(stringutils.getSubAttr("\tkey\t:\tvalue\t", "key"), "value");

    // test getting first/not-first items
    this.assertEquals(stringutils.getSubAttr("key: value; key2: value2", "key"),
                      "value");
    this.assertEquals(stringutils.getSubAttr("key: value; key: value2;", "key"),
                      "value",
                      "stringutils.getSubAttr should prefer first match");
    this.assertEquals(stringutils.getSubAttr("key: value; key2: value2", "key2"),
                      "value2");
    this.assertEquals(stringutils.getSubAttr("key: value; key2: value2;", "key2"),
                      "value2");

    // test getting quoted values
    this.assertEquals(stringutils.getSubAttr("key: 'value'", "key"), "value");
    this.assertEquals(stringutils.getSubAttr('key: "value"', "key"), "value");
    this.assertEquals(stringutils.getSubAttr("key: 'value\"'", "key"), 'value"');
    this.assertEquals(stringutils.getSubAttr("key: 'value", "key"), null); // unterminated
    this.assertEquals(stringutils.getSubAttr('key: "value', "key"), null); // unterminated
    this.assertEquals(stringutils.getSubAttr("key: 'value; key2: value2", "key2"),
                      null); // unterminated

    // test quoted values with semicolons
    this.assertEquals(stringutils.getSubAttr("key: 'value; key2: value2'; key2: value3", "key"),
                      "value; key2: value2");
    this.assertEquals(stringutils.getSubAttr("key: 'value; key2: value2'; key2: value3", "key2"),
                      "value3");
};

var JS_TESTS = ["StringUtilsTestCase"];

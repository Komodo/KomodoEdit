This directory contains mock implementations of various ko.* things; they can
be used by importing:

  var ko = {};
  // The following line imports ko.views and ko.stringutils
  Components.utils.import("resource://komodo-jstest/mock/mock.jsm", {}).import(ko, "views", "stringutils");

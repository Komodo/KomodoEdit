# Komodo IDE SDK Reference

The Komodo IDE SDK Reference describes each available resource in the Komodo API.

## Overview

The Komodo SDK uses the `require('module')` function from the CommonJS specification to load JavaScript files on demand.

Komodo's `require` functionality is built on top of the Mozilla Add-on SDK, so most of the APIs defined by Mozilla can be used by Komodo. The exceptions are browser specific functionality, such as the Firefox browser having web page tabs.

Example of loading the `ko/logging` API:

```JavaScript
var logging = require("ko/logging");

```

Example of retrieving the language of the current file:

```JavaScript
var language = require("ko/editor").getLanguage();

```

The `.getLanguage()` function is defined in the `ko/editor` API documented [here](module-ko_editor.html#.getLanguage__anchor).

## Komodo APIs

Use the Modules, Classes, and Global menus in the navigation bar at the top of the page to browse the APIs available in the Komodo IDE SDK.

## Mozilla APIs

- [High-level APIs](https://developer.mozilla.org/en-US/Add-ons/SDK/High-Level_APIs): Contains APIs for creating user interfaces and interacting with the web.
- [Low-level APIs](https://developer.mozilla.org/en-US/Add-ons/SDK/Low-Level_APIs): Contains utilities, building blocks for higher level modules, and privileged modules for low-level capabilities.

**Note**: Some of the high-level APIs will not work in Komodo.

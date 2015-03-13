# Copyright (c) 2000-2011 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import os, sys, logging

# Some MH hacks to avoid duplicate files.
# "Face.py" and 'Scintilla.iface' are in the scintilla directory
# As this is also under ActiveState source control, preventing
# duplicate files ensures that SciMoz is definately in synch with
# the relevant scintilla!

scintillaIncPath = ""
scintillaScriptsPath = ""

log = logging.getLogger("xpfacer")

try:
    import Face
except ImportError:
    scintillaIncPath = os.path.abspath(
                os.path.join(
                    os.path.split(sys.argv[0])[0], "../scintilla/include"
                ))
    scintillaScriptsPath = os.path.abspath(
                os.path.join(
                    os.path.split(sys.argv[0])[0], "../scintilla/scripts"
                ))
    if not os.path.isfile(os.path.join(scintillaIncPath,"Scintilla.iface")):
        print "WARNING: Expecting to find 'Face.py' and 'Scintilla.iface' in path"
        print scintillaIncPath, ", but I can't. "
        print "I'm probably gunna fail real-soon-now!"
    sys.path.insert(0, scintillaIncPath)
    sys.path.insert(1, scintillaScriptsPath)
    import Face

manualFunctions = """
    doBraceMatch markClosed hookEvents unhookEvents getStyledText getCurLine getLine
    getStyleRange assignCmdKey clearCmdKey getTextRange charPosAtPosition
    sendUpdateCommands getWCharAt addChar buttonDown buttonUp buttonMove endDrop
    annotationRemoveAtLine updateMarginWidths markerDefineRGBAImage
    enablePluginVisibilityHack
    """.split()
""" Implemented by hand
    note: items returning strings or complex types are easier to
    manage when we implement them by hand.
    """

textAndLengthFunctions = """
    addText addStyledText replaceTarget replaceTargetRE searchInTarget appendText
    """.split()
""" Functions taking arguments of the form (length, text); these are converted
    to taking a single UTF8 string instead.
    """

discardedFeatures = """
    formatRange findText
    """.split()
""" These Scintilla features are not needed for SciMoz
    """

manualGetterProperties = {
    "text": {
        "ReturnType": "string",
        "code": """
            nsString gettext;
            GetText(gettext);
            if (gettext.IsVoid()) {
                NULL_TO_NPVARIANT(*result);
            } else {
                NS_ConvertUTF16toUTF8 cachedTextUtf8(gettext);
                NPUTF8 *p = reinterpret_cast<NPUTF8*>(NPN_MemAlloc(cachedTextUtf8.Length()));
                if (!p) {
                    return false;
                }
                memcpy(p, cachedTextUtf8.BeginReading(), cachedTextUtf8.Length());
                STRINGN_TO_NPVARIANT(p, cachedTextUtf8.Length(), *result);
            }
            return true;
            """
    },
    "textId": {
        "ReturnType": "long",
        "code": """
            int32_t myresult;
            GetTextId(&myresult);
            INT32_TO_NPVARIANT(myresult, *result);
            return true;
            """,
    },
    "selText": {
        "ReturnType": "string",
        "code": """
            int min = SendEditor(SCI_GETSELECTIONSTART, 0, 0);
            int max = SendEditor(SCI_GETSELECTIONEND, 0, 0);
            size_t length = max - min;
            char *buffer = (char *) NPN_MemAlloc((length + 1) * sizeof(char));
            if (!buffer) {
                return false;
            }
            buffer[length] = 0;
            #ifdef USE_SCIN_DIRECT
                ::GetTextRange(fnEditor, ptrEditor, min, max, buffer);
            #else
                ::GetTextRange(wEditor, min, max, buffer);
            #endif
            NS_ASSERTION(buffer[length] == NULL, "Buffer overflow");

            STRINGN_TO_NPVARIANT(buffer, length, %(target)s);
            return true;
            """
    },
    "isOwned": {
        "ReturnType": "bool",
        "code": """
            bool myresult;
            GetIsOwned(&myresult);
            BOOLEAN_TO_NPVARIANT(myresult, *result);
            return true;
            """,
    },
    "visible": {
        "ReturnType": "bool",
        "code": """
            bool myresult;
            GetVisible(&myresult);
            BOOLEAN_TO_NPVARIANT(myresult, *result);
            return true;
            """,
    },
    "isFocused": {
        "ReturnType": "bool",
        "code": """
            BOOLEAN_TO_NPVARIANT(!!SendEditor(SCI_GETFOCUS, 0, 0), *result);
            return true;
            """
    },
    "name": {
        "ReturnType": "string",
        "code": """
            NS_ConvertUTF16toUTF8 nameUtf8(name);
            NPUTF8 *p = reinterpret_cast<NPUTF8*>(NPN_MemAlloc(nameUtf8.Length()));
            if (!p) {
                return false;
            }
            memcpy(p, nameUtf8.BeginReading(), nameUtf8.Length());
            STRINGN_TO_NPVARIANT(p, nameUtf8.Length(), *result);
            return true;
            """
    },
    "isTracking": {
        "ReturnType": "bool",
        "code": """
            bool myresult;
            GetIsTracking(&myresult);
            BOOLEAN_TO_NPVARIANT(myresult, *result);
            return true;
            """,
    },
    "inDragSession": {
        "ReturnType": "bool",
        "code": """
            bool myresult;
            GetInDragSession(&myresult);
            BOOLEAN_TO_NPVARIANT(myresult, *result);
            return true;
            """,
    },
    "wordChars": {
        # this needs a manual getter because the scintilla method returns an int
        # plus a stringresult, which we can't deal with automatically yet (the
        # stringresult argument confuses it into being a function instead of a
        # getter)
        "ReturnType": "string",
        "code": """
            size_t length = SendEditor(SCI_GETWORDCHARS, 0, 0);
            char *bufBytes = reinterpret_cast<char*>(NPN_MemAlloc(length));
            if (!bufBytes) {
                return false;
            }
            SendEditor(SCI_GETWORDCHARS, 0, reinterpret_cast<long>(bufBytes));
            // Scintilla actually gives raw bytes; we need to convert it to UTF8
            // for use by NPAPI/NPRuntime.
            NS_ConvertASCIItoUTF16 buf16(nsDependentCString(bufBytes, length));
            NPN_MemFree(bufBytes);
            NS_ConvertUTF16toUTF8 buf8(buf16);
            NPUTF8 *p = reinterpret_cast<NPUTF8*>(NPN_MemAlloc(buf8.Length()));
            if (!p) {
                return false;
            }
            memcpy(p, buf8.BeginReading(), buf8.Length());
            STRINGN_TO_NPVARIANT(p, buf8.Length(), %(target)s);
            return true;
            """,
    },
}
""" manually-implemented getters """

manualSetterProperties = {
    "setText": {
        "code": """
            if (!NPVARIANT_IS_STRING(*value)) return false;
            const NPString &strVal = NPVARIANT_TO_STRING(*value);
            NS_ConvertUTF8toUTF16 text(strVal.UTF8Characters,
                                       strVal.UTF8Length);
            nsresult rv = SetText(text);
            return NS_SUCCEEDED(rv);
            """
    },
    "setVisible": {
        "code": """
            if (!NPVARIANT_IS_BOOLEAN(*value)) return false;
            nsresult rv = SetVisible(NPVARIANT_TO_BOOLEAN(*value));
            return NS_SUCCEEDED(rv);
            """
    },
    "setIsFocused": {
        "code": """
            if (!NPVARIANT_IS_BOOLEAN(*value)) return false;
            SendEditor(SCI_SETFOCUS, NPVARIANT_TO_BOOLEAN(*value), 0);
            return true;
            """
    },
    "setName": {
        "code": """
            if (!NPVARIANT_IS_STRING(*value)) return false;
            const NPString &strVal = NPVARIANT_TO_STRING(*value);
            NS_ConvertUTF8toUTF16 name(strVal.UTF8Characters,
                                       strVal.UTF8Length);
            nsresult rv = SetName(name);
            return NS_SUCCEEDED(rv);
            """
    },
    "SetModEventMask": {
        # We override the modEventMask handling in order to workaround a
        # "scimoz.text" problem, where the scimoz text attribute does not
        # return the correct contents. The terminal-view's turn off the
        # modEventMask, which results in SciMoz not voiding the cached text it
        # holds - resulting in stale text. To work around this SciMoz overrides
        # this method and manually nulls the text when the eventmask is
        # changed. Bug 85194.

        "code": """
            /* arg 0 of type int */
            if (!NPVARIANT_IS_INT32(*value)) {
                #ifdef SCIMOZ_DEBUG
                    printf("modEventMask setter: arg 0 has invalid type %%i",
                           (*value).type);
                #endif
                return false;
            }
            nsresult rv = SetModEventMask(NPVARIANT_TO_INT32(*value));
            return NS_SUCCEEDED(rv);
            """
    },
}
""" manually implemented setters """

def _(lines, indent=0, replacements=None, file=None):
    """
    Writes the given lines to the file, attempting to do formatting
    @param lines: a sequence of lines to write
    @param indent: the indent to place in front of each line
    @param replacements: an optional hash for string replacements
    @param file: the file to write to (or None to not write)
    @return The resulting lines as a sequence
    """
    if replacements is None:
        replacements = {}
    if isinstance(lines, str):
        # got a string instead of individual lines
        lines = lines.split("\n")
    if len(lines) < 1:
        # no input, do nothing
        return []

    # the number of spaces the source was indented by
    src_indent = len(lines[-1]) - len(lines[-1].lstrip())

    for idx, line in enumerate(lines):
        line = line % replacements
        # un-indent by the source indent
        lines[idx] = line[:src_indent].lstrip() + line[src_indent:]
    # drop empty lines at start and end
    if lines[0] == "" and len(lines) > 1:
        lines.pop(0)
    if lines[-1] == "":
        lines.pop(-1)

    lines = map(lambda line: (" " * indent) + line, lines)
    if file is not None:
        # write to the file
        file.write("%s\n" % "\n".join(lines))
    return lines

def interCaps(name, upper=0):
    if upper:
        return name[0].upper() + name[1:]
    else:
        return name[0].lower() + name[1:]

def idlName(ifaceName, cxxVersion=False):
    x = ifaceName.find("Get")
    # If "Get" appears later in the name - remove it.
    if cxxVersion and x > 0:
        ifaceName = "Get" + ifaceName[:x]+ifaceName[x+3:]
    # If "Set" appears later in the name - remove it.
    x = ifaceName.find("Set")
    if cxxVersion and x > 0:
        ifaceName = "Set" + ifaceName[:x]+ifaceName[x+3:]
    return interCaps(ifaceName)

def DEFINEName(ifaceName):
    """ return the name used in C++ #defines """
    featureDefineName = ifaceName.upper()
    if "_" not in featureDefineName:
            featureDefineName = "SCI_" + featureDefineName
    return featureDefineName

def attributeName(name):
    """
    converts a name to the version used as an xpidl attribute
    """
    if name.lower().startswith("get"):
        return idlName(name[len("get"):])
    if name.lower().startswith("set"):
        return idlName(name[len("set"):])
    # look for "Get" and "Set" in the middle of the word. but only if the first
    # letter is upper case, to avoid matching "offset"
    x = name.find("Get")
    if x != -1:
        return idlName(name[:x]+name[x+3:])
    x = name.find("Set")
    if x != -1:
        return idlName(name[:x]+name[x+3:])
    return idlName(name)

def getterVersion(feature, face):
    """
    Given a setter feature, find the matching getter feature
    """
    if isinstance(feature, str):
        assert feature in face.features, \
            "Can't find getter for unknown setter %s" % (feature)
        feature = face.features[feature]
    if feature["FeatureType"] == "get":
        return feature
    name = feature["Name"]
    if name.startswith("set"):
        name = "get" + name[len("set"):]
    elif name.find("Set") != -1:
        x = name.find("Set")
        name = name[:x] + "Get" + name[x+3:]
    else:
        name = "get" + name
    if name in face.features:
        return face.features[name]
    return None

def setterVersion(feature, face):
    """
    Given a getter feature, find the matching setter feature
    """
    if isinstance(feature, str):
        assert feature in face.features, \
            "Can't find setter for unknown getter %s" % (feature)
        feature = face.features[feature]
    if feature["FeatureType"] == "set":
        return feature
    name = feature["Name"]
    if name.startswith("get"):
        name = "set" + name[len("get"):]
    elif name.find("Get") != -1:
        x = name.find("Get")
        name = name[:x] + "Set" + name[x+3:]
    else:
        name = "set" + name
    if name in face.features:
        return face.features[name]
    return None

def fixup_iface_data(face):
    """
    Fixes inconsistencies in the scintilla face definition, and map getters and
    setters
    @param face: The scintilla interface definition structure
    """
    for name in face.features.keys():
        feature = face.features[name]
        log.debug("Fixing up feature %s: %r", name, feature)
        if not "Name" in feature:
            feature["Name"] = name

        # save the param types as a list to be easier to manage later
        feature["Params"] = []
        if "Param1Type" in feature:
            feature["Params"].append({
                "Type": feature["Param1Type"] or "void",
                "Name": feature["Param1Name"],
                "Value": feature["Param1Value"]
            })
        if "Param2Type" in feature:
            feature["Params"].append({
                "Type": feature["Param2Type"] or "void",
                "Name": feature["Param2Name"],
                "Value": feature["Param2Value"]
            })
        feature["ParamCount"] = \
            len(filter(lambda p: p["Type"] != "void", feature["Params"]))

        if feature["FeatureType"] == "get":
            if attributeName(name) in manualGetterProperties.keys():
                # this has a matching manual getter, skip it
                del face.features[name]
                if name in face.order:
                    face.order.remove(name)
                continue
            if feature["ParamCount"] != 0:
                # this is a getter with an arg; treat as function
                feature["FeatureType"] = "fun"
            else:
                setter = setterVersion(feature, face)
                if setter and setter["FeatureType"] == "set":
                    feature["MatchingFeature"] = setterVersion(feature, face)
                else:
                    # This getter has no matching setter / has an invalid setter
                    feature["MatchingFeature"] = None

        if feature["FeatureType"] == "set":
            if attributeName(name) in manualSetterProperties.keys():
                # this has a matching manual setter, skip it
                del face.features[name]
                if name in face.order:
                    face.order.remove(name)
                continue
            getter = getterVersion(feature, face)
            feature["MatchingFeature"] = None
            if feature["ParamCount"] != 1:
                # this is a setter with zero or two args; treat as function
                feature["FeatureType"] = "fun"
                if getter is not None:
                    getter["MatchingFeature"] = None
            else:
                if getter is not None:
                    feature["MatchingFeature"] = getter
                else:
                    # setter with no getter? actually a function, again...
                    feature["FeatureType"] = "fun"

        if feature["FeatureType"] == "fun":
            if attributeName(feature["Name"]) in manualGetterProperties.keys():
                if not idlName(feature["Name"]) in manualFunctions:
                    feature["FeatureType"] = "overridden"

    # loop again, and check for setters with no getters
    for feature in face.features.values():
        if feature["FeatureType"] != "set":
            continue
        if feature["MatchingFeature"]["FeatureType"] != "get":
            # this feature has a matching getter... except that getter is a function
            feature["MatchingFeature"] = None
            feature["FeatureType"] = "fun"

    # add in the manually implemented getters
    for name, feature in manualGetterProperties.items():
        feature["Name"] = name
        feature["FeatureType"] = "get"
        feature["MatchingFeature"] = None
        feature["suppressIdl"] = True
        face.features[name] = feature
        if not name in face.order:
            face.order.append(name)

    # add in the manually implemented setters
    for name, feature in manualSetterProperties.items():
        feature["Name"] = name
        feature["FeatureType"] = "set"
        feature["MatchingFeature"] = getterVersion(feature, face)
        if feature["MatchingFeature"] is not None:
            feature["MatchingFeature"]["MatchingFeature"] = feature
        feature["suppressIdl"] = True
        face.features[name] = feature
        if not name in face.order:
            face.order.append(name)

def generate_idl_constants_fragment(face):
    """
    Generate the constant definitions for the XPCOM interface
    @param face: The scintilla interface definition structure
    """
    unwantedValues = ["SCI_START", "SCI_OPTIONAL_START", "SCI_LEXER_START"]
    outputfile = file("ISciMoz_gen.consts.fragment", "w")
    print "Dumping ISciMoz interface constants to %s" % outputfile.name
    outputfile.write("%{C++\n#ifndef SCINTILLA_HIDE_DEFINES\n%}\n")
    for name in face.order:
        if name in unwantedValues:
            # we don't want to expose this constant
            continue
        feature = face.features[name]
        if feature["FeatureType"] == "val":
            value = feature["Value"]
            if "Comment" in feature:
                _(map(lambda x: "// " + x, feature["Comment"]), 8, file=outputfile)
            _("const %(unsigned)slong %(name)s = %(value)s;",
              8,
              replacements={
                "name": name,
                "value": value,
                # We must use an unsigned long large hex values, like
                #   "SC_MASK_FOLDERS = 0xFE000000"
                "unsigned": "unsigned " if len(value) >= 10 and value.startswith("0x") else ""
              },
              file=outputfile)
    outputfile.write("%{C++\n#endif\n%}\n")

def generate_idl_method_fragment(feature, file, indent=8):
    """
    Generate a single method definition in an idl file
    @param feature: the feature definition
    @param file: the file to write to
    @return: number of slots taken
    """
    if "Comment" in feature:
        _(map(lambda x: "// " + x, feature["Comment"]), indent, file=file)
    args = []
    missingType = None
    for param in feature["Params"]:
        if param["Type"] == "void":
            continue
        if not param["Type"] in typeInfo:
            missingType = param["Type"]
        else:
            args.append("%s %s %s" % (
                typeInfo[param["Type"]]["idlDirection"],
                typeInfo[param["Type"]]["idlType"],
                param["Name"]))

    if idlName(feature["Name"]) in textAndLengthFunctions:
        # This is a function which takes a string length follow by a string
        # prefer just getting a single string instead, for better API in
        # JavaScript and Python
        assert len(feature["Params"]) == 2
        assert typeInfo[feature["Params"][0]["Type"]]["idlDirection"] == "in"
        assert typeInfo[feature["Params"][0]["Type"]]["idlType"] == "long"
        assert typeInfo[feature["Params"][1]["Type"]]["idlDirection"] == "in"
        args = ["in nsIVariant text_or_length",
                "[optional] in AString text_deprecated"]

    log.debug("Writing IDL method %s", feature.get("Name"))
    if missingType is not None:
        _("/* method %(name)s has missing type %(type)s */",
          indent,
          replacements={
            "name": idlName(feature["Name"]),
            "type": missingType
          },
          file=file)
    else:
        _("%(returnType)s %(name)s(%(args)s);",
          indent,
          replacements={
            "returnType": typeInfo[feature["ReturnType"] or "void"]["idlType"],
            "name":       idlName(feature["Name"]),
            "args":       ", ".join(args)
          },
          file=file)

    # methods always take up one slot only
    return 1

def generate_idl_attribute_fragment(feature, file, indent=8):
    """
    Generate a single attribute definition in an idl file
    @param feature: the feature definition
    @param file: the file to write to
    @return: number of slots taken
    """

    if "suppressIdl" in feature:
        # don't generate this feature in the idl (usually because it's hand-
        # written and this is a manual getter)
        log.debug("Skipping IDL attribute %s", feature.get("Name"))
        return 0

    if "Comment" in feature:
        _(map(lambda x: "// " + x, feature["Comment"]), 8, file=file)

    assert feature["ReturnType"] in typeInfo, \
        "idl type for return type %s missing while generating attribute %s" % (
            feature["ReturnType"], feature["Name"])

    log.debug("Writing IDL attribute %s", feature.get("Name"))
    _("%(readonly)sattribute %(type)s %(name)s;",
      file=file,
      indent=indent,
      replacements={
        "readonly": (feature["MatchingFeature"] is None) and "readonly " or "",
        "type":     typeInfo[feature["ReturnType"]]["idlType"],
        "name":     attributeName(feature["Name"])
      })

    # attributes take two slots if not readonly
    if feature["MatchingFeature"] is None:
        return 1
    return 2

def generate_idl_lite_fragment(face):
    """
    Generate the ISciMozLite interface fragment
    @param face: the scintilla interface definition structure
    """
    outputfile = file("ISciMoz_lite_gen.idl.fragment", "w")
    print "Dumping ISciMoz 'lite' inteface to %s" % outputfile.name
    liteFeatures = str.split("""
        addText insertText length currentPos anchor selectAll gotoLine
        gotoPos startStyling setStyling markerAdd markerNext styleSetFore
        readOnly selectionStart selectionEnd hideSelection replaceSel
        scrollWidth deleteBack newLine xOffset lineFromPosition
        pointXFromPosition pointYFromPosition textHeight
        beginUndoAction endUndoAction undoCollection undo
        charPositionFromPointClose getLineEndPosition positionFromLine
        positionAfter positionAtChar
        """)
    for name in face.order:
        if not (idlName(name) in liteFeatures or attributeName(name) in liteFeatures):
            continue
        if idlName(name) in manualFunctions:
            continue
        feature = face.features[name]
        if feature["FeatureType"] == "fun":
            generate_idl_method_fragment(feature, outputfile)
        elif feature["FeatureType"] == "get":
            generate_idl_attribute_fragment(feature, outputfile)
        elif feature["FeatureType"] == "set":
            # don't do anything with setters, we generate attributes on the
            # matching getter (and there are no writeonly attributes)
            pass
        else:
            # dunno what this is, not touching
            continue
        feature["isLite"] = True # don't duplicate in non-lite interface

def generate_idl_full_fragment(face):
    """
    Generate the ISciMoz interface fragment
    @param face: the scintilla interface definition structure
    """

    suppressedFeatures = """
        getStyledText getCurLine assignCmdKey clearCmdKey getLine getTextRange
        charPosAtPosition
    """.split()

    outputfile = file("ISciMoz_gen.idl.fragment", "w")
    static_guids = [  # Keep the GUIDs the same across builds.
        "a53c386b-99e2-4b2e-85e7-fb5a29322369",
        "4645e5bd-4cd1-44dc-9d70-00b38dc87d29",
        "52a719ee-a335-4da8-8b83-d83b38257239",
        "70c2de0f-2935-481b-a034-9d4426d5f77c",
        "2d6994c8-f637-438b-82dc-89ffbe0d42b8",
        "2a3167f7-7e46-4e5d-8126-23f71142d987",
        "cea8e58f-1f27-41cd-b16b-3a463f28d25a",
        "2d5da494-7942-4fac-923c-42e9b01ab5e5",
        "bfcfe675-77f8-4a55-ae90-4e70f395bc7b",
        "bbd11f0d-262a-46a9-9c98-321397b42567",
    ]
    idlTemplateHead = """
        [scriptable, uuid(%s)]
        interface ISciMoz_Part%i : nsISupports {
        """
    idlTemplateTail = """};"""
    interfaceCount = 0
    slotCount = 0

    print "Dumping ISciMoz inteface to %s" % outputfile.name
    _(idlTemplateHead % (static_guids[interfaceCount], interfaceCount), file=outputfile)
    for name in face.order:
        if idlName(name) in suppressedFeatures:
            # don't write this out - either we don't use it, or it conflicts
            # with something else
            continue
        feature = face.features[name]
        if "isLite" in feature:
            # this is a Lite feature, skip it
            continue
        if idlName(name) in manualFunctions:
            continue
        if feature["FeatureType"] == "fun":
            slotCount += generate_idl_method_fragment(feature, outputfile)
        elif feature["FeatureType"] == "get":
            slotCount += generate_idl_attribute_fragment(feature, outputfile)
        elif feature["FeatureType"] == "set":
            # don't do anything with setters, we generate attributes on the
            # matching getter (and there are no writeonly attributes)
            pass
        else:
            # didn't do anything with this one
            continue
        if slotCount > 150:
            # too many methods on this interface, make a new one
            # we actually support ~ 240 or so, but things from the ancestor
            # interfaces count too
            slotCount = 0
            interfaceCount += 1
            _(idlTemplateTail, file=outputfile)
            _(idlTemplateHead % (static_guids[interfaceCount], interfaceCount), file=outputfile)
    _(idlTemplateTail, file=outputfile)
    generate_wrapper(face, interfaceCount)

def generate_cxx_xpcom_method_fragment(feature, file):
    """
    Generate a C++ XPCOM stub for a fun feature
    @param feature: the feature definition
    @param file: the file to write to
    """
    _("#if 0", file=file, indent=4)
    generate_idl_method_fragment(feature, file, 8);
    _("#endif", file=file, indent=4)
    args = []
    sciApiName = DEFINEName(feature["Name"])
    sciArgs = [sciApiName]
    pre = ""
    post = ""
    cxxGetterResultOverride = None
    for param in feature["Params"]:
        if param["Type"] == "void":
            # scintilla takes an empty param at this position
            sciArgs.append("0")
            continue
        assert param["Type"] in typeInfo, \
            "No type info for type %s while generating %s" % (
                param["Type"], feature["Name"])
        info = typeInfo[param["Type"]]
        assert "cxxParamType" in info, \
            "No C++ param type available for type %s while generating %s" % (
                param["Type"], feature["Name"])
        args.append("%s %s" % (info["cxxParamType"], param["Name"]))
        assert "xpcomToSci" in info, \
            "No conversion available for type %s from XPCOM to Scintilla while generating %s" % (
                param["Type"], feature["Name"])
        sciArgs.append(" ".join(_(info["xpcomToSci"],
                                  replacements={
                                    "var": param["Name"]})))
        pre += " ".join(_(info.get("xpcomToSciPre", ""),
                                  replacements={
                                    "var": param["Name"]}))
        post += " ".join(_(info.get("xpcomToSciPost", ""),
                                  replacements={
                                    "var": param["Name"]}))
    returnsetter = ""
    if feature["ReturnType"] != "void":
        assert feature["ReturnType"] in typeInfo, \
            "No type info for return type %s while generating %s" % (
                feature["ReturnType"], feature["Name"])
        info = typeInfo[feature["ReturnType"]]
        assert "cxxReturnType" in info, \
            "No C++ return type available for %s while generating %s" % (
                feature["ReturnType"], feature["Name"])
        returnsetter = "*_retval = "
        args.append("%s _retval" % (info["cxxReturnType"]))
        if "cxxGetterResultOverride" in info:
            cxxGetterResultOverride = info.get("cxxGetterResultOverride", "")
    replacements = {
        "name": interCaps(idlName(feature["Name"]), 1),
        "args": ", ".join(args),
        "pre": pre,
        "post": post,
        "returnsetter": returnsetter,
        "sciArgs": ", ".join(sciArgs),
        "sciApiName": sciApiName,
    }

    resultline = "%(returnsetter)sSendEditor(%(sciArgs)s);"
    if cxxGetterResultOverride:
        resultline = cxxGetterResultOverride

    if idlName(feature["Name"]) in textAndLengthFunctions:
        args = ["nsIVariant* v", "const nsAString& t"]
        replacements["has_return"] = "0"
        if feature["ReturnType"] == "int":
            args.append("int32_t *_retval")
            replacements["has_return"] = "1"
        replacements["args"] = ", ".join(args)
        resultline = """
            nsresult rv;
            int32_t result;
            nsAutoString text;
            if (t.IsVoid()) {
                // Only one argument used, variant should be a string.
                rv = v->GetAsAString(text);
                NS_ENSURE_SUCCESS(rv, rv);
            } else {
                // Two arguments, we only want the string (second argument).
                text = t;
            }
            NS_ConvertUTF16toUTF8 textUtf8(text);
            result = SendEditor(%(sciApiName)s, textUtf8.Length(),
                                reinterpret_cast<long>(textUtf8.get()));
            #if %(has_return)s
                *_retval = result;
            #endif /* %(has_return)s */
        """

    _(r"""
        NS_IMETHODIMP SciMoz::%(name)s(%(args)s) {
            #ifdef SCIMOZ_DEBUG_VERBOSE
                printf("SciMoz::%(name)s\n");
            #endif
            SCIMOZ_CHECK_VALID("%(name)s")
            %(pre)s""" + resultline + """%(post)s
            return NS_OK;
        }

        """,
      replacements=replacements,
      file=file)

def generate_cxx_xpcom_attribute_fragment(feature, file, mode="Get"):
    """
    Generate a C++ XPCOM stub for a get/set feature
    @param feature: the feature definition
    @param file: the file to write to
    """
    _("#if 0", file=file, indent=4)
    generate_idl_attribute_fragment(feature, file, 8);
    _("#endif", file=file, indent=4)
    args = []
    sciApiName = DEFINEName(feature["Name"])
    sciArgs = [sciApiName]
    if feature["Name"] in manualGetterProperties or feature["Name"] in manualSetterProperties:
        return
    pre = ""
    post = ""
    cxxGetterResultOverride = None
    for param in feature["Params"]:
        if param["Type"] == "void":
            # scintilla takes an empty param at this position
            sciArgs.append("0")
            continue
        assert param["Type"] in typeInfo, \
            "No type info for type %s while generating %s" % (
                param["Type"], feature["Name"])
        info = typeInfo[param["Type"]]
        assert "cxxParamType" in info, \
            "No C++ param type available for type %s while generating %s" % (
                param["Type"], feature["Name"])
        args.append("%s %s" % (info["cxxParamType"], param["Name"]))
        assert "xpcomToSci" in info, \
            "No conversion available for type %s from XPCOM to Scintilla while generating %s" % (
                param["Type"], feature["Name"])
        sciArgs.append(" ".join(_(info["xpcomToSci"],
                                  replacements={
                                    "var": param["Name"]})))
        pre += " ".join(_(info.get("xpcomToSciPre", ""),
                                  replacements={
                                    "var": param["Name"]}))
        post += " ".join(_(info.get("xpcomToSciPost", ""),
                                  replacements={
                                    "var": param["Name"]}))
    if feature["ReturnType"] != "void":
        assert feature["ReturnType"] in typeInfo, \
            "No type info for return type %s while generating %s" % (
                feature["ReturnType"], feature["Name"])
        info = typeInfo[feature["ReturnType"]]
        assert "cxxReturnType" in info, \
            "No C++ return type available for %s while generating %s" % (
                feature["ReturnType"], feature["Name"])
        args.append("%s _retval" % (info["cxxReturnType"]))
        if "cxxGetterResultOverride" in info:
            cxxGetterResultOverride = info.get("cxxGetterResultOverride", "")
    name = interCaps(idlName(feature["Name"], cxxVersion=True), 1)
    if not name.startswith(mode):
        name = mode + name
    replacements = {
        "name": name,
        "args": ", ".join(args),
        "pre": pre,
        "post": post,
        "sciArgs": ", ".join(sciArgs),
        "sciApiName": sciApiName,
        "result": mode == "Get" and "*_retval = " or "",
    }

    resultline = "%(result)sSendEditor(%(sciArgs)s);"
    if cxxGetterResultOverride:
        resultline = cxxGetterResultOverride

    _(r"""
        NS_IMETHODIMP SciMoz::%(name)s(%(args)s) {
            #ifdef SCIMOZ_DEBUG_VERBOSE
                printf("SciMoz::%(name)s\n");
            #endif
            SCIMOZ_CHECK_VALID("%(name)s")
            %(pre)s""" + resultline + """%(post)s
            return NS_OK;
        }

        """,
      replacements=replacements,
      file=file)
    if mode == "Get" and feature["MatchingFeature"] is not None:
        generate_cxx_xpcom_attribute_fragment(feature["MatchingFeature"],
                                              file,
                                              mode="Set")

def generate_cxx_xpcom_fragment(face):
    """
    Generate the C++ XPCOM stubs
    @param face: the scintilla interface definition structure
    """
    outputfile = file("npscimoz_gen.h", "w")
    print "Dumping C++ SciMoz implementation to %s" % outputfile.name
    for name in face.order:
        if idlName(name) in manualFunctions + discardedFeatures:
            # skip manually implemented functions
            continue
        feature = face.features[name]
        #if not "isLite" in feature:
        #    # we don't need xpcom implementations for non-lite features
        #    continue
        if feature["FeatureType"] == "fun":
            generate_cxx_xpcom_method_fragment(feature, outputfile)
        elif feature["FeatureType"] == "get":
            generate_cxx_xpcom_attribute_fragment(feature, outputfile)
        elif feature["FeatureType"] == "set":
            pass

def generate_npapi_identifiers(face, file):
    """
    Generate the identifier declarations for NPAPI
    @param face: the scintilla interface definition structure
    @param file: the file to write to
    """
    print "Dumping NPAPI identifier declarations to %s" % file.name

    methods = set(manualFunctions)
    for name in face.order:
        if face.features[name]["FeatureType"] != "fun":
            continue
        methods.add(idlName(name))
    methods -= set(discardedFeatures)
    for method in methods:
        _("static NPIdentifier SM_METHOD_%(name)s;",
            replacements={
              "name": method.upper(),
              "debug": method
            },
            file=file)

    properties = set(manualGetterProperties)
    for name in face.order:
        if face.features[name]["FeatureType"] != "get":
            continue
        properties.add(attributeName(name))
    properties -= set(discardedFeatures)
    for property in properties:
        _("static NPIdentifier SM_PROPERTY_%(name)s;",
          replacements={
            "name": property.upper()
          },
          file=file)

    generate_npapi_init(methods, properties, file)

def generate_npapi_init(methods, properties, file):
    """
    Generate the identifier initialization for NPAPI
    @param methods: the list of method names (as listed in the idl)
    @param properties: the list of property names (as listed in the idl)
    @param file: the file to write to
    """
    print "Dumping NPAPI identifier initialization to %s" % file.name
    _("""
        static bool mNPIdentifiersInitialized = 0;
        void SciMoz::SciMozInitNPIdentifiers() {
            if (mNPIdentifiersInitialized) {
                return;
            }
            mNPIdentifiersInitialized = 1;
        """,
        file=file)
    for method in methods:
        assert method == idlName(method), \
            "unexpected method name %s not formatted as %s" % (method, idlName(method))
        _("""SM_METHOD_%(defineName)s = NPN_GetStringIdentifier("%(name)s");""",
          replacements={
            "defineName": method.upper(),
            "name": method,
          },
          indent=4,
          file=file)
    for property in properties:
        assert property == idlName(property), \
            "unexpected property name %s not formatted as %s" % (property, idlName(property))
        _("""SM_PROPERTY_%(defineName)s = NPN_GetStringIdentifier("%(name)s");""",
          replacements={
            "defineName": property.upper(),
            "name": property,
          },
          indent=4,
          file=file)
    # no need to deal with the other things - in particular, all setters have
    # matching getters with the same property name.
    _("}", file=file)

def generate_npapi_has_method(face, file):
    """
    Generate the NPAPI HasMethod method
    @param face: the scintilla interface definition structure
    @param file: the file to write to
    """
    print "Generating NPAPI HasMethod implementation in %s" % file.name
    _("""
      bool
      SciMoz::HasMethod(NPIdentifier np_name)
      {
          if (false ||
      """,
      file=file)

    methods = set(manualFunctions)
    for name in face.order:
        if idlName(name) in discardedFeatures:
            # skip things we don't need
            continue
        feature = face.features[name]
        if feature["FeatureType"] == "fun":
            methods.add(name)

    for name in methods:
        _("""np_name == SM_METHOD_%(name)s ||""",
          replacements={
            "name": name.upper(),
          },
          indent=8,
          file=file)

    _("""
              false)
              return true;
          return false;
      }
      """,
      file=file)

def generate_npapi_invoke_scintilla_fragment(feature, file):
    """
    Generate default invoke for a feature
    @param feature the scintilla feature (function) to invoke
    @param file the file to write to
    """
    name = feature["Name"]
    _(r"""
      if (name == SM_METHOD_%(defineName)s) {
          /* ## autogenerated method: %(idlName)s ## */
          #ifdef SCIMOZ_DEBUG_VERBOSE
              printf("SciMoz::%(cxxName)s\n");
          #endif
          SCIMOZ_CHECK_THREAD("%(cxxName)s", false)
          SCIMOZ_CHECK_ALIVE("%(cxxName)s", false)
          if (argCount != %(paramCount)s) return false;
      """,
      indent=4,
      replacements={
        "idlName": idlName(name),
        "defineName": name.upper(),
        "cxxName": interCaps(idlName(name), 1),
        "paramCount": feature["ParamCount"]
      },
      file=file)
    # the xpcom/npapi interface skips the unused args in scintilla, so we need
    # to keep track of the arg count manually
    usedArgs = 0
    callArgs = [DEFINEName(name)]
    postCall = []
    for idx, param in enumerate(feature["Params"]):
        if param["Type"] == "void":
            _("/* arg %(idx)s of type void */",
              replacements={
                "idx": idx,
              },
              indent=8,
              file=file)
            callArgs.append(" " * 31 + "0")
            continue
        info = typeInfo[param["Type"]]
        _("""
          /* arg %(idx)s of type %(type)s */
          if (!%(checkVariant)s(%(arg)s)) return false;
          """,
          replacements={
            "idx": idx,
            "type": param["Type"],
            "checkVariant": info["checkNPVariant"],
            "arg": "args[%i]" % (usedArgs)
          },
          indent=8,
          file=file)
        if "fromNPVariantPre" in info:
            _(info["fromNPVariantPre"],
              replacements={
                "i": usedArgs,
                "arg": "args[%i]" % (usedArgs)
              },
              indent=8,
              file=file)
        callArgs.extend(_(info["fromNPVariant"],
                          indent=31,
                          replacements={
                            "i": usedArgs,
                            "cast": "(long)",
                            "arg": "args[%i]" % (usedArgs)
                          }))
        if "fromNPVariantPost" in info:
            postCall.extend(_(info["fromNPVariantPost"],
                              replacements={
                                "i": usedArgs,
                                "arg": "args[%i]" % (usedArgs)
                              },
                              indent=0))
        usedArgs += 1

    _("""
      PRWord rv = SendEditor(%(args)s);
      """,
      replacements={
        "args": ",\n".join(callArgs)
      },
      indent=8,
      file=file)
    if feature["ReturnType"] == "void":
        _("""
          /* eat unused return value */
          rv = rv;
          """,
          indent=8,
          file=file)
    else:
        retType = feature["ReturnType"]
        _("""/* return value of type %(returnType)s */
             %(toNPVariant)s
             """,
          replacements={
            "returnType": retType,
            "toNPVariant": "\n".join(_(typeInfo[retType]["toNPVariant"],
                                       indent=8,
                                       replacements={
                                         "target": "*result",
                                         "i": "_retval"
                                       })).lstrip()
          },
          indent=8,
          file=file)
    _(postCall + [""], indent=8, file=file)

    _("""
          return true;
      }
      """,
      indent=4,
      file=file)

def generate_npapi_invoke_manual_fragment(name, file):
    """
    Generate an NPAPI invoke fragement that calls a manually-implemented method
    (taking the same arguments as the Invoke method itself).
    @param name: the name of the method
    @param file: the file to write to
    """
    log.debug("Writing manual invoke stub for method %s", name)
    _(r"""
      if (name == SM_METHOD_%(defineName)s) {
          /* ## manually implemented method: %(idlName)s ## */
          #ifdef SCIMOZ_DEBUG_VERBOSE
              printf("SciMoz::%(cxxName)s\n");
          #endif
          SCIMOZ_CHECK_THREAD("%(cxxName)s", false)
          SCIMOZ_CHECK_ALIVE("%(cxxName)s", false)
          return %(cxxName)s(args, argCount, result);
      }
      """,
      replacements={
        "idlName": idlName(name),
        "defineName": name.upper(),
        "cxxName": interCaps(name, 1),
      },
      indent=4,
      file=file)

def generate_npapi_invoke_text_and_length_fragment(feature, file):
    """
    Generate an NPAPI invoke fragment for a method that takes a length and a
    string.
    @param feature: the name of the method
    @param file: the file to write to
    """
    name = feature["Name"]
    log.debug("Writing text-and-length invoke stub for method %s", name)
    _(r"""
      if (name == SM_METHOD_%(defineName)s) {
          /* ## text-and-length method: %(idlName)s ## */
          #ifdef SCIMOZ_DEBUG_VERBOSE
              printf("SciMoz::%(cxxName)s\n");
          #endif
          SCIMOZ_CHECK_THREAD("%(cxxName)s", false)
          SCIMOZ_CHECK_ALIVE("%(cxxName)s", false)
          const NPUTF8 *text;
          uint32_t length;
          if (argCount > 2) {
              SCIMOZ_DEBUG_PRINTF("%%s: expecting 1 or two parameters, got %%u\n",
                                  __FUNCTION__, argCount);
              return false;
          }
          if (argCount == 1 || NPVARIANT_IS_NULL(args[1])) {
              /* text only; we can get a null second argument when called from
                 the JS XPCOM wrapper. */
               if (!NPVARIANT_IS_STRING(args[0])) {
                   SCIMOZ_DEBUG_PRINTF("%%s: parameter is not string\n",
                                       __FUNCTION__);
                   return false;
               }
               text = NPVARIANT_TO_STRING(args[0]).UTF8Characters;
               length = NPVARIANT_TO_STRING(args[0]).UTF8Length;
          }
          else {
              /* length + text */
              if (!NPVARIANT_IS_INT32(args[0])) {
                  SCIMOZ_DEBUG_PRINTF("%%s: first parameter is not int\n",
                                      __FUNCTION__);
                  return false;
              }
              if (!NPVARIANT_IS_STRING(args[1])) {
                  SCIMOZ_DEBUG_PRINTF("%%s: second parameter is not string\n",
                                      __FUNCTION__);
                  return false;
              }
              text = NPVARIANT_TO_STRING(args[1]).UTF8Characters;
              length = NPVARIANT_TO_STRING(args[1]).UTF8Length;
          }
          int retval = SendEditor(%(messageName)s,
                                  length,
                                  reinterpret_cast<sptr_t>(text));
          if (%(hasReturn)s) {
              NPN_ReleaseVariantValue(result);
              INT32_TO_NPVARIANT(retval, *result);
          }
          return true;
      }
      """,
      replacements={
        "idlName": idlName(name),
        "defineName": name.upper(),
        "cxxName": interCaps(name, 1),
        "messageName": DEFINEName(name),
        "hasReturn": str(feature["ReturnType"] != "void").lower(),
      },
      indent=4,
      file=file)

def generate_npapi_invoke(face, file):
    """
    Generate the NPAPI Invoke method
    @param face: the scintilla interface definition structure
    @param file: the file to write to
    """
    print "Generating NPAPI Invoke implementation in %s" % file.name
    _("""
      bool
      SciMoz::Invoke(NPP instance,
                     NPIdentifier name,
                     const NPVariant *args,
                     uint32_t argCount,
                     NPVariant *result)
      {
      """,
      file=file)
    for name in face.order:
        feature = face.features[name]
        if feature["FeatureType"] != "fun" or idlName(name) in discardedFeatures:
            log.debug("Skipping invoke method %s (type %s)",
                      name, feature.get("FeatureType"))
            continue
        if idlName(name) in manualFunctions:
            generate_npapi_invoke_manual_fragment(name, file)
        elif idlName(name) in textAndLengthFunctions:
            generate_npapi_invoke_text_and_length_fragment(feature, file)
        else:
            generate_npapi_invoke_scintilla_fragment(feature, file)

    for name in manualFunctions:
        if interCaps(name, 1) in face.order:
            log.debug("Skipping manual method %s, already found", name)
            continue
        generate_npapi_invoke_manual_fragment(name, file)

    _(r"""
          #ifdef SCIMOZ_DEBUG
              printf("SciMoz::Invoke: unknown method %%s\n",
                     NPN_UTF8FromIdentifier(name));
          #endif
          return false;
      }
      """,
      file=file)

def generate_npapi_has_property(face, file):
    """
    Generate the NPAPI HasProperty method
    @param face: the scintilla interface definition structure
    @param file: the file to write to
    """
    print "Generating NPAPI HasProperty implementation in %s" % file.name
    _("""
      bool
      SciMoz::HasProperty(NPIdentifier np_name)
      {
          if (false ||
      """,
      file=file)

    properties = set()

    for name in face.order:
        if idlName(name) in discardedFeatures:
            # skip things we don't need
            continue
        feature = face.features[name]
        if feature["FeatureType"] == "get":
            properties.add(attributeName(name))

    for name in properties:
        _("""np_name == SM_PROPERTY_%(name)s ||""",
          replacements={
            "name": name.upper(),
          },
          indent=8,
          file=file)

    _("""
              false)
              return true;
          return false;
      }
      """,
      file=file)

def generate_npapi_get_property_scintilla_fragment(feature, file):
    """
    Generate the default property getter for a feature
    @param feature the scintilla feature (property) to get
    @param file the file to write to
    """
    _(r"""
      if (np_name == SM_PROPERTY_%(defineName)s) {
          /* ## autogenerated getter: %(attrName)s ## */
          #ifdef SCIMOZ_DEBUG_VERBOSE
              printf("SciMoz::%(cxxName)s\n");
          #endif
          SCIMOZ_CHECK_THREAD("%(cxxName)s", false)
          SCIMOZ_CHECK_ALIVE("%(cxxName)s", false)
      """,
      replacements={
        "attrName": attributeName(feature["Name"]),
        "defineName": attributeName(feature["Name"]).upper(),
        "cxxName": feature["Name"]
      },
      indent=4,
      file=file)

    retType = feature["ReturnType"]
    assert "getter" in typeInfo[retType], \
        "No getter available for type %s while generating getter %s" % (retType, feature["Name"])
    _(typeInfo[retType]["getter"](feature["Name"]),
      indent=8,
      file=file)

    _("""
          return true;
      }
      """,
      indent=4,
      file=file)

def generate_npapi_get_property_manual_fragment(feature, file):
    """
    Generate the property getter for a feature using custom code
    @param feature the scintilla feature (property) to get
    @param file the file to write to
    """
    assert "code" in feature, \
        "Tried to generate manual getter without code"
    _(r"""
      if (np_name == SM_PROPERTY_%(defineName)s) {
          /* ## manually implemented getter: %(attrName)s ## */
          #ifdef SCIMOZ_DEBUG_VERBOSE
              printf("SciMoz::%(cxxName)s\n");
          #endif
          SCIMOZ_CHECK_THREAD("%(cxxName)s", false)
          SCIMOZ_CHECK_ALIVE("%(cxxName)s", false)
      """,
      replacements={
        "attrName": attributeName(feature["Name"]),
        "defineName": attributeName(feature["Name"]).upper(),
        "cxxName": feature["Name"]
      },
      indent=4,
      file=file)
    _(feature["code"],
      replacements={
        "target": "*result",
      },
      indent=8,
      file=file)

    _(r"""
          printf("SciMoz::%(name)s: ran past end of manual getter\n");
          return false;
      }
      """,
      replacements={
        "name": feature["Name"]
      },
      indent=4,
      file=file)

def generate_npapi_get_property(face, file):
    """
    Generate the NPAPI GetProperty method
    @param face: the scintilla interface definition structure
    @param file: the file to write to
    """
    print "Generating NPAPI GetProperty implementation in %s" % file.name
    _("""
      bool
      SciMoz::GetProperty(NPIdentifier np_name, NPVariant *result)
      {
      """,
      file=file)
    for name in face.order:
        if idlName(name) in discardedFeatures:
            # skip things we don't need
            continue
        feature = face.features[name]
        if feature["FeatureType"] != "get":
            continue
        if "code" in feature:
            generate_npapi_get_property_manual_fragment(feature, file)
        else:
            generate_npapi_get_property_scintilla_fragment(feature, file)

    _(r"""
          printf("SciMoz::GetProperty: unknown property %%s\n",
                 NPN_UTF8FromIdentifier(np_name));
          return false;
      }
      """,
      file=file)

def generate_npapi_set_property_scintilla_fragment(feature, file):
    """
    Generate the default property setter for a feature
    @param feature the scintilla feature (property) to set
    @param file the file to write to
    """
    _(r"""
      if (np_name == SM_PROPERTY_%(defineName)s) {
          /* ## autogenerated setter: %(attrName)s ## */
          #ifdef SCIMOZ_DEBUG_VERBOSE
              printf("SciMoz::%(cxxName)s\n");
          #endif
          SCIMOZ_CHECK_THREAD("%(cxxName)s", false)
          SCIMOZ_CHECK_ALIVE("%(cxxName)s", false)
      """,
      replacements={
        "attrName": attributeName(feature["Name"]),
        "defineName": attributeName(feature["Name"]).upper(),
        "cxxName": feature["Name"]
      },
      indent=4,
      file=file)

    attrName = attributeName(feature["Name"])
    callArgs = [DEFINEName(feature["Name"])]
    postCall = []
    usedArgs = 0
    for param in feature["Params"]:
        if param["Type"] == "void":
            callArgs.append("0")
            continue
        info = typeInfo[param["Type"]]
        _("""
          /* arg %(i)s of type %(type)s */
          if (!%(checkNPVariant)s(%(arg)s)) {
              #ifdef SCIMOZ_DEBUG
                  printf("%(name)s setter: arg %(i)s has invalid type %%i",
                         (%(arg)s).type);
              #endif
              return false;
          }
          """,
          replacements={
              "name": attrName,
              "i": usedArgs,
              "type": param["Type"],
              "checkNPVariant": info["checkNPVariant"],
              "arg": "*value"
          },
          indent=8,
          file=file)
        if "fromNPVariantPre" in info:
            _(info["fromNPVariantPre"],
              replacements={
                "arg": "*value",
                "cast": "(long)",
                "i": "%i" % (usedArgs)
              },
              indent=8,
              file=file)
        callArgs.append("".join(_(info["fromNPVariant"],
                                  replacements={
                                    "arg": "*value",
                                    "cast": "(long)",
                                    "i": "%i" % (usedArgs)
                                  })))
        if "fromNPVariantPost" in info:
            postCall.extend(_(info["fromNPVariantPost"],
                              replacements={
                                "i": "%i" % (usedArgs)
                              }))
        usedArgs += 1

    _(r"""
      SendEditor(%(args)s);
      """,
      replacements={
        "args": (",\n" + " " * 19).join(callArgs)
      },
      indent=8,
      file=file)
    _(postCall + [""], indent=8, file=file)

    _("""
          return true;
      }
      """,
      indent=4,
      file=file)

def generate_npapi_set_property_manual_fragment(feature, file):
    """
    Generate the default property setter for a feature
    @param feature the scintilla feature (property) to set
    @param file the file to write to
    """
    _(r"""
      if (np_name == SM_PROPERTY_%(defineName)s) {
          /* ## manually implemented setter: %(attrName)s ## */
          #ifdef SCIMOZ_DEBUG_VERBOSE
              printf("SciMoz::%(cxxName)s\n");
          #endif
          SCIMOZ_CHECK_THREAD("%(cxxName)s", false)
          SCIMOZ_CHECK_ALIVE("%(cxxName)s", false)
      """,
      replacements={
        "attrName": attributeName(feature["Name"]),
        "defineName": attributeName(feature["Name"]).upper(),
        "cxxName": feature["Name"]
      },
      indent=4,
      file=file)

    _(feature["code"],
      replacements={
        "target": "*result",
      },
      indent=8,
      file=file)

    _(r"""
          printf("SciMoz::%(name)s: ran past end of manual setter\n");
          return false;
      }
      """,
      replacements={
        "name": feature["Name"]
      },
      indent=4,
      file=file)

def generate_npapi_set_property(face, file):
    """
    Generate the NPAPI SetProperty method
    @param face: the scintilla interface definition structure
    @param file: the file to write to
    """
    print "Generating NPAPI SetProperty implementation in %s" % file.name
    _("""
      bool
      SciMoz::SetProperty(NPIdentifier np_name, const NPVariant *value)
      {
      """,
      file=file)
    for name in face.order:
        if idlName(name) in discardedFeatures:
            # skip things we don't need
            continue
        feature = face.features[name]
        if feature["FeatureType"] != "set":
            continue
        if "code" in feature:
            generate_npapi_set_property_manual_fragment(feature, file)
        else:
            generate_npapi_set_property_scintilla_fragment(feature, file)

    _(r"""
          printf("SciMoz::SetProperty: unknown property %%s\n",
                 NPN_UTF8FromIdentifier(np_name));
          return false;
      }
      """,
      file=file)

def generate_wrapper(face, interfaceCount):
    outputfile = file("ISciMoz_jswrapper_gen.fragment", "w")
    print "Generating XPCOM wrapper in %s" % outputfile.name
    for i in range(interfaceCount + 1):
        _("""
          koSciMozWrapper.prototype._interfaces.push(Components.interfaces.ISciMoz_Part%(i)s);
          """,
          replacements={
            "i": i,
          },
          file=outputfile)

    methods = set(manualFunctions)
    getters = set(map(attributeName, manualGetterProperties.keys()))
    setters = set(map(attributeName, manualSetterProperties.keys()))

    for name in face.order:
        if idlName(name) in discardedFeatures:
            # skip things we don't need
            continue
        feature = face.features[name]
        if feature["FeatureType"] == "get":
            getters.add(attributeName(name))
        elif feature["FeatureType"] == "set":
            setters.add(attributeName(name))
        elif feature["FeatureType"] == "fun":
            methods.add(idlName(name))

    add_logging = False  # set to True to dump all scimoz calls
    for name in getters:
        _("""
          koSciMozWrapper.prototype.__defineGetter__("%(name)s",
                                                     function get_%(name)s() {
                                                        %(logme)s return this.__scimoz.%(name)s;
                                                     });
          """,
          replacements={
            "name": name,
            "logme": 'dump("          scimoz: %s (getter)\\n");' % (name) if add_logging else "",
          },
          file=outputfile)

    for name in setters:
        _("""
          koSciMozWrapper.prototype.__defineSetter__("%(name)s",
                                                     function set_%(name)s(v) {
                                                        %(logme)s this.__scimoz.%(name)s=v;
                                                     });
          """,
          replacements={
            "name": name,
            "logme": 'dump("          scimoz: %s (SETTER)\\n");' % (name) if add_logging else "",
          },
          file=outputfile)

    for name in methods:
        _("""
          koSciMozWrapper.prototype.%(name)s =
              function meth_%(name)s() {
                %(logme)s return this.__scimoz.%(name)s.apply(this.__scimoz, arguments);
              }
          """,
          replacements={
            "name": idlName(name),
            "logme": 'dump("          scimoz: %s()\\n");' % (name) if add_logging else "",
          },
          file=outputfile)


#
# Type mappings
# This is a hash where the keys are the iface types; the value is another hash:
# "idlDirection": the direction marker on the generated idl (in, out, inout)
# "idlType": the name of the type as experssed in xpidl
# "checkNPVariant": NPRuntime macro to assert a NPVariant is of this type
# "fromNPVariant": C++ expression to convert a NPVariant ("{np}") to the Scintilla C++ type
#                  "$" will be replaced with the argument number
# "toNPVariant": C++ expression to convert a Scintilla C++ type ("{sci}") to a NPVariant ("@")
typeInfo = {
    "string": {
        "idlDirection": "in",
        "idlType": "AUTF8String",
        "cxxParamType": "const nsACString&",
        "checkNPVariant": "NPVARIANT_IS_STRING",
        "fromNPVariant": "%(cast)s(NPVARIANT_TO_STRING(%(arg)s).UTF8Characters)",
        "xpcomToSci": "reinterpret_cast<long>(PromiseFlatCString(%(var)s).get())",
    },
    "stringresult": {
        "idlDirection": "out",
        "idlType": "AString",
        "cxxParamType": "nsAString&",
        "checkNPVariant": "NPVARIANT_IS_OBJECT",
        "fromNPVariantPre": r"""static char _buffer_%(i)s[32 * 1024];
                                _buffer_%(i)s[32 * 1024-1] = '\0';
                                short _buflen_%(i)s = static_cast<short>(sizeof(_buffer_%(i)s)-1);
                                memcpy(_buffer_%(i)s, &_buflen_%(i)s, sizeof(_buflen_%(i)s));
                                """,
        "fromNPVariant": "%(cast)s(_buffer_%(i)s)",
        "fromNPVariantPost": """NPVariant _variant_%(i)s;
                                NPUTF8* _npbuf_%(i)s = reinterpret_cast<NPUTF8*>(NPN_MemAlloc(rv));
                                memcpy(_npbuf_%(i)s, _buffer_%(i)s, rv);
                                STRINGN_TO_NPVARIANT(_npbuf_%(i)s, rv, _variant_%(i)s);
                                NPN_SetProperty(instance,
                                                NPVARIANT_TO_OBJECT(%(arg)s),
                                                NPN_GetStringIdentifier("value"),
                                                &_variant_%(i)s);
                                """,
        "xpcomToSciPre": r"""   static char _buffer[32 * 1024];
                                _buffer[32 * 1024-1] = '\0';
                                """,
        "xpcomToSci": "reinterpret_cast<long>(_buffer)",
        "xpcomToSciPost": "%(var)s.Assign(NS_ConvertUTF8toUTF16(_buffer));", # TODO: Need a length here?
    },
    "int": {
        "idlDirection": "in",
        "idlType": "long",
        "cxxParamType": "PRInt32",
        "cxxReturnType": "PRInt32*",
        "checkNPVariant": "NPVARIANT_IS_INT32",
        "fromNPVariant": "NPVARIANT_TO_INT32(%(arg)s)",
        "xpcomToSci": "%(var)s",
        "toNPVariant": r"""
            INT32_TO_NPVARIANT(rv, %(target)s);
            #ifdef SCIMOZ_DEBUG_VERBOSE
                printf("SciMoz::%%s result = %%i\n", __FUNCTION__, static_cast<PRInt32>(rv));
            #endif
            """,
        "getter": lambda n: "INT32_TO_NPVARIANT(SendEditor(%s, 0, 0), *result);" % (DEFINEName(n)),
    },
    "ptr": {
        # npruntime has no useful way of encoding a 64 bit value safely
        # encode it as a string instead. since it's easy, split each byte into
        # nibbles and print as an offset from 'A' (i.e. 0 = 'A', 15 = 'P')
        "idlDirection": "in",
        "idlType": "ACString",
        "cxxParamType": "const nsACString&",
        "cxxReturnType": "nsACString&",
        "checkNPVariant": "NPVARIANT_IS_STRING",
        "fromNPVariantPre": """
            PRWord _arg_%(i)s;
            if (NPVARIANT_TO_STRING(%(arg)s).UTF8Length == 0) {
                _arg_%(i)s = 0;
            }
            else if (NPVARIANT_TO_STRING(%(arg)s).UTF8Length == sizeof(PRWord) * 2) {
                const NPUTF8* _buf_%(i)s = NPVARIANT_TO_STRING(%(arg)s).UTF8Characters;
                for (PRSize i = 0; i < sizeof(PRWord); ++i) {
                    reinterpret_cast<unsigned char*>(&_arg_%(i)s)[i] =
                        (((_buf_%(i)s[i * 2] - 'A') & 0x0F) << 4) |
                        ((_buf_%(i)s[i * 2 + 1] - 'A') & 0x0F);
                }
            }
            else {
                #ifdef SCIMOZ_DEBUG
                    printf("SciMoz::%%s pointer value %%s has invalid length %%i",
                           __FUNCTION__,
                           NPVARIANT_TO_STRING(%(arg)s).UTF8Characters,
                           NPVARIANT_TO_STRING(%(arg)s).UTF8Length);
                #endif
                return false;
            }
            """,
        "fromNPVariant": "_arg_%(i)s",
        "toNPVariant": """
            NPUTF8* _buf_%(i)s = reinterpret_cast<NPUTF8*>(NPN_MemAlloc(sizeof(PRWord) * 2));
            if (!_buf_%(i)s) return false;
            for (PRSize i = 0; i < sizeof(PRWord); ++i) {
                _buf_%(i)s[i * 2] = ((reinterpret_cast<unsigned char*>(&rv)[i] & 0xF0) >> 4) + 'A';
                _buf_%(i)s[i * 2 + 1] = (reinterpret_cast<unsigned char*>(&rv)[i] & 0x0F) + 'A';
            }
            STRINGN_TO_NPVARIANT(_buf_%(i)s, sizeof(PRWord) * 2, %(target)s);
            """,
        "getter": lambda n: """
            PRWord _ptr_$ = SendEditor(%s, 0, 0);
            NPUTF8* _buf_$ = reinterpret_cast<NPUTF8*>(NPN_MemAlloc(sizeof(PRWord) * 2));
            if (!_buf_$) return false;
            for (PRSize i = 0; i < sizeof(PRWord); ++i) {
                _buf_$[i * 2] = ((reinterpret_cast<unsigned char*>(&_ptr_$)[i] & 0xF0) >> 4) + 'A';
                _buf_$[i * 2 + 1] = (reinterpret_cast<unsigned char*>(&_ptr_$)[i] & 0x0F) + 'A';
            }
            STRINGN_TO_NPVARIANT(_buf_$, sizeof(PRWord) * 2, *result);
            """ % (DEFINEName(n)),
        "xpcomToSciPre": r"""
            PRWord ptr;
            const char *_buf = PromiseFlatCString(%(var)s).get();
            for (PRSize i = 0; i < sizeof(PRWord); ++i) {
                reinterpret_cast<unsigned char*>(&ptr)[i] =
                    (((_buf[i * 2] - 'A') & 0x0F) << 4) |
                    ((_buf[i * 2 + 1] - 'A') & 0x0F);
            }
            """,
        "xpcomToSci": "ptr",
        "cxxGetterResultOverride": """
            PRWord _ptr = SendEditor(%(sciApiName)s, 0, 0);
            static char _buf[(sizeof(PRWord) * 2) + 1];
            _buf[(sizeof(PRWord) * 2)] = '\\0';
            for (PRSize i = 0; i < sizeof(PRWord); ++i) {
                _buf[i * 2] = ((reinterpret_cast<unsigned char*>(&_ptr)[i] & 0xF0) >> 4) + 'A';
                _buf[i * 2 + 1] = (reinterpret_cast<unsigned char*>(&_ptr)[i] & 0x0F) + 'A';
            }
            nsAutoCString tmpString(_buf);
            _retval = tmpString;
            """,
    },
    "bool": {
        "idlDirection": "in",
        "idlType": "boolean",
        "cxxParamType": "bool",
        "cxxReturnType": "bool*",
        "checkNPVariant": "NPVARIANT_IS_BOOLEAN",
        "fromNPVariant": "NPVARIANT_TO_BOOLEAN(%(arg)s)",
        "toNPVariant": "BOOLEAN_TO_NPVARIANT(rv, %(target)s);",
        "xpcomToSci": "%(var)s",
        "getter": lambda n: "BOOLEAN_TO_NPVARIANT(SendEditor(%s, 0, 0), *result);" % (DEFINEName(n)),
    },
    "position": {
        "idlDirection": "in",
        "idlType": "long",
        "cxxParamType": "PRInt32",
        "cxxReturnType": "PRInt32*",
        "checkNPVariant": "NPVARIANT_IS_INT32",
        "fromNPVariant": "NPVARIANT_TO_INT32(%(arg)s)",
        "toNPVariant": "INT32_TO_NPVARIANT(rv, %(target)s);",
        "xpcomToSci": "%(var)s",
        "getter": lambda n: "INT32_TO_NPVARIANT(SendEditor(%s, 0, 0), *result);" % (DEFINEName(n)),
    },
    "colour": {
        "idlDirection": "in",
        "idlType": "long",
        "cxxParamType": "PRInt32",
        "cxxReturnType": "PRInt32*",
        "checkNPVariant": "NPVARIANT_IS_INT32",
        "fromNPVariant": "NPVARIANT_TO_INT32(%(arg)s)",
        "toNPVariant": "INT32_TO_NPVARIANT(rv, %(target)s);",
        "xpcomToSci": "%(var)s",
        "getter": lambda n: "INT32_TO_NPVARIANT(SendEditor(%s, 0, 0), *result);" % (DEFINEName(n)),
    },
    "keymod": {
        "idlDirection": "in",
        "idlType": "long",
        "cxxParamType": "PRInt32",
        "checkNPVariant": "NPVARIANT_IS_INT32",
        "fromNPVariant": "NPVARIANT_TO_INT32(%(arg)s)",
        "toNPVariant": "INT32_TO_NPVARIANT(rv, %(target)s);"
    },
    "void": {
        "idlDirection": "unused",
        "idlType": "void",
        "checkNPVariant": "NPVARIANT_IS_VOID",
        "toNPVariant": "VOID_TO_NPVARIANT(%(target)s);"
    },
    "cells": {
        "idlDirection": "in",
        "idlType": "string",
        "cxxParamType": "const char *",
        "checkNPVariant": "NPVARIANT_IS_STRING",
        "fromNPVariant": "%(cast)s(NPVARIANT_TO_STRING(%(arg)s).UTF8Characters)",
        "xpcomToSci": "reinterpret_cast<long>(PromiseFlatCString(%(var)s).get())",
    },
    "textrange": {
        "idlDirection": "inout",
        "idlType": "string",
        "checkNPVariant": "NPVARIANT_IS_STRING",
        "fromNPVariant": "%(cast)s(NPVARIANT_TO_STRING(%(arg)s).UTF8Characters)",
    },
}

def main():
    logging.basicConfig()
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-v", "--verbose", dest="verbose", action="count",
                      help="Increase verbosity for debugging", default=0)
    (options, args) = parser.parse_args()
    log.setLevel(logging.INFO - options.verbose * 10)

    # Generate the interface information and dump them to separate files
    face = Face.Face()
    face.ReadFromFile(os.path.join(scintillaIncPath, "Scintilla.iface"))
    fixup_iface_data(face)
    generate_idl_constants_fragment(face)
    generate_idl_lite_fragment(face)
    generate_idl_full_fragment(face)
    generate_cxx_xpcom_fragment(face)
    outputfile = file("generated_plugin_code.h", "w")
    generate_npapi_identifiers(face, outputfile)
    generate_npapi_has_method(face, outputfile)
    generate_npapi_invoke(face, outputfile)
    generate_npapi_has_property(face, outputfile)
    generate_npapi_get_property(face, outputfile)
    generate_npapi_set_property(face, outputfile)

if __name__ == '__main__':
    main()

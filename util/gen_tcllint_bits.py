# process tcl errors

errors = """argAfterArgs	argument specified after &quot;args&quot;
argsNotDefault	&quot;args&quot; cannot be defaulted
badBoolean	invalid Boolean value
badByteNum	invalid number, should be between 0 and 255
badColorFormat	invalid color name
badCursor	invalid cursor spec
badFloat	invalid floating-point value
badIndex	invalid index: should be integer or &quot;end&quot;
badIndexExpr	invalid index: should be integer or &quot;end&quot; or &quot;end-integer&quot;
badInt		invalid integer
badKey		invalid keyword
badList		invalid list
badLevel	invalid level
badMode		access mode must include either RDONLY, WRONLY, or RDWR
badOption	invalid option
badPixel	invalid pixel value
badResource	invalid resource name
badSwitch	invalid switch 
badVersion	invalid version number
badWholeNum	invalid value: must be a positive integer
badNatNum	invalid value: must be an integer > 0
badArrayIndex   invalid array index 
mismatchOptions the specified options cannot be used in tandem
noExpr		missing an expression
noScript	missing a script after 
noSwitchArg	missing argument for  switch
nonDefAfterDef	non-default arg specified after default
numArgs		wrong # args
numListElts	wrong # of list elements
obsoleteCmd	Obsolete usage, use  instead
parse 		parse error
procNumArgs	wrong # args for user-defined proc 
tooManyFieldArg	too many fields in argument specifier
winAlpha	window name cannot begin with a capital letter
winBeginDot	window name must begin with &quot;.&quot;
winNotNull	window name cannot be an empty string
invalidUsage    invalid usage, use  instead&quot;
internalError   internal error
arrayReadAsScalar Array variable  read as if a scalar
badMathOp       invalid expr operator 
coreTcl::badTraceOp     invalid operation: should be one or more of rwu
coreTcl::serverAndPort  Option -myport is not valid for servers
coreTcl::socketArgOpt   no argument given for option
coreTcl::socketAsync    cannot set -async option for server sockets
coreTcl::socketBadOpt   invalid option, must be -async, -myaddr, -myport, or -server
coreTcl::socketServer   cannot set -async option for server sockets
coreTcl::badCharMap     string map list should have an even number of elements
coreTcl::errBadBrktExp  the bracket expression is missing a close bracket
coreTcl::badRegexp      Bad regexp pattern
coreTcl::badBinaryFmt   Bad format for binary command
coreTcl::badFormatFmt   Bad format for format command
coreTcl::badSerialMode  Bad serial mode
coreTcl::pkgBadExactRq  Package require has -exact, but no version specified
coreTk::badColormap	invalid colormap: must be &quot;new&quot; or a window name
coreTk::badEvent		invalid event type or keysym
coreTk::badGeometry	invalid geometry specifier
coreTk::badGridRel		must specify window before shortcut
coreTk::badGridMaster	cannot determine master window
coreTk::badPalette		invalid palette spec
coreTk::badPriority	invalid priority keyword or value
coreTk::badScreen		invalid screen value
coreTk::badSticky		invalid stickyness value: should be zero or more of nswe
coreTk::badTab		invalid tab list
coreTk::badTabJust		invalid tab justification: must be left right center or numeric
coreTk::badVirtual		virtual event is badly formed
coreTk::badVisual		invalid visual
coreTk::badVisualDepth	invalid visual depth
coreTk::noVirtual		virtual event not allowed in definition of another virtual event
coreTk::noEvent		no events specified in binding
coreTk::badBindSubst	bind script contains unknown %-placeholders
blt::badIntRange   invalid integer range
blt::badSignal     invalid mnemonic signal
blt::badSignalInt  invalid signal integer, should be between 1 and 32
incrTcl::classNumArgs      wrong # args for class constructor:
incrTcl::procOutScope      proc only defined in class
incrTcl::procProtected     calling protected proc
incrTcl::badMemberName     missing class specifier for body declaration
incrTcl::classOnly         command only defined in class body
incrTcl::warnUnsupported   command deprecated and is no longer valid
incrTcl::nsOnly            command only defined in namespace body
incrTcl::nsOrClassOnly     command only defined in class or namespace body
tclX::badProfileOpt  option not valid when turning off profiling
tclX::optionRequired unexpected option
tclX::badLIndex      invalid index: should be integer, &quot;len&quot; or &quot;end&quot;
tclX::badTlibFile    the filename must have a &quot;.tlib&quot; suffix
oratcl::badConnectStr invalid Oracle connect string
oratcl::badSubstChar  invalid Oracle substitution character
oratcl::badOnOff      invalid &quot;on&quot; or &quot;off&quot; value
oratcl::missingColon  varName must be preceded by ':'
sybtcl::badSubstChar invalid Sybase substitution character
xmlAct::badXMLaction invalid action, must be start children, end, or all"""

warnings = """ nonPortChannel	use of non-portable file descriptor, use  instead
nonPortCmd	use of non-portable command
nonPortColor	non-portable color name
nonPortCursor	non-portable cursor usage
nonPortFile	use of non-portable file name, use &quot;file join&quot;
nonPortOption	use of non-portable option
nonPortVar	use of non-portable variable
warnDeprecated	deprecated usage, use  instead
warnExportPat	export patterns should not be qualified
warnExpr	use curly braces to avoid double substitution
warnExtraClose	unmatched closing character
warnIfKeyword	deprecated usage, use else or elseif
warnNamespacePat glob chars in wrong portion of pattern
warnPattern	possible unexpected substitution in pattern
warnReserved	keyword is reserved
warnRedefine	variable redefined
warnUndefProc	undefined procedure
warnUnsupported	unsupported command, option or variable: use 
warnVarRef	variable reference used where variable name expected
warnInternalCmd usage of internal command, may change without notice
warnBehaviourCmd behaviour of command has changed, 
warnBehaviour   behaviour has changed, 
warnReadonlyVar Variable is considered read-only
warnUndefFunc   unknown math function
nonPublicVar	use of private variable
undefinedVar    use of undefined variable 
globalVarColl   namespace variable  may collide with global variable of same name
shadowVar       Shadowing a previous definition
upvarNsNonsense Non-global upvar into a namespace is undefined
globalNsNonsense global into a namespace is undefined
undefinedUpvar  upvar'd variable  missing in caller scope
coreTcl::warnEscapeChar is a valid escape sequence in later versions of Tcl
coreTcl::warnNotSpecial has no meaning.
coreTcl::warnQuoteChar  &quot; in bracket expressions are treated as quotes
coreTcl::warnY2K        &quot;%y&quot; generates a year without a century. consider using &quot;%Y&quot; to avoid Y2K errors.
coreTcl::warnAIPattern  auto_import pattern is used to restrict loading in later versions of Tcl.
coreTcl::warnMemoryCmd  memory is debugging command
coreTcl::pkgVConflict   Conflict between requested and actually checked version.
coreTcl::pkgTclConflict  Tcl version confict
coreTcl::pkgUnchecked   Will not check commands provided by this package
coreTk::nonPortBitmap	use of non-portable bitmap
coreTk::nonPortKeysym	use of non-portable keysym
coreTk::warnConsoleCmd	usage of internal console command, may change without notice
coreTk::warnTkCmd		usage of internal tk command, may change without notice
expect::warnAmbiguous   ambiguous switch"""


errxulfile = open('tcl_errors.xul', 'w')
warnxulfile = open('tcl_warn.xul', 'w')
preffile = open('pref.xml', 'w')

errorsDict = {}
warningsDict = {}
for line in errors.splitlines():
    symbol, description = line.split(None, 1)
    description = description.capitalize()
    pref = 'tcllint_' + symbol.replace('::', '_')
    errorsDict[symbol] = """            <listitem label="%(description)s (%(symbol)s)"
                      type="checkbox"
                      pref="true"
                      tooltiptext="%(description)s (%(symbol)s)"
                      prefstring="%(pref)s"
                      />
""" % vars()
    print >>preffile, """  <boolean id="%(pref)s">0</boolean>""" % vars()
for line in warnings.splitlines():
    symbol, description = line.split(None, 1)
    description = description.capitalize()
    pref = 'tcllint_' + symbol.replace('::', '_')
    warningsDict[symbol] = """            <listitem label="%(description)s (%(symbol)s)"
                      type="checkbox"
                      tooltiptext="%(description)s (%(symbol)s)"
                      pref="true"
                      prefstring="%(pref)s"
                      />
""" % vars()
    print >>preffile, """  <boolean id="%(pref)s">0</boolean>""" % vars()

def sortfunc(a,b):
    if ':' not in a:
        a_prefix = None
        a_suffix = a
    else:
        a_prefix, a_suffix = a.split('::', 1)
    if ':' not in b:
        b_prefix = None
        b_suffix = b
    else:
        b_prefix, b_suffix = b.split('::', 1)
    return cmp((a_prefix, a_suffix),(b_prefix, b_suffix))

keys = errorsDict.keys()
keys.sort(sortfunc)
for key in keys:
    print >>errxulfile, errorsDict[key],
keys = warningsDict.keys()
keys.sort(sortfunc)
for key in keys:
    print >>warnxulfile, warningsDict[key],





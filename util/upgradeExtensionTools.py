"""
# upgradeTools.py -- We need to do this manually for the tools we
# ship because they're installed in the Komodo installation dir,
# not the user's profile.
"""

__version_info__ = (0, 0, 1)
__version__ = '.'.join(map(str, __version_info__))

import os, sys, re, json
from os.path import basename, join, walk
import getopt
import optparse

import logging

log = logging.getLogger("upgradeExtensionTools")
log.setLevel(logging.INFO)

KODIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, join(KODIR, 'src', 'toolbox'))
sys.path.insert(0, join(KODIR, 'src', 'python-sitelib'))
import koToolbox2
itemVersionString = koToolbox2.ToolboxLoader.ITEM_VERSION
itemVersionArray = [int(x) for x in itemVersionString.split('.')]

sys.stderr.write("itemVersionArray: %s\n" % (itemVersionArray,))

class ToolUpdater(object):
    """
    This class has methods that point to a subtree, find all the directories
    in that subtree named 'tools', and then walk into each of those looking
    for komodo tool files that need updating.
    """
    def __init__(self, opts, args):
        self.opts = opts
        self.args = args

    def upgrade(self, dir):
        os.path.walk(dir, self.findTools, False)

    def findTools(self, notifyNow, dirname, fnames):
        log.debug("findTools: dirname: %s, fnames:%s", dirname, fnames)
        for fname in fnames:
            if fname == "tools":
                os.path.walk(join(dirname, fname), self.walkFunc, False)
                # Don't walk any further here. Slice assignments act as filters.
                fnames[:] = []
                    
    def walkFunc(self, notifyNow, dirname, fnames):
        log.debug("walkFunc: dirname: %s, fnames:%s", dirname, fnames)
        if basename(dirname) == ".svn":
            fnames[:] = []
            return
        for fname in fnames:
            if '.komodotool' in fname or fname == ".folderdata":
                child_path = join(dirname, fname)
                try:
                    fp = open(child_path, 'r')
                    data = json.load(fp, encoding="utf-8")
                except:
                    # Files that get preprocessed, like
                    # src/samples/tools/Find_in_Files.komodotool
                    # aren't valid JSON, and might need to be updated manually.
                    log.exception("Problem processing file %s", fname)
                    continue
                try:
                    if 'version' in data:
                        version = [int(x) for x in data['version'].split('.')]
                        while len(version) < 3:
                            version.append(0)
                        if version == itemVersionArray:
                            log.debug("file %s up-to-date", fname)
                            continue
                    if 'id' in data:
                        # ID's are assigned by sqlite3, and do not persist
                        # outside the database.
                        del data['id']
                    if data['type'] == "snippet":
                        # "false" because these are used as element attribute
                        # values (and database values), and not Python values.
                        if "auto_abbreviation" not in data:
                            data["auto_abbreviation"] = "false"
                        if "treat_as_ejs" not in data:
                            data["treat_as_ejs"] = "false"
                    data['version'] = itemVersionString
                except:
                    log.error("Problem updating json for file %s", fname)
                    continue
                if self.opts.dry_run:
                    log.info("Skip updating %s", child_path)
                try:
                    s = json.dumps(data, encoding="utf-8", indent=2)
                    # Make sure the file ends with a newline
                    fp = open(child_path, 'w')
                    fp.write(s)
                    if not s.endswith("\n"):
                        fp.write("\n")
                    fp.close()
                    log.debug("Updated %s", fname)
                except:
                    log.exception("Problem updating file %s", fname)

# Boilerplate logging etc. pulled from kointegrate.py

class _NoReflowFormatter(optparse.IndentedHelpFormatter):
    """An optparse formatter that does NOT reflow the description."""
    def format_description(self, description):
        return description or ""

def main(argv=sys.argv):
    version = "%prog "+__version__
    desc = __doc__
    desc += "\n\n Use `upgradeExtensionTools.py --help' for options.\n"

    parser = optparse.OptionParser(usage="",
        version=version, description=desc,
        formatter=_NoReflowFormatter())
    parser.add_option("-q", "--quiet", dest="log_level",
                      action="store_const", const=logging.WARN,
                      help="no verbose output")
    parser.add_option("-v", "--verbose", dest="log_level",
                      action="store_const", const=logging.DEBUG,
                      help="more verbose output")
    parser.add_option("-n", "--dry-run", action="store_true",
                      dest="dry_run", help="dry run")
    parser.set_defaults(log_level=logging.INFO, dry_run=False)
    opts, args = parser.parse_args()
    log.setLevel(opts.log_level)
    c = ToolUpdater(opts, args)
    c.upgrade(join(KODIR, 'src', 'modules'))
    c.upgrade(join(KODIR, 'src', 'samples'))

# Recipe: pretty_logging (0.1) in C:\trentm\tm\recipes\cookbook
class _PerLevelFormatter(logging.Formatter):
    """Allow multiple format string -- depending on the log level.

    A "fmtFromLevel" optional arg is added to the constructor. It can be
    a dictionary mapping a log record level to a format string. The
    usual "fmt" argument acts as the default.
    """
    def __init__(self, fmt=None, datefmt=None, fmtFromLevel=None):
        logging.Formatter.__init__(self, fmt, datefmt)
        if fmtFromLevel is None:
            self.fmtFromLevel = {}
        else:
            self.fmtFromLevel = fmtFromLevel
    def format(self, record):
        record.lowerlevelname = record.levelname.lower()
        if record.levelno in self.fmtFromLevel:
            #XXX This is a non-threadsafe HACK. Really the base Formatter
            #    class should provide a hook accessor for the _fmt
            #    attribute. *Could* add a lock guard here (overkill?).
            _saved_fmt = self._fmt
            self._fmt = self.fmtFromLevel[record.levelno]
            try:
                return logging.Formatter.format(self, record)
            finally:
                self._fmt = _saved_fmt
        else:
            return logging.Formatter.format(self, record)

def _setup_logging(stream=None):
    """Do logging setup:

    We want a prettier default format:
        $name: level: ...
    Spacing. Lower case. Drop the prefix for INFO-level. 
    """
    hdlr = logging.StreamHandler(stream)
    defaultFmt = "%(name)s: %(levelname)s: %(message)s"
    infoFmt = "%(message)s"
    fmtr = _PerLevelFormatter(fmt=defaultFmt,
                              fmtFromLevel={logging.INFO: infoFmt})
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)
    log.setLevel(logging.INFO)

if __name__ == "__main__":
    _setup_logging()
    try:
        retval = main(sys.argv)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        sys.exit(1)
    except:
        exc_info = sys.exc_info()
        import traceback
        print
        traceback.print_exception(*exc_info)
        sys.exit(1)
    else:
        sys.exit(retval)

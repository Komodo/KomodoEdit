#!/usr/bin/env python

"""
Adds/removes files in wxs ini files.

Script uses the following file markers (which is generated from buildbots):

  Extra files:
      feature-core/INSTALLDIR/lib/mozilla/chrome/en-US/locale/en-US/formautofill/requestAutocomplete.dtd
      ...

  Missing files:
      feature-core/INSTALLDIR/lib/mozilla/application.ini
      ...
"""

import os
import sys
from os.path import exists, dirname, abspath, normpath, join
from glob import glob
import bisect
import logging

log = logging.getLogger("")
log.setLevel(logging.INFO)

HI_LOW_FROM_FILETYPE = {
    "feature-core": {
        "low": "[default]",
        "high": "[withWatchdogFSNotifications]",
    },
    "feature-docs": {
        "low": "[withDocs]",
        "high": None,  # There is no marker
    },
}

class Error(Exception):
    pass

class Merger(object):
    def __init__(self, wxs_dir):
        self.wxs_dir = wxs_dir
        self.contents_for_wxs_file = {}

    def get_content_lines(self, line):
        parts = line.split("/")
        assert len(parts) > 1
        filename = join(self.wxs_dir, parts[0] + ".ini")
        content_lines = self.contents_for_wxs_file.get(filename)
        if content_lines is None:
            assert exists(filename), "file %r does not exist" % (filename, )
            log.info("reading contents for %r", filename)
            content_lines = file(filename).read().splitlines(0)
            self.contents_for_wxs_file[filename] = content_lines
        return content_lines

    def save(self):
        for filename, content_lines in self.contents_for_wxs_file.items():
            contents = "\n".join(content_lines) + "\n"
            file(filename, "w").write(contents)

    @staticmethod
    def get_low_high_for_content_lines(content_lines, line):
        parts = line.split("/")
        markers = HI_LOW_FROM_FILETYPE[parts[0]]
        low, high = (0, len(content_lines)-1)
        if markers["low"]:
            low = content_lines.index(markers["low"]) + 1
        if markers["high"]:
            high = content_lines.index(markers["high"])
        while content_lines[low] == "":
            low += 1
        while content_lines[high] == "":
            high -= 1
        return low, high

    def handle_unknown(self, line):
        log.warn("Ignoring unknown line: %r", line)

    def handle_add(self, line):
        log.info("  adding file '%s'", line)
        content_lines = self.get_content_lines(line)
        assert line not in content_lines
        low, high = self.get_low_high_for_content_lines(content_lines, line)
        bisect.insort(content_lines, line, lo=low, hi=high)

    def handle_remove(self, line):
        log.info("  removing file '%s'", line)
        content_lines = self.get_content_lines(line)
        low, high = self.get_low_high_for_content_lines(content_lines, line)
        # Try a bisect first, then fall back to iteration.
        idx = bisect.bisect_left(content_lines, line)
        if content_lines[idx] == line:
            content_lines.pop(idx)
            return
        # Iterate to remove the line.
        try:
            content_lines.remove(line)
        except IndexError:
            raise Error("Could not find line to remove: '%s'", line)

    def addremove(self, path):
        fn = self.handle_unknown
        for line in file(path):
            line = line.strip()
            if not line:
                continue
            if line == "Extra files:":
                fn = self.handle_add
                log.info("starting 'added files'")
                continue
            if line == "Missing files:":
                fn = self.handle_remove
                log.info("starting 'missing files'")
                continue
            log.debug("processing line: %r", line)
            fn(line)

def main():
    logging.basicConfig()
    wxs_dir = dirname(dirname(abspath(__file__)))
    merger = Merger(wxs_dir)
    for path in sys.argv[1:]:
        merger.addremove(path)
    merger.save()

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print "Usage: addremove.py file.txt"
        sys.exit(1)
    main()


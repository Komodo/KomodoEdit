#!python
# Copyright (c) 2004-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Get and manage Code Intelligence data about source code of many languages.

The Code Intelligence system is one for generating and managing code
structure information on given source code. See the spec for more details:
    http://specs.tl.activestate.com/kd/kd-0100.html

General Usage
-------------

    from codeintel2.manager import Manager
    mgr = Manager()
    # Alternatively use Database upgrade methods directly for finer control.
    mgr.upgrade()
    mgr.initialize()
    try:
        # Get a Buffer object from a scimoz/path/content.
        buf = mgr.buf_from_*(...)
        
        # Use the buffer's API to do codeintel-y stuff. For example:
        # - See if you are at a trigger point.
        trg = buf.trg_from_pos(...)

        # - Get completions at that trigger. See also
        #   Buffer.async_eval_at_trg(), Buffer.calltips_from_trg().
        cplns = buf.cplns_from_trg(trg, ...)

        # ...
    finally:
        mgr.finalize() # make sure this gets run on your could get hangs
"""



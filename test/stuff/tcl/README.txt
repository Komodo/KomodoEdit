This dir holds files for manually testing Komodo's Tcl debugging.


How To Use
----------

Define the environment variable TCLDEVKIT_LOCAL to refer to the
directory containing the file "ats_run.pdx".

Run Komodo, so that it and the processes it creates see the
TCLDEVKIT_LOCAL variable and its contents.

When running the debugger with logging enabled we should see at the
very beginning that the file ats_run.pdx is loaded from its specified
directory, and we should see 'ats_run' as wrapper and spawn command.

Komodo should accept spawnpoints on the lines with ats_run, (Debugger
running), and execution should spawn proper sub-processes which are
again under debugger control.

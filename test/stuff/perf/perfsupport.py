import os, sys, time
import which
from memutils import getpidsforprocess

def startKomodo(args=[]):
    # start up Komodo with the testFile
    # - spawn komodo and wait to startup
    verbose = 1
    komodoExe = which.which("komodo")
    out = sys.stdout
    pidsBefore = getpidsforprocess('mozilla')

    argv = [os.path.basename(komodoExe), '-v', '']
    os.spawnv(os.P_NOWAIT, komodoExe, argv)
    if verbose:
        out.write("Wait for '%s %s' to start up.\n" % (komodoExe,
                                                       ' '.join(args)))
    time.sleep(20)
    # - determine process PID and prefix for Win32 PDH logging
    pidsAfter = getpidsforprocess('mozilla')
    newPids = [pid for pid in pidsAfter if pid not in pidsBefore]
    if len(newPids) == 0:
        raise "No new Mozilla PIDs were found. The same Komodo was probably already running."
    elif len(newPids) > 1:
        raise "More that one Mozilla process was started by spawning Komodo!"
    else:
        pid = newPids[0]
    return pid

#!/usr/bin/env python

"""
codesign.py
Script to drive Mac OSX code signing
"""

import os
import subprocess
import sys
import tempfile

def run(argv, stdout=False, check=True):
    """
    subprocess wrapper to simplify commands
    @param argv {list} The command to execute
    @param stdout {bool} If true, capture and return stdout
    @param check {bool} If true, throw an exception if command returns non-zero
    @note This assumes small amounts of output only
    """
    if stdout:
        stdout = subprocess.PIPE
    proc = subprocess.Popen(argv, stdout=stdout)
    output, dummy = proc.communicate()
    if check and proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, argv[0])
    return output

def codesign(app, certificate=None, password="", codesign_exe=None):
    """ Sign the given application
    @param app {str} The absolute path to the .app bundle to sign
    @param certificate {str} The absolute path to a PKCS12 file containing both
        the certificate and the private key used to sign.  It must have an empty
        password.  This can be exported via Keychain Access.
    @param password {str} Optional, used if the certificate requires a password.
    @param codesign_exe {str} Optional, location of codesign executable to use.
    """
    if not os.path.exists(os.path.join(app, "Contents", "Info.plist")):
        raise RuntimeError("%s does not appear to be an application" % (app,))
    if certificate is None:
        raise RuntimeError("No certificate given")
    if not os.path.exists(certificate):
        raise RuntimeError("Certificate file does not exist")
    if not codesign_exe:
        codesign_exe = "/usr/bin/codesign"
    if not os.path.exists(codesign_exe):
        raise RuntimeError("codesign exe does not exist at %r" % (codesign_exe,))

    dirname = os.path.dirname(os.path.abspath(__file__))
    tempdir = tempfile.mkdtemp()
    keychain = os.path.join(tempdir, "codesign.keychain")

    try:
        run(["/usr/bin/security", "create-keychain", "-p", "", keychain])
        run(["/usr/bin/security", "unlock-keychain", "-p", "", keychain])
        argv = ["/usr/bin/security", "import", certificate, "-k", keychain]
        if password is not None:
            argv += ["-P", password]
        else:
            print("Please enter passpharse (via the GUI)...")
        argv += ["-x", "-T", codesign_exe]
        run(argv)
        run(["/usr/bin/security", "unlock-keychain", "-p", "", keychain])
        stdout = run(["/usr/bin/security", "find-identity", "-v",
                      "-p", "codesigning", keychain], stdout=True)
        for line in stdout.splitlines():
            if line[3] == ")":
                # this is a cert
                identity = line.split('"')[-2]
                break
        else:
            raise RuntimeError("Failed to find identity in imported keychain")
        run([codesign_exe, "--sign", identity,
             "--keychain", keychain, "--force", "--deep", "--verbose",
             # Requirements causes problems with "--deep", resulting in signed
             # files that won't pass the verification step.
             # "--requirements", os.path.join(dirname, "requirements.txt"),
             app])
    finally:
        run(["/usr/bin/security", "delete-keychain", keychain], check=False)
        if os.path.exists(keychain):
            os.unlink(keychain)
        if os.path.exists(tempdir):
            os.rmdir(tempdir)
    # Display the new requirements so we can see it in the logs
    run([codesign_exe, "--display", "--requirements", "-", app])
    run([codesign_exe, "--verify", "--verbose", app])

def main():
    import optparse
    parser = optparse.OptionParser()
    parser.usage += " <Komodo.app>"
    parser.epilog = " ".join(filter(bool, ("""
        The certificate must be in a format that Keychain Access can import;
        PKCS12 is preferred.  The passpharse for the certificate is
        unfortunately given on the command line, so for security entering via
        the GUI is preferred.  It is undefined which identity in the file will
        be used; for reliable operation, supply a file with only one identity
        (i.e. a single certificate / private key pair).
        """).split()))
    parser.add_option("-f", "--certificate", default=None,
                      help="Certificate file containing signing identity (REQUIRED)")
    parser.add_option("-p", "--password", default=None,
                      help="Unwrapping passphrase for the certificate file; " +
                           "if empty, the user is prompted (via the GUI). " +
                           "By default, an empty passphrase is used.")
    (options, args) = parser.parse_args()
    if not args:
        parser.print_usage()
        sys.exit(1)
    password = options.password
    if password is None:
        password = ""
    elif not password:
        password = None
    codesign(*args, certificate=options.certificate, password=password)

if __name__ == '__main__':
    main()

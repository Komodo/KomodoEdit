# Komodo-specific notes on this vendored paramiko

This is paramiko **1.17.2**, unmodified except for two small compatibility
patches in `paramiko/rsakey.py` and `paramiko/dsskey.py` (see the comments
at the two `generate()`/`sign_ssh_data()`/`verify_ssh_sig()` methods in each
file) needed after the vendored crypto backend was swapped from PyCrypto to
PyCryptodome.

## Why this stays at 1.17.2 (known, accepted residual risk)

paramiko 1.17.2 predates the switch to the `cryptography` library as its
crypto backend (that landed around paramiko 1.18). A real security-relevant
upgrade -- notably the fix for the Terrapin SSH prefix-truncation attack,
**CVE-2023-48795**, which landed in paramiko **3.4.0** -- is not reachable
from this Python-2.7-based build:

- The last paramiko release that still supports Python 2.7 is **2.10.0**
  (2.10.1 requires keyword arguments to `os.open()` that don't exist in
  Python 2.7).
- The last `cryptography` release that still supports Python 2.7 is in its
  **2.x** series (`cryptography` dropped Python 2.7 support at 3.0).
- The Terrapin fix (3.4.0) is far beyond both of those ceilings.

So there is no version of paramiko this Python-2.7 build can vendor that
both (a) still runs on Python 2.7 and (b) includes the Terrapin fix or any
paramiko-level CVE fix from after ~2018. This is a hard architectural
ceiling, not a "just try a newer version" problem -- this whole codebase
(PyXPCOM has never had a Python 3 port) is bound to Python 2.7.

**Decision (2026-07-22):** paramiko stays at 1.17.2 here. Modernizing SSH/
SFTP/SCP support to a real Python-3-based paramiko (3.x, with the Terrapin
fix and a `cryptography`/`bcrypt`/`pynacl` backend) is scoped as a *new
feature* for `qtedit/` (the Python-3/Qt rewrite of this application), not a
patch to this legacy tree -- see the project's modernization roadmap.

## What *was* fixed here

- `PyCrypto` (unmaintained since ~2013, CVE-2013-7459, CVE-2012-2417) was
  replaced with `PyCryptodome` (actively maintained, same `Crypto.*` import
  namespace) -- see `contrib/pycryptodome/`.
- `ecdsa` was bumped 0.11 -> 0.19.2 (still does not fix CVE-2024-23342, a
  timing side-channel the ecdsa maintainers consider out of scope for a
  pure-Python library by design -- only relevant if a user's SSH auth key or
  a remote host's key uses ECDSA).

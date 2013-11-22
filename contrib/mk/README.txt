# README for 'mk' project

<http://svn.openkomodo.com/repos/mk>

This is a Makefile/make replacement written in Python. You put a
`Makefile.py` at the base of your project. Makefile tasks are classes
that subclass from `mklib.Task`. Then you run `mk TASK` like you would run
GNU `make TASK`.

TODO: fill out this readme, obviously a lot more needs to be documented


versions, branches, releases
----------------------------

This is the mk 0.x (the trunk).  See CHANGES.txt for details on recent
changes. This is currently the only active branch.

Releases are tagged in
<http://svn.openkomodo.com/repos/mk/tags/$version>.
The latest current releases are: 0.7.1.



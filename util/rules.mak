# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# Miscellaneous things to make it easier to build things
# in the Komodo area.

MOZSRC=/mozilla_source/mozilla
MOZIDL=$(MOZSRC)/dist/idl
MOZINCS=-I$(MOZIDL) \
	-I$(MOZSRC)/dist/WIN32_D.OBJ/include \
	-I../SciMoz \
	-I$(MOZSRC)/dist/include \
	-I../idl
MOZBIN=$(MOZSRC)/dist/WIN32_D.OBJ/bin
MOZCOMPONENTS=$(MOZBIN)/components
XPIDL=$(MOZBIN)/xpidl

.SUFFIXES: .idl .xpt

.idl.xpt:
	$(XPIDL) -m typelib -w -v $(MOZINCS) $<


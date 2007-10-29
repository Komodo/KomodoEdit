# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

# Makefile to build "komodo.msi".

# UI library:
# The first one here is for development: playing with the UI lib built directly
# in the "aswixui" project dir.
#UILIB=C:\trentm\as\main\support\aswixui\aswixui_featuretree.wixlib
UILIB=aswixui\aswixui_featuretree.wixlib

CANDLE=candle.exe -nologo
LIGHT=light.exe -nologo
ORCA="C:\Program Files\Orca\Orca.exe"
MAKE=nmake -nologo

PRODNAME=komodo
OBJECTS=$(PRODNAME).wixobj feature-core.wixobj feature-docs.wixobj feature-env.wixobj
INCLUDES=config.wxi guids.wxi
LIBS=$(UILIB)

all: $(PRODNAME).msi

$(PRODNAME).msi: $(OBJECTS) $(LIBS)
	$(LIGHT) -out $(PRODNAME).msi $(OBJECTS) $(LIBS)

$(UILIB): aswixui\*.wxs
	cd aswixui && $(MAKE)

#TODO Do nmake-templating-fu for this bit. Maybe this is right:
#.wxs.wixobj:
#	$(CANDLE) $<
$(PRODNAME).wixobj: $(PRODNAME).wxs $(INCLUDES)
	$(CANDLE) $(PRODNAME).wxs
feature-core.wixobj: feature-core.wxs $(INCLUDES)
	$(CANDLE) feature-core.wxs
feature-docs.wixobj: feature-docs.wxs $(INCLUDES)
	$(CANDLE) feature-docs.wxs
feature-env.wixobj: feature-env.wxs $(INCLUDES)
	$(CANDLE) feature-env.wxs

clean:
	del *.wixobj
	del $(PRODNAME).msi

install:
	msiexec /i $(PRODNAME).msi /l*v install.log

silentinstall:
	msiexec /i $(PRODNAME).msi /l*v install.log /qn

uninstall:
	msiexec /x $(PRODNAME).msi /l*v uninstall.log

cycle: install uninstall

release:
	echo "release" msi to network share for testing
	copy $(PRODNAME).msi H:\tmp

orca:
	$(ORCA) $(PRODNAME).msi




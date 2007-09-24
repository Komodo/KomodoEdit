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




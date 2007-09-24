# Makefile for ASWIXUI (the ActiveState WiX UI) library.

all: aswixui

OBJ_DIR=build
SRC_DIR=.

CANDLE=candle.exe
LIGHT=light.exe
LIT=lit.exe

CANDLE_FLAGS=-nologo
LIT_FLAGS=-nologo
LIGHT_FLAGS=-nologo

OBJ_FILES=\
    $(OBJ_DIR)\BrowseDlg.wixobj \
    $(OBJ_DIR)\CancelDlg.wixobj \
    $(OBJ_DIR)\Common.wixobj \
    $(OBJ_DIR)\CustomizeDlg.wixobj \
    $(OBJ_DIR)\DiskCostDlg.wixobj \
    $(OBJ_DIR)\ErrorDlg.wixobj \
    $(OBJ_DIR)\ExitDialog.wixobj \
    $(OBJ_DIR)\FatalError.wixobj \
    $(OBJ_DIR)\FilesInUse.wixobj \
    $(OBJ_DIR)\LicenseAgreementDlg.wixobj \
    $(OBJ_DIR)\MaintenanceTypeDlg.wixobj \
    $(OBJ_DIR)\MaintenanceWelcomeDlg.wixobj \
    $(OBJ_DIR)\OutOfDiskDlg.wixobj \
    $(OBJ_DIR)\OutOfRbDiskDlg.wixobj \
    $(OBJ_DIR)\PrepareDlg.wixobj \
    $(OBJ_DIR)\ProgressDlg.wixobj \
    $(OBJ_DIR)\ResumeDlg.wixobj \
    $(OBJ_DIR)\SetupTypeDlg.wixobj \
    $(OBJ_DIR)\UserExit.wixobj \
    $(OBJ_DIR)\VerifyReadyDlg.wixobj \
    $(OBJ_DIR)\VerifyRemoveDlg.wixobj \
    $(OBJ_DIR)\VerifyRepairDlg.wixobj \
    $(OBJ_DIR)\WaitForCostingDlg.wixobj \
    $(OBJ_DIR)\WelcomeDlg.wixobj \
    $(OBJ_DIR)\WelcomeEulaDlg.wixobj \

FEATURETREE_OBJ_FILES=\
    $(OBJ_DIR)\WixUI_FeatureTree.wixobj \


# rules
.SUFFIXES : .wxs .wixobj

{$(SRC_DIR)}.wxs.wixobj::
    $(CANDLE) $(CANDLE_FLAGS) -out $(OBJ_DIR)\ $<
{$(SRC_DIR)\featuretree}.wxs.wixobj::
    $(CANDLE) $(CANDLE_FLAGS) -out $(OBJ_DIR)\ $<


# targets
aswixui_featuretree.wixlib : $(OBJ_FILES) $(FEATURETREE_OBJ_FILES)
    $(LIT) $(LIT_FLAGS) -out $@ $**

mkdirs:
	@if not exist "$(OBJ_DIR)" mkdir $(OBJ_DIR)

clean:
	-rd /q/s $(OBJ_DIR)
	-del /q aswixui*.wixlib

aswixui: mkdirs aswixui_featuretree.wixlib
    @echo 'aswixui_featuretree.wixlib' created


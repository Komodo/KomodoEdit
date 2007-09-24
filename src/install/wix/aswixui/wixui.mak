#    Copyright (c) Microsoft Corporation.  All rights reserved.
#
#    The use and distribution terms for this software are covered by the
#    Common Public License 1.0 (http://opensource.org/licenses/cpl.php)
#    which can be found in the file CPL.TXT at the root of this distribution.
#    By using this software in any fashion, you are agreeing to be bound by
#    the terms of this license.
#
#    You must not remove this notice, or any other, from this software.
#

###################
# build variables
#
WIXUI_OBJ_DIR = $(OBJ_DIR)\wixui
WIXUI_SRC_DIR = $(SRC_DIR)\ui\wixui
WIXUI_FEATURETREE_SRC_DIR = $(WIXUI_SRC_DIR)\featuretree
WIXUI_MINIMAL_SRC_DIR = $(WIXUI_SRC_DIR)\minimal
WIXUI_MONDO_SRC_DIR = $(WIXUI_SRC_DIR)\mondo

WIXUI_COMMON_OBJ_FILES=\
    $(WIXUI_OBJ_DIR)\BrowseDlg.wixobj \
    $(WIXUI_OBJ_DIR)\CancelDlg.wixobj \
    $(WIXUI_OBJ_DIR)\Common.wixobj \
    $(WIXUI_OBJ_DIR)\CustomizeDlg.wixobj \
    $(WIXUI_OBJ_DIR)\DiskCostDlg.wixobj \
    $(WIXUI_OBJ_DIR)\ErrorDlg.wixobj \
    $(WIXUI_OBJ_DIR)\ExitDialog.wixobj \
    $(WIXUI_OBJ_DIR)\FatalError.wixobj \
    $(WIXUI_OBJ_DIR)\FilesInUse.wixobj \
    $(WIXUI_OBJ_DIR)\LicenseAgreementDlg.wixobj \
    $(WIXUI_OBJ_DIR)\MaintenanceTypeDlg.wixobj \
    $(WIXUI_OBJ_DIR)\MaintenanceWelcomeDlg.wixobj \
    $(WIXUI_OBJ_DIR)\OutOfDiskDlg.wixobj \
    $(WIXUI_OBJ_DIR)\OutOfRbDiskDlg.wixobj \
    $(WIXUI_OBJ_DIR)\PrepareDlg.wixobj \
    $(WIXUI_OBJ_DIR)\ProgressDlg.wixobj \
    $(WIXUI_OBJ_DIR)\ResumeDlg.wixobj \
    $(WIXUI_OBJ_DIR)\SetupTypeDlg.wixobj \
    $(WIXUI_OBJ_DIR)\UserExit.wixobj \
    $(WIXUI_OBJ_DIR)\VerifyReadyDlg.wixobj \
    $(WIXUI_OBJ_DIR)\VerifyRemoveDlg.wixobj \
    $(WIXUI_OBJ_DIR)\VerifyRepairDlg.wixobj \
    $(WIXUI_OBJ_DIR)\WaitForCostingDlg.wixobj \
    $(WIXUI_OBJ_DIR)\WelcomeDlg.wixobj \
    $(WIXUI_OBJ_DIR)\WelcomeEulaDlg.wixobj \

WIXUI_FEATURETREE_OBJ_FILES=\
    $(WIXUI_OBJ_DIR)\WixUI_FeatureTree.wixobj \

WIXUI_MINMAL_OBJ_FILES=\
    $(WIXUI_OBJ_DIR)\WixUI_Minimal.wixobj \

WIXUI_MONDO_OBJ_FILES=\
    $(WIXUI_OBJ_DIR)\WixUI_Mondo.wixobj \


###################
# build rules
#
.SUFFIXES : .wxs .wixobj

{$(WIXUI_SRC_DIR)}.wxs.wixobj::
    $(CANDLE) $(CANDLE_FLAGS) -out $(WIXUI_OBJ_DIR)\ $<

{$(WIXUI_FEATURETREE_SRC_DIR)}.wxs.wixobj::
    $(CANDLE) $(CANDLE_FLAGS) -out $(WIXUI_OBJ_DIR)\ $<

{$(WIXUI_MINIMAL_SRC_DIR)}.wxs.wixobj::
    $(CANDLE) $(CANDLE_FLAGS) -out $(WIXUI_OBJ_DIR)\ $<

{$(WIXUI_MONDO_SRC_DIR)}.wxs.wixobj::
    $(CANDLE) $(CANDLE_FLAGS) -out $(WIXUI_OBJ_DIR)\ $<


###################
# build targets
#
cleanwixui:
    -rd /s /q $(WIXUI_OBJ_DIR)
    -del /q $(UI_DIR)\wixui*.wixlib

wixuidirs:
    @if not exist "$(UI_DIR)" mkdir $(UI_DIR)
    @if not exist "$(UI_DIR)\Bitmaps" mkdir $(UI_DIR)\Bitmaps
    @if not exist "$(WIXUI_OBJ_DIR)" mkdir $(WIXUI_OBJ_DIR)
    @cd $(WIXUI_OBJ_DIR)

wixuibin:
   @copy "$(WIXUI_SRC_DIR)\Bitmaps" "$(UI_DIR)\Bitmaps"

$(UI_DIR)\wixui_featuretree.wixlib : $(WIXUI_COMMON_OBJ_FILES) $(WIXUI_FEATURETREE_OBJ_FILES)
    $(LIT) $(LIT_FLAGS) -out $@ $**

$(UI_DIR)\wixui_minimal.wixlib : $(WIXUI_COMMON_OBJ_FILES) $(WIXUI_MINIMAL_OBJ_FILES)
    $(LIT) $(LIT_FLAGS) -out $@ $**

$(UI_DIR)\wixui_mondo.wixlib : $(WIXUI_COMMON_OBJ_FILES) $(WIXUI_MONDO_OBJ_FILES)
    $(LIT) $(LIT_FLAGS) -out $@ $**

wixui: wixuidirs $(UI_DIR)\wixui_featuretree.wixlib $(UI_DIR)\wixui_minimal.wixlib $(UI_DIR)\wixui_mondo.wixlib wixuibin
    @echo wixui (wixui*.wixlib): - Success.

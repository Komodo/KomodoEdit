/* Copyright (c) 2011 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

#include <mozilla/ModuleUtils.h>

#include "koSciMozIMEHelper.h"

NS_GENERIC_FACTORY_CONSTRUCTOR(koSciMozIMEHelper)

NS_DEFINE_NAMED_CID(KOSCIMOZIMEHELPER_CID);

static const mozilla::Module::CIDEntry kModuleCIDs[] = {
    { &kKOSCIMOZIMEHELPER_CID, true, NULL, koSciMozIMEHelperConstructor },
    { NULL }
};

static const mozilla::Module::ContractIDEntry kModuleContracts[] = {
    { KOSCIMOZIMEHELPER_CONTRACTID, &kKOSCIMOZIMEHELPER_CID },
    { NULL }
};

static const mozilla::Module::CategoryEntry kModuleCategories[] = {
    { NULL }
};

static const mozilla::Module kModule = {
    mozilla::Module::kVersion,
    kModuleCIDs,
    kModuleContracts,
    kModuleCategories
};

NSMODULE_DEFN(koSciMozIMEHelperModule) = &kModule;

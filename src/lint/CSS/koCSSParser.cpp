/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */
#include "nsXPCOM.h"
#include "nsCOMPtr.h"

#include "nsILocalFile.h"
#include "nsNetUtil.h"

#include "nsContentCID.h"
#include "koICSSParser.h"

#include "mozilla/css/Loader.h"
#include "nsCSSStyleSheet.h"

#include "mozilla/ModuleUtils.h"


// {7D82F06D-CF2D-11DA-AE2F-000D935D3368}
#define KO_CSSPARSER_CID \
{ 0x7D82F06D, 0xCF2D, 0x11DA, { 0xAE, 0x2F, 0x00, 0x0D, 0x93, 0x5D, 0x33, 0x68 } }
#define KO_CSSPARSER_CONTRACTID "@activestate.com/koCSSParser;1"

static NS_DEFINE_CID(kCSSLoaderCID, KO_CSSPARSER_CID);
NS_DEFINE_NAMED_CID(KO_CSSPARSER_CID);


class koCSSParser : public koICSSParser
{
public:
  NS_DECL_ISUPPORTS
  NS_DECL_KOICSSPARSER

  koCSSParser();
  virtual ~koCSSParser();
};

NS_IMPL_ISUPPORTS1(koCSSParser, koICSSParser)

koCSSParser::koCSSParser()
{
  NS_INIT_ISUPPORTS();
}

koCSSParser::~koCSSParser()
{
}

static already_AddRefed<nsIURI>
FileToURI(const char *aFilename, nsresult *aRv = 0)
{
    nsCOMPtr<nsILocalFile> lf(do_CreateInstance(NS_LOCAL_FILE_CONTRACTID, aRv));
    NS_ENSURE_TRUE(lf, nullptr);
    // XXX Handle relative paths somehow.
    lf->InitWithNativePath(nsDependentCString(aFilename));

    nsIURI *uri = nullptr;
    nsresult rv = NS_NewFileURI(&uri, lf);
    if (aRv)
        *aRv = rv;
    return uri;
}

NS_IMETHODIMP koCSSParser::ParseFile(const char *filename)
{
    nsRefPtr<mozilla::css::Loader> loader = new mozilla::css::Loader();
    nsRefPtr<nsCSSStyleSheet> sheet;
    nsresult rv;
    nsCOMPtr<nsIURI> aSheetURI = FileToURI(filename, &rv);
    if (!aSheetURI) {
      return NS_ERROR_FILE_NOT_FOUND;
    }
    loader->LoadSheetSync(aSheetURI, getter_AddRefs(sheet));
    NS_ASSERTION(sheet, "sheet load failed");
    /* This can happen if the file can't be found (e.g. you
     * ask for a relative path and xpcom/io rejects it)
     */
    if (!sheet) {
        return NS_ERROR_FILE_NOT_FOUND;
    }
    return NS_OK;
}

NS_GENERIC_FACTORY_CONSTRUCTOR(koCSSParser)

static const mozilla::Module::CIDEntry kModuleCIDs[] = {
    { &kKO_CSSPARSER_CID, true, NULL, koCSSParserConstructor },
    { NULL }
};

static const mozilla::Module::ContractIDEntry kModuleContracts[] = {
    { KO_CSSPARSER_CONTRACTID, &kKO_CSSPARSER_CID },
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

// The following line implements the one-and-only "NSModule" symbol exported from this
// shared library.
NSMODULE_DEFN(koCSSParserModule) = &kModule;

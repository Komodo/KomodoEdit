/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */
#include "nsXPCOM.h"
#include "nsCOMPtr.h"

#include "nsIGenericFactory.h"
#include "nsILocalFile.h"
#include "nsNetUtil.h"

#include "nsContentCID.h"
#include "nsICSSLoader.h"
#include "nsICSSStyleSheet.h"
#include "koICSSParser.h"

static NS_DEFINE_CID(kCSSLoaderCID, NS_CSS_LOADER_CID);



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
    NS_ENSURE_TRUE(lf, nsnull);
    // XXX Handle relative paths somehow.
    lf->InitWithNativePath(nsDependentCString(aFilename));

    nsIURI *uri = nsnull;
    nsresult rv = NS_NewFileURI(&uri, lf);
    if (aRv)
        *aRv = rv;
    return uri;
}

NS_IMETHODIMP koCSSParser::ParseFile(const char *filename)
{
    nsCOMPtr<nsICSSLoader> loader(do_CreateInstance(kCSSLoaderCID));
    nsCOMPtr<nsICSSStyleSheet> sheet;
    nsresult rv;
    nsCOMPtr<nsIURI> aSheetURI = FileToURI(filename, &rv);
    if (!aSheetURI) {
      return NS_ERROR_FILE_NOT_FOUND;
    }
#if MOZ_VERSION < 190
    loader->LoadAgentSheet(aSheetURI, getter_AddRefs(sheet));
#else
    loader->LoadSheetSync(aSheetURI, getter_AddRefs(sheet));
#endif
    NS_ASSERTION(sheet, "sheet load failed");
    /* This can happen if the file can't be found (e.g. you
     * ask for a relative path and xpcom/io rejects it)
     */
    if (!sheet) {
        return NS_ERROR_FILE_NOT_FOUND;
    }
    PRBool complete;
    sheet->GetComplete(complete);
    NS_ASSERTION(complete, "synchronous load did not complete");
    if (!complete) {
        return NS_ERROR_UNEXPECTED;
    }
    return NS_OK;
}

// {7D82F06D-CF2D-11DA-AE2F-000D935D3368}
#define KO_CSSPARSER_CID \
{ 0x7D82F06D, 0xCF2D, 0x11DA, { 0xAE, 0x2F, 0x00, 0x0D, 0x93, 0x5D, 0x33, 0x68 } }
#define KO_CSSPARSER_CONTRACTID "@activestate.com/koCSSParser;1"

NS_GENERIC_FACTORY_CONSTRUCTOR(koCSSParser)

static nsModuleComponentInfo components[] =
{
  { 
    "Komodo CSS Parser",
    KO_CSSPARSER_CID,
    KO_CSSPARSER_CONTRACTID,
    koCSSParserConstructor,
    NULL, // RegistrationProc /* NULL if you dont need one */,
    NULL // UnregistrationProc /* NULL if you dont need one */
  }
};

NS_IMPL_NSGETMODULE("koCSSParserModule", components)

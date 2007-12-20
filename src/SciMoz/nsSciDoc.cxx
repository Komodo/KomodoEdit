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

#include <cstring>
#include <cstdio>
#include <cstdlib>

#include "Platform.h"

#include "Scintilla.h"
#include "SVector.h"
#include "SplitVector.h"
#include "Partitioning.h"
#include "RunStyles.h"
#include "CellBuffer.h"
#include "CharClassify.h"
#include "Decoration.h"
#include "Document.h"

#include "nsIAllocator.h"
#include "nsIGenericFactory.h"
#include "nsString.h"
#include "ISciDoc.h"

using namespace Scintilla;

/* Header file */
class SciDoc : public ISciDoc
{
public:
  NS_DECL_ISUPPORTS
  NS_DECL_ISCIDOC

  SciDoc();

private:
  ~SciDoc();
  Document *documentPointer;

protected:
  /* additional members */
};

/* Implementation file */
NS_IMPL_ISUPPORTS1(SciDoc, ISciDoc)

SciDoc::SciDoc()
{
  /* member initializers and constructor code */
    documentPointer = new Document();
    if (documentPointer) {
        documentPointer->AddRef();
    }
}

SciDoc::~SciDoc()
{
    /* destructor code */
    if (documentPointer!=nsnull) {
        documentPointer->Release();
    }
}

/* attribute long document; */
NS_IMETHODIMP SciDoc::GetDocPointer(PRInt32 *aDocument)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *aDocument = reinterpret_cast<PRInt32>(documentPointer);
    return NS_OK;
}
NS_IMETHODIMP SciDoc::SetDocPointer(PRInt32 aDocument)
{
    if (documentPointer!=nsnull) {
        documentPointer->Release();
    }
    documentPointer = reinterpret_cast<Document *>(aDocument);
    if (documentPointer) {
            documentPointer->AddRef();
    }
    return NS_OK;
}

NS_IMETHODIMP SciDoc::GetText(PRUnichar ** text)
{
    return GetCharRange(0, documentPointer->Length(), text);
}
NS_IMETHODIMP SciDoc::SetText(const PRUnichar * aText)
{
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciDoc::SetText\n");
#endif
        // SCI_SETTEXT from Editor.cxx
        documentPointer->BeginUndoAction();
        documentPointer->DeleteChars(0, documentPointer->Length());
        // SetEmptySelection(0);
	if (documentPointer->dbcsCodePage == 0) {
	    documentPointer->InsertCString(0, NS_LossyConvertUTF16toASCII(aText).get());
	} else {
	    documentPointer->InsertCString(0, NS_ConvertUTF16toUTF8(aText).get());
	}
        documentPointer->EndUndoAction();

	return NS_OK;
}

/* attribute PRInt32 stylingBits; */
NS_IMETHODIMP SciDoc::GetStylingBits(PRInt32 *aStylingBits)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *aStylingBits = documentPointer->stylingBits;
    return NS_OK;
}
NS_IMETHODIMP SciDoc::SetStylingBits(PRInt32 aStylingBits)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->stylingBits = aStylingBits;
    return NS_OK;
}

/* attribute PRInt32 stylingBitsMask; */
NS_IMETHODIMP SciDoc::GetStylingBitsMask(PRInt32 *aStylingBitsMask)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *aStylingBitsMask = documentPointer->stylingBitsMask;
    return NS_OK;
}
NS_IMETHODIMP SciDoc::SetStylingBitsMask(PRInt32 aStylingBitsMask)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->stylingBitsMask = aStylingBitsMask;
    return NS_OK;
}

/* attribute PRInt32 eolMode; */
NS_IMETHODIMP SciDoc::GetEolMode(PRInt32 *aEolMode)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *aEolMode = documentPointer->eolMode;
    return NS_OK;
}
NS_IMETHODIMP SciDoc::SetEolMode(PRInt32 aEolMode)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->eolMode = aEolMode;
    return NS_OK;
}

/* attribute PRInt32 dbcsCodePage; */
NS_IMETHODIMP SciDoc::GetDbcsCodePage(PRInt32 *aDbcsCodePage)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *aDbcsCodePage = documentPointer->dbcsCodePage;
    return NS_OK;
}
NS_IMETHODIMP SciDoc::SetDbcsCodePage(PRInt32 aDbcsCodePage)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->dbcsCodePage = aDbcsCodePage;
    return NS_OK;
}

/* attribute PRInt32 tabInChars; */
NS_IMETHODIMP SciDoc::GetTabInChars(PRInt32 *aTabInChars)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *aTabInChars = documentPointer->tabInChars;
    return NS_OK;
}
NS_IMETHODIMP SciDoc::SetTabInChars(PRInt32 aTabInChars)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->tabInChars = aTabInChars;
    return NS_OK;
}

/* attribute PRInt32 indentInChars; */
NS_IMETHODIMP SciDoc::GetIndentInChars(PRInt32 *aIndentInChars)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *aIndentInChars = documentPointer->indentInChars;
    return NS_OK;
}
NS_IMETHODIMP SciDoc::SetIndentInChars(PRInt32 aIndentInChars)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->indentInChars = aIndentInChars;
    return NS_OK;
}

/* attribute PRInt32 actualIndentInChars; */
NS_IMETHODIMP SciDoc::GetActualIndentInChars(PRInt32 *aActualIndentInChars)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *aActualIndentInChars = documentPointer->actualIndentInChars;
    return NS_OK;
}
NS_IMETHODIMP SciDoc::SetActualIndentInChars(PRInt32 aActualIndentInChars)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->actualIndentInChars = aActualIndentInChars;
    return NS_OK;
}

/* attribute boolean useTabs; */
NS_IMETHODIMP SciDoc::GetUseTabs(PRBool *aUseTabs)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *aUseTabs = documentPointer->useTabs;
    return NS_OK;
}
NS_IMETHODIMP SciDoc::SetUseTabs(PRBool aUseTabs)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->useTabs = aUseTabs;
    return NS_OK;
}

/* attribute boolean tabIndents; */
NS_IMETHODIMP SciDoc::GetTabIndents(PRBool *aTabIndents)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *aTabIndents = documentPointer->tabIndents;
    return NS_OK;
}
NS_IMETHODIMP SciDoc::SetTabIndents(PRBool aTabIndents)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->tabIndents = aTabIndents;
    return NS_OK;
}

/* attribute boolean backspaceUnindents; */
NS_IMETHODIMP SciDoc::GetBackspaceUnindents(PRBool *aBackspaceUnindents)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *aBackspaceUnindents = documentPointer->backspaceUnindents;
    return NS_OK;
}
NS_IMETHODIMP SciDoc::SetBackspaceUnindents(PRBool aBackspaceUnindents)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->backspaceUnindents = aBackspaceUnindents;
    return NS_OK;
}

/* PRInt32 LineFromPosition (in PRInt32 pos); */
NS_IMETHODIMP SciDoc::LineFromPosition(PRInt32 pos, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->LineFromPosition(pos);
    return NS_OK;
}

/* PRInt32 ClampPositionIntoDocument (in PRInt32 pos); */
NS_IMETHODIMP SciDoc::ClampPositionIntoDocument(PRInt32 pos, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->ClampPositionIntoDocument(pos);
    return NS_OK;
}

/* boolean IsCrLf (in PRInt32 pos); */
NS_IMETHODIMP SciDoc::IsCrLf(PRInt32 pos, PRBool *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->IsCrLf(pos);
    return NS_OK;
}

/* PRInt32 LenChar (in PRInt32 pos); */
NS_IMETHODIMP SciDoc::LenChar(PRInt32 pos, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->LenChar(pos);
    return NS_OK;
}

/* PRInt32 MovePositionOutsideChar (in PRInt32 pos, in PRInt32 moveDir, in boolean checkLineEnd); */
NS_IMETHODIMP SciDoc::MovePositionOutsideChar(PRInt32 pos, PRInt32 moveDir, PRBool checkLineEnd, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->MovePositionOutsideChar(pos, moveDir, checkLineEnd);
    return NS_OK;
}

/* PRInt32 GetBytePositionForCharOffset (in PRInt32 bytePos, in PRInt32 charOffset, in boolean checkLineEnd); */
NS_IMETHODIMP SciDoc::GetBytePositionForCharOffset(PRInt32 bytePos, PRInt32 charOffset, PRBool checkLineEnd, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->GetBytePositionForCharOffset(bytePos, charOffset, checkLineEnd);
    return NS_OK;
}

/* void ModifiedAt (in PRInt32 pos); */
NS_IMETHODIMP SciDoc::ModifiedAt(PRInt32 pos)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->ModifiedAt(pos);
    return NS_OK;
}

/* boolean DeleteChars (in PRInt32 pos, in PRInt32 len); */
NS_IMETHODIMP SciDoc::DeleteChars(PRInt32 pos, PRInt32 len, PRBool *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->DeleteChars(pos, len);
    return NS_OK;
}

/* boolean InsertString (in PRInt32 position, in wstring s); */
NS_IMETHODIMP SciDoc::InsertString(PRInt32 position, const PRUnichar *s, PRBool *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    nsCAutoString text = NS_ConvertUTF16toUTF8(s);
    *_retval = documentPointer->InsertString(position,
                                             reinterpret_cast<const char *>(text.get()),
                                             text.Length());
    return NS_OK;
}

/* PRInt32 Undo (); */
NS_IMETHODIMP SciDoc::Undo(PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->Undo();
    return NS_OK;
}

/* PRInt32 Redo (); */
NS_IMETHODIMP SciDoc::Redo(PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->Redo();
    return NS_OK;
}

/* boolean CanUndo (); */
NS_IMETHODIMP SciDoc::CanUndo(PRBool *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->CanUndo();
    return NS_OK;
}

/* boolean CanRedo (); */
NS_IMETHODIMP SciDoc::CanRedo(PRBool *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->CanRedo();
    return NS_OK;
}

/* void DeleteUndoHistory (); */
NS_IMETHODIMP SciDoc::DeleteUndoHistory()
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->DeleteUndoHistory();
    return NS_OK;
}

/* boolean SetUndoCollection (in boolean collectUndo); */
NS_IMETHODIMP SciDoc::SetUndoCollection(PRBool collectUndo, PRBool *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->SetUndoCollection(collectUndo);
    return NS_OK;
}

/* boolean IsCollectingUndo (); */
NS_IMETHODIMP SciDoc::IsCollectingUndo(PRBool *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->IsCollectingUndo();
    return NS_OK;
}

/* void BeginUndoAction (); */
NS_IMETHODIMP SciDoc::BeginUndoAction()
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->BeginUndoAction();
    return NS_OK;
}

/* void EndUndoAction (); */
NS_IMETHODIMP SciDoc::EndUndoAction()
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->EndUndoAction();
    return NS_OK;
}

/* void SetSavePoint (); */
NS_IMETHODIMP SciDoc::SetSavePoint()
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->SetSavePoint();
    return NS_OK;
}

/* boolean IsSavePoint (); */
NS_IMETHODIMP SciDoc::IsSavePoint(PRBool *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->IsSavePoint();
    return NS_OK;
}

/* PRInt32 GetLineIndentation (in PRInt32 line); */
NS_IMETHODIMP SciDoc::GetLineIndentation(PRInt32 line, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->GetLineIndentation(line);
    return NS_OK;
}

/* void SetLineIndentation (in PRInt32 line, in PRInt32 indent); */
NS_IMETHODIMP SciDoc::SetLineIndentation(PRInt32 line, PRInt32 indent)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->SetLineIndentation(line, indent);
    return NS_OK;
}

/* PRInt32 GetLineIndentPosition (in PRInt32 line); */
NS_IMETHODIMP SciDoc::GetLineIndentPosition(PRInt32 line, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->GetLineIndentPosition(line);
    return NS_OK;
}

/* PRInt32 GetColumn (in PRInt32 position); */
NS_IMETHODIMP SciDoc::GetColumn(PRInt32 position, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->GetColumn(position);
    return NS_OK;
}

/* PRInt32 FindColumn (in PRInt32 line, in PRInt32 column); */
NS_IMETHODIMP SciDoc::FindColumn(PRInt32 line, PRInt32 column, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->FindColumn(line, column);
    return NS_OK;
}

/* void Indent (in boolean forwards, in PRInt32 lineBottom, in PRInt32 lineTop); */
NS_IMETHODIMP SciDoc::Indent(PRBool forwards, PRInt32 lineBottom, PRInt32 lineTop)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->Indent(forwards, lineBottom, lineTop);
    return NS_OK;
}

/* wstring TransformLineEnds (in wstring s, in PRInt32 eolMode); */
NS_IMETHODIMP SciDoc::TransformLineEnds(const PRUnichar *s, PRInt32 eolMode, PRUnichar **_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    nsCAutoString text = NS_ConvertUTF16toUTF8(s);
    int lenOut = 0;
    char *buffer = documentPointer->TransformLineEnds(&lenOut,
                                             reinterpret_cast<const char *>(text.get()),
                                             text.Length(),
                                             eolMode);
    if (documentPointer->dbcsCodePage == 0) {
        *_retval =  ToNewUnicode(NS_ConvertASCIItoUTF16(buffer));
    } else {
        *_retval =  ToNewUnicode(NS_ConvertUTF8toUTF16(buffer));
    }
    return NS_OK;
}

/* void ConvertLineEnds (in PRInt32 eolModeSet); */
NS_IMETHODIMP SciDoc::ConvertLineEnds(PRInt32 eolModeSet)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->ConvertLineEnds(eolModeSet);
    return NS_OK;
}

/* void SetReadOnly (in boolean set); */
NS_IMETHODIMP SciDoc::SetReadOnly(PRBool set)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->SetReadOnly(set);
    return NS_OK;
}

/* boolean IsReadOnly (); */
NS_IMETHODIMP SciDoc::IsReadOnly(PRBool *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->IsReadOnly();
    return NS_OK;
}

/* boolean InsertChar (in PRInt32 pos, in wchar ch); */
NS_IMETHODIMP SciDoc::InsertChar(PRInt32 pos, PRUnichar ch, PRBool *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->InsertChar(pos, ch);
    return NS_OK;
}

/* void ChangeChar (in PRInt32 pos, in wchar ch); */
NS_IMETHODIMP SciDoc::ChangeChar(PRInt32 pos, PRUnichar ch)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->InsertChar(pos, ch);
    return NS_OK;
}

/* void DelChar (in PRInt32 pos); */
NS_IMETHODIMP SciDoc::DelChar(PRInt32 pos)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->DelChar(pos);
    return NS_OK;
}

/* void DelCharBack (in PRInt32 pos); */
NS_IMETHODIMP SciDoc::DelCharBack(PRInt32 pos)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->DelCharBack(pos);
    return NS_OK;
}

/* wchar CharAt (in PRInt32 position); */
NS_IMETHODIMP SciDoc::CharAt(PRInt32 position, PRUnichar *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->CharAt(position);
    return NS_OK;
}

/* wstring GetCharRange (in PRInt32 position, in PRInt32 lengthRetrieve); */
NS_IMETHODIMP SciDoc::GetCharRange(PRInt32 position, PRInt32 lengthRetrieve, PRUnichar **_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    char *buffer = new char[lengthRetrieve + 1];
    if (!buffer)
            return NS_ERROR_OUT_OF_MEMORY;
    buffer[lengthRetrieve]=0;
    documentPointer->GetCharRange(buffer, position, lengthRetrieve);

    NS_ASSERTION(buffer[lengthRetrieve] == NULL, "Buffer overflow");

    if (documentPointer->dbcsCodePage == 0) {
        *_retval =  ToNewUnicode(NS_ConvertASCIItoUTF16(buffer));
    } else {
        *_retval =  ToNewUnicode(NS_ConvertUTF8toUTF16(buffer));
    }

    delete []buffer;
    return NS_OK;
}

/* wchar StyleAt (in PRInt32 position); */
NS_IMETHODIMP SciDoc::StyleAt(PRInt32 position, PRUnichar *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->StyleAt(position);
    return NS_OK;
}

/* PRInt32 GetMark (in PRInt32 line); */
NS_IMETHODIMP SciDoc::GetMark(PRInt32 line, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->GetMark(line);
    return NS_OK;
}

/* PRInt32 AddMark (in PRInt32 line, in PRInt32 markerNum); */
NS_IMETHODIMP SciDoc::AddMark(PRInt32 line, PRInt32 markerNum, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->AddMark(line, markerNum);
    return NS_OK;
}

/* void AddMarkSet (in PRInt32 line, in PRInt32 valueSet); */
NS_IMETHODIMP SciDoc::AddMarkSet(PRInt32 line, PRInt32 valueSet)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->AddMarkSet(line, valueSet);
    return NS_OK;
}

/* void DeleteMark (in PRInt32 line, in PRInt32 markerNum); */
NS_IMETHODIMP SciDoc::DeleteMark(PRInt32 line, PRInt32 markerNum)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->DeleteMark(line, markerNum);
    return NS_OK;
}

/* void DeleteMarkFromHandle (in PRInt32 markerHandle); */
NS_IMETHODIMP SciDoc::DeleteMarkFromHandle(PRInt32 markerHandle)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->DeleteMarkFromHandle(markerHandle);
    return NS_OK;
}

/* void DeleteAllMarks (in PRInt32 markerNum); */
NS_IMETHODIMP SciDoc::DeleteAllMarks(PRInt32 markerNum)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->DeleteAllMarks(markerNum);
    return NS_OK;
}

/* PRInt32 LineFromHandle (in PRInt32 markerHandle); */
NS_IMETHODIMP SciDoc::LineFromHandle(PRInt32 markerHandle, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->LineFromHandle(markerHandle);
    return NS_OK;
}

/* PRInt32 LineStart (in PRInt32 line); */
NS_IMETHODIMP SciDoc::LineStart(PRInt32 line, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->LineStart(line);
    return NS_OK;
}

/* PRInt32 LineEnd (in PRInt32 line); */
NS_IMETHODIMP SciDoc::LineEnd(PRInt32 line, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->LineEnd(line);
    return NS_OK;
}

/* PRInt32 LineEndPosition (in PRInt32 position); */
NS_IMETHODIMP SciDoc::LineEndPosition(PRInt32 position, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->LineEndPosition(position);
    return NS_OK;
}

/* PRInt32 VCHomePosition (in PRInt32 position); */
NS_IMETHODIMP SciDoc::VCHomePosition(PRInt32 position, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->VCHomePosition(position);
    return NS_OK;
}

/* PRInt32 SetLevel (in PRInt32 line, in PRInt32 level); */
NS_IMETHODIMP SciDoc::SetLevel(PRInt32 line, PRInt32 level, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->SetLevel(line, level);
    return NS_OK;
}

/* PRInt32 GetLevel (in PRInt32 line); */
NS_IMETHODIMP SciDoc::GetLevel(PRInt32 line, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->GetLevel(line);
    return NS_OK;
}

/* void ClearLevels (); */
NS_IMETHODIMP SciDoc::ClearLevels()
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->ClearLevels();
    return NS_OK;
}

/* PRInt32 GetLastChild (in PRInt32 lineParent, in PRInt32 level); */
NS_IMETHODIMP SciDoc::GetLastChild(PRInt32 lineParent, PRInt32 level, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->GetLastChild(lineParent, level);
    return NS_OK;
}

/* PRInt32 GetFoldParent (in PRInt32 line); */
NS_IMETHODIMP SciDoc::GetFoldParent(PRInt32 line, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->GetFoldParent(line);
    return NS_OK;
}

/* PRInt32 ExtendWordSelect (in PRInt32 pos, in PRInt32 delta, in boolean onlyWordCharacters); */
NS_IMETHODIMP SciDoc::ExtendWordSelect(PRInt32 pos, PRInt32 delta, PRBool onlyWordCharacters, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->ExtendWordSelect(pos, delta, onlyWordCharacters);
    return NS_OK;
}

/* PRInt32 NextWordStart (in PRInt32 pos, in PRInt32 delta); */
NS_IMETHODIMP SciDoc::NextWordStart(PRInt32 pos, PRInt32 delta, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->NextWordStart(pos, delta);
    return NS_OK;
}

/* PRInt32 NextWordEnd (in PRInt32 pos, in PRInt32 delta); */
NS_IMETHODIMP SciDoc::NextWordEnd(PRInt32 pos, PRInt32 delta, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->NextWordEnd(pos, delta);
    return NS_OK;
}

/* PRInt32 Length (); */
NS_IMETHODIMP SciDoc::Length(PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->Length();
    return NS_OK;
}

/* void Allocate (in PRInt32 newSize); */
NS_IMETHODIMP SciDoc::Allocate(PRInt32 newSize)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->Allocate(newSize);
    return NS_OK;
}

/* long FindText (in PRInt32 minPos, in PRInt32 maxPos, in wstring s, in boolean caseSensitive, in boolean word, in boolean wordStart, in boolean regExp, in boolean posix); */
NS_IMETHODIMP SciDoc::FindText(PRInt32 minPos, PRInt32 maxPos,
                               const PRUnichar *s, PRBool caseSensitive,
                               PRBool word, PRBool wordStart, PRBool regExp, 
                               PRBool posix, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    nsCAutoString text = NS_ConvertUTF16toUTF8(s);
    int length = text.Length();
    *_retval = documentPointer->FindText(minPos, maxPos, reinterpret_cast<const char *>(text.get()),
                                         caseSensitive, word, wordStart, regExp, posix, &length);
    return NS_OK;
}

/* wstring SubstituteByPosition (in wstring text); */
NS_IMETHODIMP SciDoc::SubstituteByPosition(const PRUnichar *s, PRUnichar **_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    nsCAutoString text = NS_ConvertUTF16toUTF8(s);
    int length = text.Length();
    const char *buffer = documentPointer->SubstituteByPosition(reinterpret_cast<const char *>(text.get()), &length);
    if (documentPointer->dbcsCodePage == 0) {
        *_retval =  ToNewUnicode(NS_ConvertASCIItoUTF16(buffer));
    } else {
        *_retval =  ToNewUnicode(NS_ConvertUTF8toUTF16(buffer));
    }
    return NS_OK;
}

/* PRInt32 LinesTotal (); */
NS_IMETHODIMP SciDoc::LinesTotal(PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->LinesTotal();
    return NS_OK;
}

/* void ChangeCase (in PRInt32 start, in PRInt32 end, in boolean makeUpperCase); */
NS_IMETHODIMP SciDoc::ChangeCase(PRInt32 start, PRInt32 end, PRBool makeUpperCase)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->ChangeCase(Range(start, end), makeUpperCase);
    return NS_OK;
}

/* void SetDefaultCharClasses (in boolean includeWordClass); */
NS_IMETHODIMP SciDoc::SetDefaultCharClasses(PRBool includeWordClass)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->SetDefaultCharClasses(includeWordClass);
    return NS_OK;
}

/* void StartStyling (in PRInt32 position, in wchar mask); */
NS_IMETHODIMP SciDoc::StartStyling(PRInt32 position, PRUnichar mask)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->StartStyling(position, mask);
    return NS_OK;
}

/* boolean SetStyleFor (in PRInt32 length, in wchar style); */
NS_IMETHODIMP SciDoc::SetStyleFor(PRInt32 length, PRUnichar style, PRBool *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->SetStyleFor(length, style);
    return NS_OK;
}

/* boolean SetStyles (in PRInt32 length, in wstring styles); */
NS_IMETHODIMP SciDoc::SetStyles(PRInt32 length, const char *styles, PRBool *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    char *buffer = new char[length + 1];
    if (!buffer)
            return NS_ERROR_OUT_OF_MEMORY;
    buffer[length]=0;
    memcpy(buffer, styles, length);
    *_retval = documentPointer->SetStyles(length, buffer);
    delete buffer;
    return NS_OK;
}

/* PRInt32 GetEndStyled (); */
NS_IMETHODIMP SciDoc::GetEndStyled(PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->GetEndStyled();
    return NS_OK;
}

/* void EnsureStyledTo (in PRInt32 pos); */
NS_IMETHODIMP SciDoc::EnsureStyledTo(PRInt32 pos)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->EnsureStyledTo(pos);
    return NS_OK;
}

/* PRInt32 GetStyleClock (); */
NS_IMETHODIMP SciDoc::GetStyleClock(PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->GetStyleClock();
    return NS_OK;
}

/* void IncrementStyleClock (); */
NS_IMETHODIMP SciDoc::IncrementStyleClock()
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->IncrementStyleClock();
    return NS_OK;
}

/* void DecorationFillRange (in PRInt32 position, in PRInt32 value, in PRInt32 fillLength); */
NS_IMETHODIMP SciDoc::DecorationFillRange(PRInt32 position, PRInt32 value, PRInt32 fillLength)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    documentPointer->DecorationFillRange(position, value, fillLength);
    return NS_OK;
}

/* PRInt32 SetLineState (in PRInt32 line, in PRInt32 state); */
NS_IMETHODIMP SciDoc::SetLineState(PRInt32 line, PRInt32 state, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->SetLineState(line, state);
    return NS_OK;
}

/* PRInt32 GetLineState (in PRInt32 line); */
NS_IMETHODIMP SciDoc::GetLineState(PRInt32 line, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->GetLineState(line);
    return NS_OK;
}

/* PRInt32 GetMaxLineState (); */
NS_IMETHODIMP SciDoc::GetMaxLineState(PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->GetMaxLineState();
    return NS_OK;
}

/* boolean IsWordPartSeparator (in wchar ch); */
NS_IMETHODIMP SciDoc::IsWordPartSeparator(PRUnichar ch, PRBool *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->IsWordPartSeparator(ch);
    return NS_OK;
}

/* PRInt32 WordPartLeft (in PRInt32 pos); */
NS_IMETHODIMP SciDoc::WordPartLeft(PRInt32 pos, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->WordPartLeft(pos);
    return NS_OK;
}

/* PRInt32 WordPartRight (in PRInt32 pos); */
NS_IMETHODIMP SciDoc::WordPartRight(PRInt32 pos, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->WordPartRight(pos);
    return NS_OK;
}

/* PRInt32 ExtendStyleRange (in PRInt32 pos, in PRInt32 delta, in boolean singleLine); */
NS_IMETHODIMP SciDoc::ExtendStyleRange(PRInt32 pos, PRInt32 delta, PRBool singleLine, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->ExtendStyleRange(pos, delta, singleLine);
    return NS_OK;
}

/* boolean IsWhiteLine (in PRInt32 line); */
NS_IMETHODIMP SciDoc::IsWhiteLine(PRInt32 line, PRBool *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->WordPartRight(line);
    return NS_OK;
}

/* PRInt32 ParaUp (in PRInt32 pos); */
NS_IMETHODIMP SciDoc::ParaUp(PRInt32 pos, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->ParaUp(pos);
    return NS_OK;
}

/* PRInt32 ParaDown (in PRInt32 pos); */
NS_IMETHODIMP SciDoc::ParaDown(PRInt32 pos, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->ParaDown(pos);
    return NS_OK;
}

/* PRInt32 IndentSize (); */
NS_IMETHODIMP SciDoc::IndentSize(PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->IndentSize();
    return NS_OK;
}

/* PRInt32 BraceMatch (in PRInt32 position, in PRInt32 maxReStyle); */
NS_IMETHODIMP SciDoc::BraceMatch(PRInt32 position, PRInt32 maxReStyle, PRInt32 *_retval)
{
    if (documentPointer==nsnull) return NS_ERROR_UNEXPECTED;
    *_retval = documentPointer->BraceMatch(position, maxReStyle);
    return NS_OK;
}




// {1d79ca08-3f1b-4e6c-b00d-39fdf36475a9}
#define SCIDOC_CID \
{ 0x1d79ca08, 0x3f1b, 0x4e6c, { 0xb0, 0x0d, 0x39, 0xfd, 0xf3, 0x64, 0x75, 0xa9 } }
#define SCIDOC_CONTRACTID "@activestate.com/ISciDoc;1"

NS_GENERIC_FACTORY_CONSTRUCTOR(SciDoc)

static nsModuleComponentInfo components[] =
{
  { 
    "Scintilla Document",
    SCIDOC_CID,
    SCIDOC_CONTRACTID,
    SciDocConstructor,
    NULL, // RegistrationProc /* NULL if you dont need one */,
    NULL // UnregistrationProc /* NULL if you dont need one */
  }
};

NS_IMPL_NSGETMODULE("SciDoc", components)
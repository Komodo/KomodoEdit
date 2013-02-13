// Copyright 2002 by Brian Quinlan <brian@sweetapp.com>
// The License.txt file describes the conditions under which this 
// software may be distributed.

#include "SC_PropSet.h"
#include "LineVector.h"
#include "LexState.h"

class BufferAccessor : public IDocument {
	// Private so DocumentAccessor objects can not be copied
	BufferAccessor(const BufferAccessor &source) : props(source.props) {}
	BufferAccessor &operator=(const BufferAccessor &) { return *this; }

protected:
    // From Document.h
	SC_PropSet &props;
    LineVector lv;
	int bufLen;
    const char * charBuf;
    char * styleBuf;

    // From Document.h, parts not done by Accessors
	int codePage;
	char stylingMask;
	int endStyled;

public:
    BufferAccessor(const char * charBuf_,
                   int bufLen_,
                   char * styleBuf,
                   SC_PropSet &props_);
	~BufferAccessor();

	int dbcsCodePage;
	int tabInChars;
	//LexState *pli; // pointer to LexInterface in core scintilla.
                   // Here LexState swallowed LexInterface

    int GetColumn(int position);
    int GetLine(int position);
    bool InGoodUTF8(int pos, int &start, int &end) const;
    bool InternalIsLeadByte(char ch);
    int NextPosition(int pos, int moveDir) const;
	int GetPropertyInt(const char *key, int defaultValue=0) { 
		return props.GetInt(key, defaultValue); 
	}
	char *GetProperties() {
		return props.ToString();
	}

	int IndentAmount(int line, int *flags);

    // And declare all the methods inherited from IDocument
	int SCI_METHOD Version() const;
	void SCI_METHOD SetErrorStatus(int status);
	int SCI_METHOD LineFromPosition(int pos) const;
	int SCI_METHOD CodePage() const;
	bool SCI_METHOD IsDBCSLeadByte(char ch) const;
	const char * SCI_METHOD BufferPointer();
	int SCI_METHOD GetLineIndentation(int line);
	void SCI_METHOD GetCharRange(char *buffer, int position, int lengthRetrieve) const;
	char SCI_METHOD StyleAt(int position) const;
	int SCI_METHOD LineStart(int line) const;
	int SCI_METHOD SetLevel(int line, int level);
	int SCI_METHOD GetLevel(int line) const;
	int SCI_METHOD Length() const;
	void SCI_METHOD StartStyling(int position, char mask);
	bool SCI_METHOD SetStyleFor(int length, char style);
	bool SCI_METHOD SetStyles(int length, const char *styles);
	void SCI_METHOD DecorationSetCurrentIndicator(int indicator);
	void SCI_METHOD DecorationFillRange(int position, int value, int fillLength);
	int SCI_METHOD SetLineState(int line, int state);
	int SCI_METHOD SetLineStateNoNotify(int line, int state);
	int SCI_METHOD GetLineState(int line) const;
	void SCI_METHOD ChangeLexerState(int start, int end);
};


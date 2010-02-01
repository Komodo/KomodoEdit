// Copyright 2002 by Brian Quinlan <brian@sweetapp.com>
// The License.txt file describes the conditions under which this 
// software may be distributed.

#include "LineVector.h"

class BufferAccessor : public Accessor {
	// Private so DocumentAccessor objects can not be copied
	BufferAccessor(const BufferAccessor &source) : Accessor(), props(source.props) {}
	BufferAccessor &operator=(const BufferAccessor &) { return *this; }

protected:
    // From Document.h
	char stylingMask;
	int endStyled;

	SC_PropSet &props;
    LineVector lv;
	int bufLen;
    const char * charBuf;
	char * styleBuf;
	char chFlags;
	char chWhile;
	unsigned int startSeg;

	bool InternalIsLeadByte(char ch);
	void Fill(int position);

public:
    BufferAccessor(const char * charBuf_,
                   int bufLen_,
                   char * styleBuf,
                   SC_PropSet &props_);
	~BufferAccessor();

	bool Match(int pos, const char *s);
	char StyleAt(int position);
	int GetLine(int position);
    int GetColumn(int position);
	int LineStart(int line);
	int LevelAt(int line);
	int Length();
	void Flush();
	int GetLineState(int line);
	int SetLineState(int line, int state);
	int GetPropertyInt(const char *key, int defaultValue=0) { 
		return props.GetInt(key, defaultValue); 
	}
	char *GetProperties() {
		return props.ToString();
	}

	void StartAt(unsigned int start, char chMask=31);
	void SetFlags(char chFlags_, char chWhile_) {chFlags = chFlags_; chWhile = chWhile_; };
	unsigned int GetStartSegment() { return startSeg; }
	void StartSegment(unsigned int pos);
	void ColourTo(unsigned int pos, int chAttr);
	void SetLevel(int line, int level);
	int IndentAmount(int line, int *flags, PFNIsCommentLeader pfnIsCommentLeader = 0);
	void IndicatorFill(int start, int end, int indicator, int value) {};
};


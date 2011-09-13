// Copyright 2002 by Brian Quinlan <brian@sweetapp.com>
// The License.txt file describes the conditions under which this 
// software may be distributed.

#include <Scintilla.h>

class LineData
{
public:
    int startPosition;
    int lineState;
    int level;

    LineData(   int startPosition_ = -1, 
                int lineState_ = 0, 
                int level_ = SC_FOLDLEVELBASE)
        :   startPosition(startPosition_), 
            lineState(lineState_),
            level(level_) {}
};

class LineVector {
protected:
  	enum { growSize = 4000 };
	LineData *linesData;
	int numLines;
    int size;

    void Init(void);
    void Expand(int sizeNew);
    void ExpandFor(int sizeNew);

public:
	LineVector();
	~LineVector();

    void Append(const LineData & lineData);
    LineData& operator[](int pos) const;

    int GetNumLines() const { return numLines; };
};

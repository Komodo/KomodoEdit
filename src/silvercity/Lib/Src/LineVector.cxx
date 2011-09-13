// Copyright 2002 by Brian Quinlan <brian@sweetapp.com>
// The License.txt file describes the conditions under which this 
// software may be distributed.

#include "LineVector.h"

#include "Platform.h"

LineVector::LineVector() {
	linesData = 0;
	numLines = 0;
	size = 0;

	Init();
}

LineVector::~LineVector() {
	delete []linesData;
}

void LineVector::Init(void) {
	delete []linesData;
	linesData = new LineData[static_cast<int>(growSize)];
	size = growSize;
	numLines = 0;
}

void LineVector::Expand(int sizeNew) {
	LineData *linesDataNew = new LineData[sizeNew];
	if (linesDataNew) {
        // XXX Why are we copying unused lines?
		for (int i = 0; i < size; i++)
			linesDataNew[i] = linesData[i];

        delete []linesData;
		linesData = linesDataNew;
		size = sizeNew;
	} else {
		Platform::DebugPrintf("No memory available\n");
		// TODO: Blow up
	}
}

void LineVector::ExpandFor(int sizeNew)
{
    if (sizeNew < size)
        return;
    
    Expand(sizeNew + growSize);
}

void LineVector::Append(const LineData & lineData)
{
    ExpandFor(numLines + 1);
    linesData[numLines] = lineData;
    ++numLines;
}

LineData& LineVector::operator[](int pos) const
{
    PLATFORM_ASSERT(pos < numLines);
    PLATFORM_ASSERT(pos >= 0);
    return linesData[pos];
}

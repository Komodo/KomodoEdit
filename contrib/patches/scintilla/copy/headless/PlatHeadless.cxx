// Scintilla source code edit control
// PlatGTK.cxx - implementation of platform facilities on GTK+/Linux
// Copyright 1998-2004 by Neil Hodgson <neilh@scintilla.org>
// The License.txt file describes the conditions under which this software may be distributed.

#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <math.h>

#ifdef MACOSX
#include <sys/time.h>
#endif

#include <vector>
#include <map>

#include "Platform.h"

#include "Scintilla.h"
#include "ScintillaHeadless.h"
#include "UniConversion.h"
#include "XPM.h"

#ifdef SCI_NAMESPACE
using namespace Scintilla;
#endif

Font::Font() : fid(0) {}

Font::~Font() {}

void Font::Create(const FontParameters &fp) {
}

void Font::Release() {
	fid = 0;
}


// Required on OS X
#ifdef SCI_NAMESPACE
namespace Scintilla {
#endif

// SurfaceID is a cairo_t*
class SurfaceImpl : public Surface {
	int et;
	void *context;
	void *psurf;
	int x;
	int y;
	bool inited;
	bool createdGC;
	void *pcontext;
	void *layout;
	int characterSet;
public:
	SurfaceImpl();
	virtual ~SurfaceImpl();

	void Init(WindowID wid);
	void Init(SurfaceID sid, WindowID wid);
	void InitPixMap(int width, int height, Surface *surface_, WindowID wid);

	void Release();
	bool Initialised();
	void PenColour(ColourDesired fore);
	int LogPixelsY();
	int DeviceHeightFont(int points);
	void MoveTo(int x_, int y_);
	void LineTo(int x_, int y_);
	void Polygon(Point *pts, int npts, ColourDesired fore, ColourDesired back);
	void RectangleDraw(PRectangle rc, ColourDesired fore, ColourDesired back);
	void FillRectangle(PRectangle rc, ColourDesired back);
	void FillRectangle(PRectangle rc, Surface &surfacePattern);
	void RoundedRectangle(PRectangle rc, ColourDesired fore, ColourDesired back);
	void AlphaRectangle(PRectangle rc, int cornerSize, ColourDesired fill, int alphaFill,
		ColourDesired outline, int alphaOutline, int flags);
	void DrawRGBAImage(PRectangle rc, int width, int height, const unsigned char *pixelsImage);
	void Ellipse(PRectangle rc, ColourDesired fore, ColourDesired back);
	void Copy(PRectangle rc, Point from, Surface &surfaceSource);

	void DrawTextBase(PRectangle rc, Font &font_, XYPOSITION ybase, const char *s, int len, ColourDesired fore);
	void DrawTextNoClip(PRectangle rc, Font &font_, XYPOSITION ybase, const char *s, int len, ColourDesired fore, ColourDesired back);
	void DrawTextClipped(PRectangle rc, Font &font_, XYPOSITION ybase, const char *s, int len, ColourDesired fore, ColourDesired back);
	void DrawTextTransparent(PRectangle rc, Font &font_, XYPOSITION ybase, const char *s, int len, ColourDesired fore);
	void MeasureWidths(Font &font_, const char *s, int len, XYPOSITION *positions);
	XYPOSITION WidthText(Font &font_, const char *s, int len);
	XYPOSITION WidthChar(Font &font_, char ch);
	XYPOSITION Ascent(Font &font_);
	XYPOSITION Descent(Font &font_);
	XYPOSITION InternalLeading(Font &font_);
	XYPOSITION ExternalLeading(Font &font_);
	XYPOSITION Height(Font &font_);
	XYPOSITION AverageCharWidth(Font &font_);

	void SetClip(PRectangle rc);
	void FlushCachedState();

	void SetUnicodeMode(bool unicodeMode_);
	void SetDBCSMode(int codePage);
};
#ifdef SCI_NAMESPACE
}
#endif

SurfaceImpl::SurfaceImpl() : et(0),
context(0),
psurf(0),
x(0), y(0), inited(false), createdGC(false)
, pcontext(0), layout(0), characterSet(-1) {
}

SurfaceImpl::~SurfaceImpl() {
	Release();
}

void SurfaceImpl::Release() {
	x = 0;
	y = 0;
	inited = false;
}

bool SurfaceImpl::Initialised() {
	return inited;
}

void SurfaceImpl::Init(WindowID wid) {
	Release();
	PLATFORM_ASSERT(wid);
	inited = true;
}

void SurfaceImpl::Init(SurfaceID sid, WindowID wid) {
	PLATFORM_ASSERT(sid);
	Release();
	inited = true;
}

void SurfaceImpl::InitPixMap(int width, int height, Surface *surface_, WindowID wid) {
	PLATFORM_ASSERT(surface_);
	Release();
	inited = true;
}

void SurfaceImpl::PenColour(ColourDesired fore) {
}

int SurfaceImpl::LogPixelsY() {
	return 72;
}

int SurfaceImpl::DeviceHeightFont(int points) {
	int logPix = LogPixelsY();
	return (points * logPix + logPix / 2) / 72;
}

void SurfaceImpl::MoveTo(int x_, int y_) {
	x = x_;
	y = y_;
}

void SurfaceImpl::LineTo(int x_, int y_) {
	x = x_;
	y = y_;
}

void SurfaceImpl::Polygon(Point *pts, int npts, ColourDesired fore,
                          ColourDesired back) {
}

void SurfaceImpl::RectangleDraw(PRectangle rc, ColourDesired fore, ColourDesired back) {
}

void SurfaceImpl::FillRectangle(PRectangle rc, ColourDesired back) {
}

void SurfaceImpl::FillRectangle(PRectangle rc, Surface &surfacePattern) {
}

void SurfaceImpl::RoundedRectangle(PRectangle rc, ColourDesired fore, ColourDesired back) {
}

void SurfaceImpl::AlphaRectangle(PRectangle rc, int cornerSize, ColourDesired fill, int alphaFill,
		ColourDesired outline, int alphaOutline, int flags) {
}

void SurfaceImpl::DrawRGBAImage(PRectangle rc, int width, int height, const unsigned char *pixelsImage) {
}

void SurfaceImpl::Ellipse(PRectangle rc, ColourDesired fore, ColourDesired back) {
}

void SurfaceImpl::Copy(PRectangle rc, Point from, Surface &surfaceSource) {
}

void SurfaceImpl::DrawTextBase(PRectangle rc, Font &font_, XYPOSITION ybase, const char *s, int len,
                                 ColourDesired fore) {
}

void SurfaceImpl::DrawTextNoClip(PRectangle rc, Font &font_, XYPOSITION ybase, const char *s, int len,
                                 ColourDesired fore, ColourDesired back) {
}

void SurfaceImpl::DrawTextClipped(PRectangle rc, Font &font_, XYPOSITION ybase, const char *s, int len,
                                  ColourDesired fore, ColourDesired back) {
}

void SurfaceImpl::DrawTextTransparent(PRectangle rc, Font &font_, XYPOSITION ybase, const char *s, int len,
                                  ColourDesired fore) {
}

void SurfaceImpl::MeasureWidths(Font &font_, const char *s, int len, XYPOSITION *positions) {
	// No font so return an ascending range of values
	for (int i = 0; i < len; i++) {
		positions[i] = i + 1;
	}
}

#define HEADLESS_CHAR_WIDTH 8

XYPOSITION SurfaceImpl::WidthText(Font &font_, const char *s, int len) {
	return len * HEADLESS_CHAR_WIDTH;
}

XYPOSITION SurfaceImpl::WidthChar(Font &font_, char ch) {
	return HEADLESS_CHAR_WIDTH;
}

// Ascent and descent determined by Pango font metrics.

XYPOSITION SurfaceImpl::Ascent(Font &font_) {
	return 1;
}

XYPOSITION SurfaceImpl::Descent(Font &font_) {
	return 1;
}

XYPOSITION SurfaceImpl::InternalLeading(Font &) {
	return 0;
}

XYPOSITION SurfaceImpl::ExternalLeading(Font &) {
	return 0;
}

XYPOSITION SurfaceImpl::Height(Font &font_) {
	return 12;
}

XYPOSITION SurfaceImpl::AverageCharWidth(Font &font_) {
	return HEADLESS_CHAR_WIDTH;
}

void SurfaceImpl::SetClip(PRectangle rc) {
}

void SurfaceImpl::FlushCachedState() {}

void SurfaceImpl::SetUnicodeMode(bool unicodeMode_) {
}

void SurfaceImpl::SetDBCSMode(int codePage) {
}

Surface *Surface::Allocate(int) {
	return new SurfaceImpl();
}

Window::~Window() {}

void Window::Destroy() {
	wid = 0;
}

bool Window::HasFocus() {
	return true;
}

PRectangle Window::GetPosition() {
	// Before any size allocated pretend its 1000 wide so not scrolled
	return PRectangle(0, 0, 1000, 1000);
}

void Window::SetPosition(PRectangle rc) {
}

void Window::SetPositionRelative(PRectangle rc, Window relativeTo) {
}

PRectangle Window::GetClientPosition() {
	return GetPosition();
}

void Window::Show(bool show) {
}

void Window::InvalidateAll() {
}

void Window::InvalidateRectangle(PRectangle rc) {
}

void Window::SetFont(Font &) {
}

void Window::SetCursor(Cursor curs) {
}

void Window::SetTitle(const char *s) {
}

PRectangle Window::GetMonitorRect(Point pt) {
	return PRectangle(0, 0, 1000, 1000);
}

typedef std::map<int, RGBAImage*> ImageMap;

ListBox::ListBox() {
}

ListBox::~ListBox() {
}

class ListBoxX : public ListBox {
	void *list;
	void *scroller;
	void *lb;
	void *pixhash;
	void *pixbuf_renderer;
	int desiredVisibleRows;
	unsigned int maxItemCharacters;
	unsigned int aveCharWidth;
public:
	CallBackAction doubleClickAction;
	void *doubleClickActionData;

	ListBoxX() : list(0), scroller(0), pixhash(NULL), pixbuf_renderer(0),
		desiredVisibleRows(5), maxItemCharacters(0),
		aveCharWidth(1), doubleClickAction(NULL), doubleClickActionData(NULL) {
	}
	virtual ~ListBoxX() {
	}
	virtual void SetFont(Font &font);
	virtual void Create(Window &parent, int ctrlID, Point location_, int lineHeight_, bool unicodeMode_, int technology_);
	virtual void SetAverageCharWidth(int width);
	virtual void SetVisibleRows(int rows);
	virtual int GetVisibleRows() const;
	virtual PRectangle GetDesiredRect();
	virtual int CaretFromEdge();
	virtual void Clear();
	virtual void Append(char *s, int type = -1);
	virtual int Length();
	virtual void Select(int n);
	virtual int GetSelection();
	virtual int Find(const char *prefix);
	virtual void GetValue(int n, char *value, int len);
	void RegisterRGBA(int type, RGBAImage *image);
	virtual void RegisterImage(int type, const char *xpm_data);
	virtual void RegisterRGBAImage(int type, int width, int height, const unsigned char *pixelsImage);
	virtual void ClearRegisteredImages();
	virtual void SetDoubleClickAction(CallBackAction action, void *data) {
		doubleClickAction = action;
		doubleClickActionData = data;
	}
	virtual void SetList(const char *listText, char separator, char typesep);
};

ListBox *ListBox::Allocate() {
	ListBoxX *lb = new ListBoxX();
	return lb;
}

void ListBoxX::Create(Window &, int, Point, int, bool, int) {
}

void ListBoxX::SetFont(Font &scint_font) {
}

void ListBoxX::SetAverageCharWidth(int width) {
	aveCharWidth = width;
}

void ListBoxX::SetVisibleRows(int rows) {
	desiredVisibleRows = rows;
}

int ListBoxX::GetVisibleRows() const {
	return desiredVisibleRows;
}

PRectangle ListBoxX::GetDesiredRect() {
	// Before any size allocated pretend its 100 wide so not scrolled
	return PRectangle(0, 0, 100, 100);
}

int ListBoxX::CaretFromEdge() {
	return 4;
}

void ListBoxX::Clear() {
	maxItemCharacters = 0;
}

void ListBoxX::Append(char *s, int type) {
}

int ListBoxX::Length() {
	return 0;
}

void ListBoxX::Select(int n) {
}

int ListBoxX::GetSelection() {
	return -1;
}

int ListBoxX::Find(const char *prefix) {
	return -1;
}

void ListBoxX::GetValue(int n, char *value, int len) {
	value[0] = '\0';
}

void ListBoxX::RegisterRGBA(int type, RGBAImage *image) {
}

void ListBoxX::RegisterImage(int type, const char *xpm_data) {
}

void ListBoxX::RegisterRGBAImage(int type, int width, int height, const unsigned char *pixelsImage) {
}

void ListBoxX::ClearRegisteredImages() {
}

void ListBoxX::SetList(const char *listText, char separator, char typesep) {
}

Menu::Menu() : mid(0) {}

void Menu::CreatePopUp() {
	Destroy();
}

void Menu::Destroy() {
	mid = 0;
}

void Menu::Show(Point pt, Window &) {
}


//----------------- ElapsedTime --------------------------------------------------------------------

#if defined(GTK)
#include <glib.h>
#include <gmodule.h>
#include <gdk/gdk.h>
#include <gtk/gtk.h>
#include <gdk/gdkkeysyms.h>
ElapsedTime::ElapsedTime() {
	GTimeVal curTime;
	g_get_current_time(&curTime);
	bigBit = curTime.tv_sec;
	littleBit = curTime.tv_usec;
}
double ElapsedTime::Duration(bool reset) {
	GTimeVal curTime;
	g_get_current_time(&curTime);
	long endBigBit = curTime.tv_sec;
	long endLittleBit = curTime.tv_usec;
	double result = 1000000.0 * (endBigBit - bigBit);
	result += endLittleBit - littleBit;
	result /= 1000000.0;
	if (reset) {
		bigBit = endBigBit;
		littleBit = endLittleBit;
	}
	return result;
}
#endif // end GTK

#if defined(MACOSX)
ElapsedTime::ElapsedTime() {
  struct timeval curTime;
  gettimeofday( &curTime, NULL );

  bigBit = curTime.tv_sec;
  littleBit = curTime.tv_usec;
}
double ElapsedTime::Duration(bool reset) {
  struct timeval curTime;
  gettimeofday( &curTime, NULL );
  long endBigBit = curTime.tv_sec;
  long endLittleBit = curTime.tv_usec;
  double result = 1000000.0 * (endBigBit - bigBit);
  result += endLittleBit - littleBit;
  result /= 1000000.0;
  if (reset) {
    bigBit = endBigBit;
    littleBit = endLittleBit;
  }
  return result;
}
#endif // end MACOSX


//----------------- DynamicLibrary -----------------------------------------------------------------

#if defined(_WIN32)
#include <windows.h>
#include <commctrl.h>
#include <richedit.h>
#include <windowsx.h>
class DynamicLibraryImpl : public DynamicLibrary {
protected:
	HMODULE h;
public:
	DynamicLibraryImpl(const char *modulePath) {
		h = ::LoadLibraryA(modulePath);
	}
	virtual ~DynamicLibraryImpl() {
		if (h != NULL)
			::FreeLibrary(h);
	}
	// Use GetProcAddress to get a pointer to the relevant function.
	virtual Function FindFunction(const char *name) {
		if (h != NULL) {
			// C++ standard doesn't like casts betwen function pointers and void pointers so use a union
			union {
				FARPROC fp;
				Function f;
			} fnConv;
			fnConv.fp = ::GetProcAddress(h, name);
			return fnConv.f;
		} else
			return NULL;
	}
	virtual bool IsValid() {
		return h != NULL;
	}
};
DynamicLibrary *DynamicLibrary::Load(const char *modulePath) {
	return static_cast<DynamicLibrary *>(new DynamicLibraryImpl(modulePath));
}
#endif

#if defined(GTK)
class DynamicLibraryImpl : public DynamicLibrary {
protected:
	GModule* m;
public:
	DynamicLibraryImpl(const char *modulePath) {
		m = g_module_open(modulePath, G_MODULE_BIND_LAZY);
	}
	virtual ~DynamicLibraryImpl() {
		if (m != NULL)
			g_module_close(m);
	}
	// Use g_module_symbol to get a pointer to the relevant function.
	virtual Function FindFunction(const char *name) {
		if (m != NULL) {
			gpointer fn_address = NULL;
			gboolean status = g_module_symbol(m, name, &fn_address);
			if (status)
				return static_cast<Function>(fn_address);
			else
				return NULL;
		} else
			return NULL;
	}
	virtual bool IsValid() {
		return m != NULL;
	}
};
DynamicLibrary *DynamicLibrary::Load(const char *modulePath) {
	return static_cast<DynamicLibrary *>( new DynamicLibraryImpl(modulePath) );
}
#endif // end GTK

#if defined(MACOSX)
DynamicLibrary* DynamicLibrary::Load(const char* /* modulePath */)
{
  // Not implemented.
  return NULL;
}
#endif // end MACOSX



ColourDesired Platform::Chrome() {
	return ColourDesired(0xe0, 0xe0, 0xe0);
}

ColourDesired Platform::ChromeHighlight() {
	return ColourDesired(0xff, 0xff, 0xff);
}

const char *Platform::DefaultFont() {
#ifdef G_OS_WIN32
	return "Lucida Console";
#else
#ifdef MACOSX
	return "Monaco";
#endif
	return "!Sans";
#endif
}

int Platform::DefaultFontSize() {
	return 12;
}

unsigned int Platform::DoubleClickTime() {
	return 500; 	// Half a second
}

bool Platform::MouseButtonBounce() {
	return true;
}

void Platform::DebugDisplay(const char *s) {
	fprintf(stderr, "%s", s);
}

bool Platform::IsKeyDown(int) {
	// TODO: discover state of keys in GTK+/X
	return false;
}

long Platform::SendScintilla(WindowID w, unsigned int msg, unsigned long wParam, long lParam) {
	return scintilla_send_message(w, msg, wParam, lParam);
}

long Platform::SendScintillaPointer(WindowID w, unsigned int msg, unsigned long wParam, void *lParam) {
	return scintilla_send_message(w, msg, wParam, reinterpret_cast<sptr_t>(lParam));
}

bool Platform::IsDBCSLeadByte(int codePage, char ch) {
	// Byte ranges found in Wikipedia articles with relevant search strings in each case
	unsigned char uch = static_cast<unsigned char>(ch);
	switch (codePage) {
		case 932:
			// Shift_jis
			return ((uch >= 0x81) && (uch <= 0x9F)) ||
				((uch >= 0xE0) && (uch <= 0xFC));
				// Lead bytes F0 to FC may be a Microsoft addition.
		case 936:
			// GBK
			return (uch >= 0x81) && (uch <= 0xFE);
		case 950:
			// Big5
			return (uch >= 0x81) && (uch <= 0xFE);
		// Korean EUC-KR may be code page 949.
	}
	return false;
}

int Platform::DBCSCharLength(int codePage, const char *s) {
	if (codePage == 932 || codePage == 936 || codePage == 950) {
		return IsDBCSLeadByte(codePage, s[0]) ? 2 : 1;
	} else {
		int bytes = mblen(s, MB_CUR_MAX);
		if (bytes >= 1)
			return bytes;
		else
			return 1;
	}
}

int Platform::DBCSCharMaxLength() {
	return MB_CUR_MAX;
	//return 2;
}

// These are utility functions not really tied to a platform

int Platform::Minimum(int a, int b) {
	if (a < b)
		return a;
	else
		return b;
}

int Platform::Maximum(int a, int b) {
	if (a > b)
		return a;
	else
		return b;
}

//#define TRACE

#ifdef TRACE
void Platform::DebugPrintf(const char *format, ...) {
	char buffer[2000];
	va_list pArguments;
	va_start(pArguments, format);
	vsprintf(buffer, format, pArguments);
	va_end(pArguments);
	Platform::DebugDisplay(buffer);
}
#else
void Platform::DebugPrintf(const char *, ...) {}

#endif

// Not supported for GTK+
static bool assertionPopUps = true;

bool Platform::ShowAssertionPopUps(bool assertionPopUps_) {
	bool ret = assertionPopUps;
	assertionPopUps = assertionPopUps_;
	return ret;
}

void Platform::Assert(const char *c, const char *file, int line) {
	char buffer[2000];
	sprintf(buffer, "Assertion [%s] failed at %s %d", c, file, line);
	strcat(buffer, "\r\n");
	Platform::DebugDisplay(buffer);
	abort();
}

int Platform::Clamp(int val, int minVal, int maxVal) {
	if (val > maxVal)
		val = maxVal;
	if (val < minVal)
		val = minVal;
	return val;
}

void Platform_Initialise() {
}

void Platform_Finalise() {
}

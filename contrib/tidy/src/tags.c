/* tags.c -- recognize HTML tags

  (c) 1998-2005 (W3C) MIT, ERCIM, Keio University
  See tidy.h for the copyright notice.

  CVS Info :

    $Author: arnaud02 $ 
    $Date: 2005/09/19 16:23:39 $ 
    $Revision: 1.58 $ 

  The HTML tags are stored as 8 bit ASCII strings.

*/

#include "tags.h"
#include "tidy-int.h"
#include "message.h"
#include "tmbstr.h"

#define VERS_ELEM_A          (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_ABBR       (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_ACRONYM    (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_ADDRESS    (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_APPLET     (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|xxxx|xxxx|xxxx|xxxx|xxxx)
#define VERS_ELEM_AREA       (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_B          (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_BASE       (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_BASEFONT   (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|xxxx|xxxx|xxxx|xxxx|xxxx)
#define VERS_ELEM_BDO        (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_BIG        (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_BLOCKQUOTE (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_BODY       (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_BR         (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_BUTTON     (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_CAPTION    (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_CENTER     (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|xxxx|xxxx|xxxx|xxxx|xxxx)
#define VERS_ELEM_CITE       (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_CODE       (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_COL        (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_COLGROUP   (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_DD         (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_DEL        (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_DFN        (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_DIR        (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|xxxx|xxxx|xxxx|xxxx|xxxx)
#define VERS_ELEM_DIV        (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_DL         (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_DT         (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_EM         (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_FIELDSET   (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_FONT       (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|xxxx|xxxx|xxxx|xxxx|xxxx)
#define VERS_ELEM_FORM       (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_FRAME      (xxxx|xxxx|xxxx|xxxx|xxxx|H40F|H41F|X10F|xxxx|xxxx|xxxx|xxxx|xxxx)
#define VERS_ELEM_FRAMESET   (xxxx|xxxx|xxxx|xxxx|xxxx|H40F|H41F|X10F|xxxx|xxxx|xxxx|xxxx|xxxx)
#define VERS_ELEM_H1         (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_H2         (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_H3         (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_H4         (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_H5         (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_H6         (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_HEAD       (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_HR         (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_HTML       (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_I          (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_IFRAME     (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|xxxx|xxxx|xxxx|xxxx|xxxx)
#define VERS_ELEM_IMG        (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_INPUT      (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_INS        (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_ISINDEX    (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|xxxx|xxxx|xxxx|xxxx|xxxx)
#define VERS_ELEM_KBD        (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_LABEL      (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_LEGEND     (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_LI         (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_LINK       (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_LISTING    (HT20|HT32|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx)
#define VERS_ELEM_MAP        (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_MENU       (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|xxxx|xxxx|xxxx|xxxx|xxxx)
#define VERS_ELEM_META       (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_NEXTID     (HT20|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx)
#define VERS_ELEM_NOFRAMES   (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|xxxx|xxxx|xxxx|xxxx|xxxx)
#define VERS_ELEM_NOSCRIPT   (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_OBJECT     (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_OL         (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_OPTGROUP   (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_OPTION     (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_P          (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_PARAM      (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_PLAINTEXT  (HT20|HT32|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx)
#define VERS_ELEM_PRE        (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_Q          (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_RB         (xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|XH11|xxxx)
#define VERS_ELEM_RBC        (xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|XH11|xxxx)
#define VERS_ELEM_RP         (xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|XH11|xxxx)
#define VERS_ELEM_RT         (xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|XH11|xxxx)
#define VERS_ELEM_RTC        (xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|XH11|xxxx)
#define VERS_ELEM_RUBY       (xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|XH11|xxxx)
#define VERS_ELEM_S          (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|xxxx|xxxx|xxxx|xxxx|xxxx)
#define VERS_ELEM_SAMP       (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_SCRIPT     (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_SELECT     (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_SMALL      (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_SPAN       (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_STRIKE     (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|xxxx|xxxx|xxxx|xxxx|xxxx)
#define VERS_ELEM_STRONG     (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_STYLE      (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_SUB        (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_SUP        (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_TABLE      (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_TBODY      (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_TD         (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_TEXTAREA   (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_TFOOT      (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_TH         (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_THEAD      (xxxx|xxxx|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_TITLE      (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_TR         (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_TT         (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|xxxx)
#define VERS_ELEM_U          (xxxx|HT32|H40T|H41T|X10T|H40F|H41F|X10F|xxxx|xxxx|xxxx|xxxx|xxxx)
#define VERS_ELEM_UL         (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_VAR        (HT20|HT32|H40T|H41T|X10T|H40F|H41F|X10F|H40S|H41S|X10S|XH11|XB10)
#define VERS_ELEM_XMP        (HT20|HT32|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx|xxxx)

static const Dict tag_defs[] =
{
  { TidyTag_UNKNOWN,    "unknown!",   VERS_UNKNOWN,         NULL,                       (0),                                           NULL,          NULL           },

  /* W3C defined elements */
  { TidyTag_A,          "a",          VERS_ELEM_A,          &W3CAttrsFor_A[0],          (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_ABBR,       "abbr",       VERS_ELEM_ABBR,       &W3CAttrsFor_ABBR[0],       (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_ACRONYM,    "acronym",    VERS_ELEM_ACRONYM,    &W3CAttrsFor_ACRONYM[0],    (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_ADDRESS,    "address",    VERS_ELEM_ADDRESS,    &W3CAttrsFor_ADDRESS[0],    (CM_BLOCK),                                    ParseInline,   NULL           },
  { TidyTag_APPLET,     "applet",     VERS_ELEM_APPLET,     &W3CAttrsFor_APPLET[0],     (CM_OBJECT|CM_IMG|CM_INLINE|CM_PARAM),         ParseBlock,    NULL           },
  { TidyTag_AREA,       "area",       VERS_ELEM_AREA,       &W3CAttrsFor_AREA[0],       (CM_BLOCK|CM_EMPTY),                           ParseEmpty,    CheckAREA      },
  { TidyTag_B,          "b",          VERS_ELEM_B,          &W3CAttrsFor_B[0],          (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_BASE,       "base",       VERS_ELEM_BASE,       &W3CAttrsFor_BASE[0],       (CM_HEAD|CM_EMPTY),                            ParseEmpty,    NULL           },
  { TidyTag_BASEFONT,   "basefont",   VERS_ELEM_BASEFONT,   &W3CAttrsFor_BASEFONT[0],   (CM_INLINE|CM_EMPTY),                          ParseEmpty,    NULL           },
  { TidyTag_BDO,        "bdo",        VERS_ELEM_BDO,        &W3CAttrsFor_BDO[0],        (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_BIG,        "big",        VERS_ELEM_BIG,        &W3CAttrsFor_BIG[0],        (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_BLOCKQUOTE, "blockquote", VERS_ELEM_BLOCKQUOTE, &W3CAttrsFor_BLOCKQUOTE[0], (CM_BLOCK),                                    ParseBlock,    NULL           },
  { TidyTag_BODY,       "body",       VERS_ELEM_BODY,       &W3CAttrsFor_BODY[0],       (CM_HTML|CM_OPT|CM_OMITST),                    ParseBody,     NULL           },
  { TidyTag_BR,         "br",         VERS_ELEM_BR,         &W3CAttrsFor_BR[0],         (CM_INLINE|CM_EMPTY),                          ParseEmpty,    NULL           },
  { TidyTag_BUTTON,     "button",     VERS_ELEM_BUTTON,     &W3CAttrsFor_BUTTON[0],     (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_CAPTION,    "caption",    VERS_ELEM_CAPTION,    &W3CAttrsFor_CAPTION[0],    (CM_TABLE),                                    ParseInline,   CheckCaption   },
  { TidyTag_CENTER,     "center",     VERS_ELEM_CENTER,     &W3CAttrsFor_CENTER[0],     (CM_BLOCK),                                    ParseBlock,    NULL           },
  { TidyTag_CITE,       "cite",       VERS_ELEM_CITE,       &W3CAttrsFor_CITE[0],       (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_CODE,       "code",       VERS_ELEM_CODE,       &W3CAttrsFor_CODE[0],       (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_COL,        "col",        VERS_ELEM_COL,        &W3CAttrsFor_COL[0],        (CM_TABLE|CM_EMPTY),                           ParseEmpty,    NULL           },
  { TidyTag_COLGROUP,   "colgroup",   VERS_ELEM_COLGROUP,   &W3CAttrsFor_COLGROUP[0],   (CM_TABLE|CM_OPT),                             ParseColGroup, NULL           },
  { TidyTag_DD,         "dd",         VERS_ELEM_DD,         &W3CAttrsFor_DD[0],         (CM_DEFLIST|CM_OPT|CM_NO_INDENT),              ParseBlock,    NULL           },
  { TidyTag_DEL,        "del",        VERS_ELEM_DEL,        &W3CAttrsFor_DEL[0],        (CM_INLINE|CM_BLOCK|CM_MIXED),                 ParseInline,   NULL           },
  { TidyTag_DFN,        "dfn",        VERS_ELEM_DFN,        &W3CAttrsFor_DFN[0],        (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_DIR,        "dir",        VERS_ELEM_DIR,        &W3CAttrsFor_DIR[0],        (CM_BLOCK|CM_OBSOLETE),                        ParseList,     NULL           },
  { TidyTag_DIV,        "div",        VERS_ELEM_DIV,        &W3CAttrsFor_DIV[0],        (CM_BLOCK),                                    ParseBlock,    NULL           },
  { TidyTag_DL,         "dl",         VERS_ELEM_DL,         &W3CAttrsFor_DL[0],         (CM_BLOCK),                                    ParseDefList,  NULL           },
  { TidyTag_DT,         "dt",         VERS_ELEM_DT,         &W3CAttrsFor_DT[0],         (CM_DEFLIST|CM_OPT|CM_NO_INDENT),              ParseInline,   NULL           },
  { TidyTag_EM,         "em",         VERS_ELEM_EM,         &W3CAttrsFor_EM[0],         (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_FIELDSET,   "fieldset",   VERS_ELEM_FIELDSET,   &W3CAttrsFor_FIELDSET[0],   (CM_BLOCK),                                    ParseBlock,    NULL           },
  { TidyTag_FONT,       "font",       VERS_ELEM_FONT,       &W3CAttrsFor_FONT[0],       (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_FORM,       "form",       VERS_ELEM_FORM,       &W3CAttrsFor_FORM[0],       (CM_BLOCK),                                    ParseBlock,    CheckFORM      },
  { TidyTag_FRAME,      "frame",      VERS_ELEM_FRAME,      &W3CAttrsFor_FRAME[0],      (CM_FRAMES|CM_EMPTY),                          ParseEmpty,    NULL           },
  { TidyTag_FRAMESET,   "frameset",   VERS_ELEM_FRAMESET,   &W3CAttrsFor_FRAMESET[0],   (CM_HTML|CM_FRAMES),                           ParseFrameSet, NULL           },
  { TidyTag_H1,         "h1",         VERS_ELEM_H1,         &W3CAttrsFor_H1[0],         (CM_BLOCK|CM_HEADING),                         ParseInline,   NULL           },
  { TidyTag_H2,         "h2",         VERS_ELEM_H2,         &W3CAttrsFor_H2[0],         (CM_BLOCK|CM_HEADING),                         ParseInline,   NULL           },
  { TidyTag_H3,         "h3",         VERS_ELEM_H3,         &W3CAttrsFor_H3[0],         (CM_BLOCK|CM_HEADING),                         ParseInline,   NULL           },
  { TidyTag_H4,         "h4",         VERS_ELEM_H4,         &W3CAttrsFor_H4[0],         (CM_BLOCK|CM_HEADING),                         ParseInline,   NULL           },
  { TidyTag_H5,         "h5",         VERS_ELEM_H5,         &W3CAttrsFor_H5[0],         (CM_BLOCK|CM_HEADING),                         ParseInline,   NULL           },
  { TidyTag_H6,         "h6",         VERS_ELEM_H6,         &W3CAttrsFor_H6[0],         (CM_BLOCK|CM_HEADING),                         ParseInline,   NULL           },
  { TidyTag_HEAD,       "head",       VERS_ELEM_HEAD,       &W3CAttrsFor_HEAD[0],       (CM_HTML|CM_OPT|CM_OMITST),                    ParseHead,     NULL           },
  { TidyTag_HR,         "hr",         VERS_ELEM_HR,         &W3CAttrsFor_HR[0],         (CM_BLOCK|CM_EMPTY),                           ParseEmpty,    NULL           },
  { TidyTag_HTML,       "html",       VERS_ELEM_HTML,       &W3CAttrsFor_HTML[0],       (CM_HTML|CM_OPT|CM_OMITST),                    ParseHTML,     CheckHTML      },
  { TidyTag_I,          "i",          VERS_ELEM_I,          &W3CAttrsFor_I[0],          (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_IFRAME,     "iframe",     VERS_ELEM_IFRAME,     &W3CAttrsFor_IFRAME[0],     (CM_INLINE),                                   ParseBlock,    NULL           },
  { TidyTag_IMG,        "img",        VERS_ELEM_IMG,        &W3CAttrsFor_IMG[0],        (CM_INLINE|CM_IMG|CM_EMPTY),                   ParseEmpty,    CheckIMG       },
  { TidyTag_INPUT,      "input",      VERS_ELEM_INPUT,      &W3CAttrsFor_INPUT[0],      (CM_INLINE|CM_IMG|CM_EMPTY),                   ParseEmpty,    NULL           },
  { TidyTag_INS,        "ins",        VERS_ELEM_INS,        &W3CAttrsFor_INS[0],        (CM_INLINE|CM_BLOCK|CM_MIXED),                 ParseInline,   NULL           },
  { TidyTag_ISINDEX,    "isindex",    VERS_ELEM_ISINDEX,    &W3CAttrsFor_ISINDEX[0],    (CM_BLOCK|CM_EMPTY),                           ParseEmpty,    NULL           },
  { TidyTag_KBD,        "kbd",        VERS_ELEM_KBD,        &W3CAttrsFor_KBD[0],        (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_LABEL,      "label",      VERS_ELEM_LABEL,      &W3CAttrsFor_LABEL[0],      (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_LEGEND,     "legend",     VERS_ELEM_LEGEND,     &W3CAttrsFor_LEGEND[0],     (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_LI,         "li",         VERS_ELEM_LI,         &W3CAttrsFor_LI[0],         (CM_LIST|CM_OPT|CM_NO_INDENT),                 ParseBlock,    NULL           },
  { TidyTag_LINK,       "link",       VERS_ELEM_LINK,       &W3CAttrsFor_LINK[0],       (CM_HEAD|CM_EMPTY),                            ParseEmpty,    CheckLINK      },
  { TidyTag_LISTING,    "listing",    VERS_ELEM_LISTING,    &W3CAttrsFor_LISTING[0],    (CM_BLOCK|CM_OBSOLETE),                        ParsePre,      NULL           },
  { TidyTag_MAP,        "map",        VERS_ELEM_MAP,        &W3CAttrsFor_MAP[0],        (CM_INLINE),                                   ParseBlock,    NULL           },
  { TidyTag_MENU,       "menu",       VERS_ELEM_MENU,       &W3CAttrsFor_MENU[0],       (CM_BLOCK|CM_OBSOLETE),                        ParseList,     NULL           },
  { TidyTag_META,       "meta",       VERS_ELEM_META,       &W3CAttrsFor_META[0],       (CM_HEAD|CM_EMPTY),                            ParseEmpty,    CheckMETA      },
  { TidyTag_NOFRAMES,   "noframes",   VERS_ELEM_NOFRAMES,   &W3CAttrsFor_NOFRAMES[0],   (CM_BLOCK|CM_FRAMES),                          ParseNoFrames, NULL           },
  { TidyTag_NOSCRIPT,   "noscript",   VERS_ELEM_NOSCRIPT,   &W3CAttrsFor_NOSCRIPT[0],   (CM_BLOCK|CM_INLINE|CM_MIXED),                 ParseBlock,    NULL           },
  { TidyTag_OBJECT,     "object",     VERS_ELEM_OBJECT,     &W3CAttrsFor_OBJECT[0],     (CM_OBJECT|CM_HEAD|CM_IMG|CM_INLINE|CM_PARAM), ParseBlock,    NULL           },
  { TidyTag_OL,         "ol",         VERS_ELEM_OL,         &W3CAttrsFor_OL[0],         (CM_BLOCK),                                    ParseList,     NULL           },
  { TidyTag_OPTGROUP,   "optgroup",   VERS_ELEM_OPTGROUP,   &W3CAttrsFor_OPTGROUP[0],   (CM_FIELD|CM_OPT),                             ParseOptGroup, NULL           },
  { TidyTag_OPTION,     "option",     VERS_ELEM_OPTION,     &W3CAttrsFor_OPTION[0],     (CM_FIELD|CM_OPT),                             ParseText,     NULL           },
  { TidyTag_P,          "p",          VERS_ELEM_P,          &W3CAttrsFor_P[0],          (CM_BLOCK|CM_OPT),                             ParseInline,   NULL           },
  { TidyTag_PARAM,      "param",      VERS_ELEM_PARAM,      &W3CAttrsFor_PARAM[0],      (CM_INLINE|CM_EMPTY),                          ParseEmpty,    NULL           },
  { TidyTag_PLAINTEXT,  "plaintext",  VERS_ELEM_PLAINTEXT,  &W3CAttrsFor_PLAINTEXT[0],  (CM_BLOCK|CM_OBSOLETE),                        ParsePre,      NULL           },
  { TidyTag_PRE,        "pre",        VERS_ELEM_PRE,        &W3CAttrsFor_PRE[0],        (CM_BLOCK),                                    ParsePre,      NULL           },
  { TidyTag_Q,          "q",          VERS_ELEM_Q,          &W3CAttrsFor_Q[0],          (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_RB,         "rb",         VERS_ELEM_RB,         &W3CAttrsFor_RB[0],         (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_RBC,        "rbc",        VERS_ELEM_RBC,        &W3CAttrsFor_RBC[0],        (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_RP,         "rp",         VERS_ELEM_RP,         &W3CAttrsFor_RP[0],         (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_RT,         "rt",         VERS_ELEM_RT,         &W3CAttrsFor_RT[0],         (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_RTC,        "rtc",        VERS_ELEM_RTC,        &W3CAttrsFor_RTC[0],        (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_RUBY,       "ruby",       VERS_ELEM_RUBY,       &W3CAttrsFor_RUBY[0],       (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_S,          "s",          VERS_ELEM_S,          &W3CAttrsFor_S[0],          (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_SAMP,       "samp",       VERS_ELEM_SAMP,       &W3CAttrsFor_SAMP[0],       (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_SCRIPT,     "script",     VERS_ELEM_SCRIPT,     &W3CAttrsFor_SCRIPT[0],     (CM_HEAD|CM_MIXED|CM_BLOCK|CM_INLINE),         ParseScript,   CheckSCRIPT    },
  { TidyTag_SELECT,     "select",     VERS_ELEM_SELECT,     &W3CAttrsFor_SELECT[0],     (CM_INLINE|CM_FIELD),                          ParseSelect,   NULL           },
  { TidyTag_SMALL,      "small",      VERS_ELEM_SMALL,      &W3CAttrsFor_SMALL[0],      (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_SPAN,       "span",       VERS_ELEM_SPAN,       &W3CAttrsFor_SPAN[0],       (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_STRIKE,     "strike",     VERS_ELEM_STRIKE,     &W3CAttrsFor_STRIKE[0],     (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_STRONG,     "strong",     VERS_ELEM_STRONG,     &W3CAttrsFor_STRONG[0],     (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_STYLE,      "style",      VERS_ELEM_STYLE,      &W3CAttrsFor_STYLE[0],      (CM_HEAD),                                     ParseScript,   CheckSTYLE     },
  { TidyTag_SUB,        "sub",        VERS_ELEM_SUB,        &W3CAttrsFor_SUB[0],        (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_SUP,        "sup",        VERS_ELEM_SUP,        &W3CAttrsFor_SUP[0],        (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_TABLE,      "table",      VERS_ELEM_TABLE,      &W3CAttrsFor_TABLE[0],      (CM_BLOCK),                                    ParseTableTag, CheckTABLE     },
  { TidyTag_TBODY,      "tbody",      VERS_ELEM_TBODY,      &W3CAttrsFor_TBODY[0],      (CM_TABLE|CM_ROWGRP|CM_OPT),                   ParseRowGroup, NULL           },
  { TidyTag_TD,         "td",         VERS_ELEM_TD,         &W3CAttrsFor_TD[0],         (CM_ROW|CM_OPT|CM_NO_INDENT),                  ParseBlock,    NULL           },
  { TidyTag_TEXTAREA,   "textarea",   VERS_ELEM_TEXTAREA,   &W3CAttrsFor_TEXTAREA[0],   (CM_INLINE|CM_FIELD),                          ParseText,     NULL           },
  { TidyTag_TFOOT,      "tfoot",      VERS_ELEM_TFOOT,      &W3CAttrsFor_TFOOT[0],      (CM_TABLE|CM_ROWGRP|CM_OPT),                   ParseRowGroup, NULL           },
  { TidyTag_TH,         "th",         VERS_ELEM_TH,         &W3CAttrsFor_TH[0],         (CM_ROW|CM_OPT|CM_NO_INDENT),                  ParseBlock,    NULL           },
  { TidyTag_THEAD,      "thead",      VERS_ELEM_THEAD,      &W3CAttrsFor_THEAD[0],      (CM_TABLE|CM_ROWGRP|CM_OPT),                   ParseRowGroup, NULL           },
  { TidyTag_TITLE,      "title",      VERS_ELEM_TITLE,      &W3CAttrsFor_TITLE[0],      (CM_HEAD),                                     ParseTitle,    NULL           },
  { TidyTag_TR,         "tr",         VERS_ELEM_TR,         &W3CAttrsFor_TR[0],         (CM_TABLE|CM_OPT),                             ParseRow,      NULL           },
  { TidyTag_TT,         "tt",         VERS_ELEM_TT,         &W3CAttrsFor_TT[0],         (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_U,          "u",          VERS_ELEM_U,          &W3CAttrsFor_U[0],          (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_UL,         "ul",         VERS_ELEM_UL,         &W3CAttrsFor_UL[0],         (CM_BLOCK),                                    ParseList,     NULL           },
  { TidyTag_VAR,        "var",        VERS_ELEM_VAR,        &W3CAttrsFor_VAR[0],        (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_XMP,        "xmp",        VERS_ELEM_XMP,        &W3CAttrsFor_XMP[0],        (CM_BLOCK|CM_OBSOLETE),                        ParsePre,      NULL           },
  { TidyTag_NEXTID,     "nextid",     VERS_ELEM_NEXTID,     &W3CAttrsFor_NEXTID[0],     (CM_HEAD|CM_EMPTY),                            ParseEmpty,    NULL           },

  /* proprietary elements */
  { TidyTag_ALIGN,      "align",      VERS_NETSCAPE,        NULL,                       (CM_BLOCK),                                    ParseBlock,    NULL           },
  { TidyTag_BGSOUND,    "bgsound",    VERS_MICROSOFT,       NULL,                       (CM_HEAD|CM_EMPTY),                            ParseEmpty,    NULL           },
  { TidyTag_BLINK,      "blink",      VERS_PROPRIETARY,     NULL,                       (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_COMMENT,    "comment",    VERS_MICROSOFT,       NULL,                       (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_EMBED,      "embed",      VERS_NETSCAPE,        NULL,                       (CM_INLINE|CM_IMG|CM_EMPTY),                   ParseEmpty,    NULL           },
  { TidyTag_ILAYER,     "ilayer",     VERS_NETSCAPE,        NULL,                       (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_KEYGEN,     "keygen",     VERS_NETSCAPE,        NULL,                       (CM_INLINE|CM_EMPTY),                          ParseEmpty,    NULL           },
  { TidyTag_LAYER,      "layer",      VERS_NETSCAPE,        NULL,                       (CM_BLOCK),                                    ParseBlock,    NULL           },
  { TidyTag_MARQUEE,    "marquee",    VERS_MICROSOFT,       NULL,                       (CM_INLINE|CM_OPT),                            ParseInline,   NULL           },
  { TidyTag_MULTICOL,   "multicol",   VERS_NETSCAPE,        NULL,                       (CM_BLOCK),                                    ParseBlock,    NULL           },
  { TidyTag_NOBR,       "nobr",       VERS_PROPRIETARY,     NULL,                       (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_NOEMBED,    "noembed",    VERS_NETSCAPE,        NULL,                       (CM_INLINE),                                   ParseInline,   NULL           },
  { TidyTag_NOLAYER,    "nolayer",    VERS_NETSCAPE,        NULL,                       (CM_BLOCK|CM_INLINE|CM_MIXED),                 ParseBlock,    NULL           },
  { TidyTag_NOSAVE,     "nosave",     VERS_NETSCAPE,        NULL,                       (CM_BLOCK),                                    ParseBlock,    NULL           },
  { TidyTag_SERVER,     "server",     VERS_NETSCAPE,        NULL,                       (CM_HEAD|CM_MIXED|CM_BLOCK|CM_INLINE),         ParseScript,   NULL           },
  { TidyTag_SERVLET,    "servlet",    VERS_SUN,             NULL,                       (CM_OBJECT|CM_IMG|CM_INLINE|CM_PARAM),         ParseBlock,    NULL           },
  { TidyTag_SPACER,     "spacer",     VERS_NETSCAPE,        NULL,                       (CM_INLINE|CM_EMPTY),                          ParseEmpty,    NULL           },
  { TidyTag_WBR,        "wbr",        VERS_PROPRIETARY,     NULL,                       (CM_INLINE|CM_EMPTY),                          ParseEmpty,    NULL           },

  /* this must be the final entry */
  { (TidyTagId)0,        NULL,         0,                    NULL,                       (0),                                           NULL,          NULL           }
};

#ifdef ELEMENT_HASH_LOOKUP
static uint hash(ctmbstr s)
{
    uint hashval;

    for (hashval = 0; *s != '\0'; s++)
        hashval = *s + 31*hashval;

    return hashval % ELEMENT_HASH_SIZE;
}

static Dict *install(TidyTagImpl* tags, const Dict* old)
{
    Dict *np;
    uint hashval;

    np = (Dict *)MemAlloc(sizeof(*np));
    np->name = tmbstrdup(old->name);

    hashval = hash(np->name);
    np->next = tags->hashtab[hashval];
    tags->hashtab[hashval] = np;

    np->id       = old->id;
    np->versions = old->versions;
    np->model    = old->model;
    np->parser   = old->parser;
    np->chkattrs = old->chkattrs;
    np->attrvers = old->attrvers;

    return np;
}
#endif /* ELEMENT_HASH_LOOKUP */

static const Dict* lookup( TidyTagImpl* tags, ctmbstr s )
{
    const Dict *np;

    if (!s)
        return NULL;

#ifdef ELEMENT_HASH_LOOKUP
    /* this breaks if declared elements get changed between two   */
    /* parser runs since Tidy would use the cached version rather */
    /* than the new one                                           */
    for (np = tags->hashtab[hash(s)]; np != NULL; np = np->next)
        if (tmbstrcmp(s, np->name) == 0)
            return np;

    for (np = tag_defs + 1; np < tag_defs + N_TIDY_TAGS; ++np)
        if (tmbstrcmp(s, np->name) == 0)
            return install(tags, np);

    for (np = tags->declared_tag_list; np; np = np->next)
        if (tmbstrcmp(s, np->name) == 0)
            return install(tags, np);
#else

    for (np = tag_defs + 1; np < tag_defs + N_TIDY_TAGS; ++np)
        if (tmbstrcmp(s, np->name) == 0)
            return np;

    for (np = tags->declared_tag_list; np; np = np->next)
        if (tmbstrcmp(s, np->name) == 0)
            return np;

#endif /* ELEMENT_HASH_LOOKUP */

    return NULL;
}


static void declare( TidyTagImpl* tags,
                     ctmbstr name, uint versions, uint model, 
                     Parser *parser, CheckAttribs *chkattrs )
{
    if ( name )
    {
        Dict* np = (Dict*) lookup( tags, name );
        if ( np == NULL )
        {
            np = (Dict*) MemAlloc( sizeof(Dict) );
            ClearMemory( np, sizeof(Dict) );

            np->name = tmbstrdup( name );
            np->next = tags->declared_tag_list;
            tags->declared_tag_list = np;
        }

        /* Make sure we are not over-writing predefined tags */
        if ( np->id == TidyTag_UNKNOWN )
        {
          np->versions = versions;
          np->model   |= model;
          np->parser   = parser;
          np->chkattrs = chkattrs;
          np->attrvers = NULL;
        }
    }
}

/* public interface for finding tag by name */
Bool FindTag( TidyDocImpl* doc, Node *node )
{
    const Dict *np = NULL;
    if ( cfgBool(doc, TidyXmlTags) )
    {
        node->tag = doc->tags.xml_tags;
        return yes;
    }

    if ( node->element && (np = lookup(&doc->tags, node->element)) )
    {
        node->tag = np;
        return yes;
    }
    
    return no;
}

const Dict* LookupTagDef( TidyTagId tid )
{
    const Dict *np;

    for (np = tag_defs + 1; np < tag_defs + N_TIDY_TAGS; ++np )
        if (np->id == tid)
            return np;

    return NULL;    
}

Parser* FindParser( TidyDocImpl* doc, Node *node )
{
    const Dict* np = lookup( &doc->tags, node->element );
    if ( np )
        return np->parser;
    return NULL;
}

void DefineTag( TidyDocImpl* doc, UserTagType tagType, ctmbstr name )
{
    Parser* parser = NULL;
    uint cm = 0;
    uint vers = VERS_PROPRIETARY;

    switch (tagType)
    {
    case tagtype_empty:
        cm = CM_EMPTY|CM_NO_INDENT|CM_NEW;
        parser = ParseBlock;
        break;

    case tagtype_inline:
        cm = CM_INLINE|CM_NO_INDENT|CM_NEW;
        parser = ParseInline;
        break;

    case tagtype_block:
        cm = CM_BLOCK|CM_NO_INDENT|CM_NEW;
        parser = ParseBlock;
        break;

    case tagtype_pre:
        cm = CM_BLOCK|CM_NO_INDENT|CM_NEW;
        parser = ParsePre;
        break;

    case tagtype_null:
        break;
    }
    if ( cm && parser )
        declare( &doc->tags, name, vers, cm, parser, NULL );
}

TidyIterator   GetDeclaredTagList( TidyDocImpl* doc )
{
    return (TidyIterator) doc->tags.declared_tag_list;
}

ctmbstr        GetNextDeclaredTag( TidyDocImpl* ARG_UNUSED(doc),
                                   UserTagType tagType, TidyIterator* iter )
{
    ctmbstr name = NULL;
    Dict* curr;
    for ( curr = (Dict*) *iter; name == NULL && curr != NULL; curr = curr->next )
    {
        switch ( tagType )
        {
        case tagtype_empty:
            if ( (curr->model & CM_EMPTY) != 0 )
                name = curr->name;
            break;

        case tagtype_inline:
            if ( (curr->model & CM_INLINE) != 0 )
                name = curr->name;
            break;

        case tagtype_block:
            if ( (curr->model & CM_BLOCK) != 0 &&
                 curr->parser == ParseBlock )
                name = curr->name;
            break;
    
        case tagtype_pre:
            if ( (curr->model & CM_BLOCK) != 0 &&
                 curr->parser == ParsePre )
                name = curr->name;
            break;

        case tagtype_null:
            break;
        }
    }
    *iter = (TidyIterator) curr;
    return name;
}

void InitTags( TidyDocImpl* doc )
{
    Dict* xml;
    TidyTagImpl* tags = &doc->tags;

    ClearMemory( tags, sizeof(TidyTagImpl) );

    /* create dummy entry for all xml tags */
    xml = (Dict*) MemAlloc( sizeof(Dict) );
    ClearMemory( xml, sizeof(Dict) );
    xml->name = NULL;
    xml->versions = VERS_XML;
    xml->model = CM_BLOCK;
    xml->parser = NULL;
    xml->chkattrs = NULL;
    xml->attrvers = NULL;
    tags->xml_tags = xml;
}

/* By default, zap all of them.  But allow
** an single type to be specified.
*/
void FreeDeclaredTags( TidyDocImpl* doc, UserTagType tagType )
{
    TidyTagImpl* tags = &doc->tags;
    Dict *curr, *next = NULL, *prev = NULL;

    for ( curr=tags->declared_tag_list; curr; curr = next )
    {
        Bool deleteIt = yes;
        next = curr->next;
        switch ( tagType )
        {
        case tagtype_empty:
            deleteIt = ( curr->model & CM_EMPTY ) != 0;
            break;

        case tagtype_inline:
            deleteIt = ( curr->model & CM_INLINE ) != 0;
            break;

        case tagtype_block:
            deleteIt = ( (curr->model & CM_BLOCK) != 0 &&
                         curr->parser == ParseBlock );
            break;

        case tagtype_pre:
            deleteIt = ( (curr->model & CM_BLOCK) != 0 &&
                         curr->parser == ParsePre );
            break;

        case tagtype_null:
            break;
        }

        if ( deleteIt )
        {
          MemFree( curr->name );
          MemFree( curr );
          if ( prev )
            prev->next = next;
          else
            tags->declared_tag_list = next;
        }
        else
          prev = curr;
    }
}

void FreeTags( TidyDocImpl* doc )
{
    TidyTagImpl* tags = &doc->tags;

#ifdef ELEMENT_HASH_LOOKUP
    uint i;
    Dict *prev, *next;

    for (i = 0; i < ELEMENT_HASH_SIZE; ++i)
    {
        prev = NULL;
        next = tags->hashtab[i];

        while(next)
        {
            prev = next->next;
            MemFree(next->name);
            MemFree(next);
            next = prev;
        }

        tags->hashtab[i] = NULL;
    }
#endif

    FreeDeclaredTags( doc, tagtype_null );
    MemFree( tags->xml_tags );

    /* get rid of dangling tag references */
    ClearMemory( tags, sizeof(TidyTagImpl) );
}


/* default method for checking an element's attributes */
void CheckAttributes( TidyDocImpl* doc, Node *node )
{
    AttVal *next, *attval = node->attributes;
    while (attval)
    {
        next = attval->next;
        CheckAttribute( doc, node, attval );
        attval = next;
    }
}

/* methods for checking attributes for specific elements */

void CheckIMG( TidyDocImpl* doc, Node *node )
{
    Bool HasAlt = AttrGetById(node, TidyAttr_ALT) != NULL;
    Bool HasSrc = AttrGetById(node, TidyAttr_SRC) != NULL;
    Bool HasUseMap = AttrGetById(node, TidyAttr_USEMAP) != NULL;
    Bool HasIsMap = AttrGetById(node, TidyAttr_ISMAP) != NULL;
    Bool HasDataFld = AttrGetById(node, TidyAttr_DATAFLD) != NULL;

    CheckAttributes(doc, node);

    if ( !HasAlt )
    {
        if ( cfg(doc, TidyAccessibilityCheckLevel) == 0 )
        {
            doc->badAccess |= MISSING_IMAGE_ALT;
            ReportMissingAttr( doc, node, "alt" );
        }
  
        if ( cfgStr(doc, TidyAltText) )
            AddAttribute( doc, node, "alt", cfgStr(doc, TidyAltText) );
    }

    if ( !HasSrc && !HasDataFld )
        ReportMissingAttr( doc, node, "src" );

    if ( cfg(doc, TidyAccessibilityCheckLevel) == 0 )
    {
        if ( HasIsMap && !HasUseMap )
            ReportMissingAttr( doc, node, "ismap" );
    }
}

void CheckCaption(TidyDocImpl* doc, Node *node)
{
    AttVal *attval;

    CheckAttributes(doc, node);

    attval = AttrGetById(node, TidyAttr_ALIGN);

    if (!AttrHasValue(attval))
        return;

    if (AttrValueIs(attval, "left") || AttrValueIs(attval, "right"))
        ConstrainVersion(doc, VERS_HTML40_LOOSE);
    else if (AttrValueIs(attval, "top") || AttrValueIs(attval, "bottom"))
        ConstrainVersion(doc, ~(VERS_HTML20|VERS_HTML32));
    else
        ReportAttrError(doc, node, attval, BAD_ATTRIBUTE_VALUE);
}

void CheckHTML( TidyDocImpl* doc, Node *node )
{
    CheckAttributes(doc, node);
}

void CheckAREA( TidyDocImpl* doc, Node *node )
{
    Bool HasAlt = AttrGetById(node, TidyAttr_ALT) != NULL;
    Bool HasHref = AttrGetById(node, TidyAttr_HREF) != NULL;
    Bool HasNohref = AttrGetById(node, TidyAttr_NOHREF) != NULL;

    CheckAttributes(doc, node);

    if ( !HasAlt )
    {
        if ( cfg(doc, TidyAccessibilityCheckLevel) == 0 )
        {
            doc->badAccess |= MISSING_LINK_ALT;
            ReportMissingAttr( doc, node, "alt" );
        }
    }

    if ( !HasHref && !HasNohref )
        ReportMissingAttr( doc, node, "href" );
}

void CheckTABLE( TidyDocImpl* doc, Node *node )
{
    AttVal* attval;
    Bool HasSummary = AttrGetById(node, TidyAttr_SUMMARY) != NULL;

    CheckAttributes(doc, node);

    /* a missing summary attribute is bad accessibility, no matter
       what HTML version is involved; a document without is valid */
    if (cfg(doc, TidyAccessibilityCheckLevel) == 0)
    {
        if (!HasSummary)
        {
            doc->badAccess |= MISSING_SUMMARY;
            ReportMissingAttr( doc, node, "summary");
        }
    }

    /* convert <table border> to <table border="1"> */
    if ( cfgBool(doc, TidyXmlOut) && (attval = AttrGetById(node, TidyAttr_BORDER)) )
    {
        if (attval->value == NULL)
            attval->value = tmbstrdup("1");
    }
}

/* add missing type attribute when appropriate */
void CheckSCRIPT( TidyDocImpl* doc, Node *node )
{
    AttVal *lang, *type;
    char buf[16];

    CheckAttributes(doc, node);

    lang = AttrGetById(node, TidyAttr_LANGUAGE);
    type = AttrGetById(node, TidyAttr_TYPE);

    if (!type)
    {
        /* check for javascript */
        if (lang)
        {
            /* Test #696799. lang->value can be NULL. */
            buf[0] = '\0';
            tmbstrncpy(buf, lang->value, sizeof(buf));
            buf[10] = '\0';

            if (tmbstrncasecmp(buf, "javascript", 10) == 0 ||
                 tmbstrncasecmp(buf,   "jscript",  7) == 0)
            {
                AddAttribute(doc, node, "type", "text/javascript");
            }
            else if (tmbstrcasecmp(buf, "vbscript") == 0)
            {
                /* per Randy Waki 8/6/01 */
                AddAttribute(doc, node, "type", "text/vbscript");
            }
        }
        else
        {
            AddAttribute(doc, node, "type", "text/javascript");
        }

        type = AttrGetById(node, TidyAttr_TYPE);

        if (type != NULL)
        {
            ReportAttrError(doc, node, type, INSERTING_ATTRIBUTE);
        }
        else
        {
            ReportMissingAttr(doc, node, "type");
        }
    }
}


/* add missing type attribute when appropriate */
void CheckSTYLE( TidyDocImpl* doc, Node *node )
{
    AttVal *type = AttrGetById(node, TidyAttr_TYPE);

    CheckAttributes( doc, node );

    if ( !type || !type->value || !tmbstrlen(type->value) )
    {
        type = RepairAttrValue(doc, node, "type", "text/css");
        ReportAttrError( doc, node, type, INSERTING_ATTRIBUTE );
    }
}

/* add missing type attribute when appropriate */
void CheckLINK( TidyDocImpl* doc, Node *node )
{
    AttVal *rel = AttrGetById(node, TidyAttr_REL);

    CheckAttributes( doc, node );

    /* todo: <link rel="alternate stylesheet"> */
    if (AttrValueIs(rel, "stylesheet"))
    {
        AttVal *type = AttrGetById(node, TidyAttr_TYPE);
        if (!type)
        {
            AddAttribute( doc, node, "type", "text/css" );
            type = AttrGetById(node, TidyAttr_TYPE);
            ReportAttrError( doc, node, type, INSERTING_ATTRIBUTE );
        }
    }
}

/* reports missing action attribute */
void CheckFORM( TidyDocImpl* doc, Node *node )
{
    AttVal *action = AttrGetById(node, TidyAttr_ACTION);

    CheckAttributes(doc, node);

    if (!action)
        ReportMissingAttr(doc, node, "action");
}

/* reports missing content attribute */
void CheckMETA( TidyDocImpl* doc, Node *node )
{
    AttVal *content = AttrGetById(node, TidyAttr_CONTENT);

    CheckAttributes(doc, node);

    if (!content)
        ReportMissingAttr( doc, node, "content" );
    /* name or http-equiv attribute must also be set */
}


Bool nodeIsText( Node* node )
{
  return ( node && node->type == TextNode );
}

Bool nodeHasText( TidyDocImpl* doc, Node* node )
{
  if ( doc && node )
  {
    uint ix;
    Lexer* lexer = doc->lexer;
    for ( ix = node->start; ix < node->end; ++ix )
    {
        /* whitespace */
        if ( !IsWhite( lexer->lexbuf[ix] ) )
            return yes;
    }
  }
  return no;
}

Bool nodeIsElement( Node* node )
{
  return ( node && 
           (node->type == StartTag || node->type == StartEndTag) );
}

/* Compare & result to operand.  If equal, then all bits
** requested are set.
*/
Bool nodeMatchCM( Node* node, uint contentModel )
{
  return ( node && node->tag && 
           (node->tag->model & contentModel) == contentModel );
}

/* True if any of the bits requested are set.
*/
Bool nodeHasCM( Node* node, uint contentModel )
{
  return ( node && node->tag && 
           (node->tag->model & contentModel) != 0 );
}

Bool nodeCMIsBlock( Node* node )
{
  return nodeHasCM( node, CM_BLOCK );
}
Bool nodeCMIsInline( Node* node )
{
  return nodeHasCM( node, CM_INLINE );
}
Bool nodeCMIsEmpty( Node* node )
{
  return nodeHasCM( node, CM_EMPTY );
}

Bool nodeIsHeader( Node* node )
{
    TidyTagId tid = TagId( node  );
    return ( tid && 
             tid == TidyTag_H1 ||
             tid == TidyTag_H2 ||
             tid == TidyTag_H3 ||        
             tid == TidyTag_H4 ||        
             tid == TidyTag_H5 ||
             tid == TidyTag_H6 );
}

uint nodeHeaderLevel( Node* node )
{
    TidyTagId tid = TagId( node  );
    switch ( tid )
    {
    case TidyTag_H1:
        return 1;
    case TidyTag_H2:
        return 2;
    case TidyTag_H3:
        return 3;
    case TidyTag_H4:
        return 4;
    case TidyTag_H5:
        return 5;
    case TidyTag_H6:
        return 6;
    default:
    {
        /* fall through */
    }
    }
    return 0;
}

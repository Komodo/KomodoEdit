


import os, sre, sys

os_join = os.path.join
os_isdir = os.path.isdir
os_isfile = os.path.isfile
os_split = os.path.split
os_dirname=os.path.dirname
os_basename=os.path.basename
os_splitext = os.path.splitext

from wnd.tools.doctool.chmcompile import ChmCompiler
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

KW_SITE='::site::'
KW_FOLDER='::folder::'
KW_ITEM='::item::'
KW_DEF= '::def::'

KW_ROOT='::root::'
KW_ROOTSITE='::rootsite::'
KW_ROOTSITENAME='::rootsitename::'
KW_CWDIR='::cwdir::'
KW_CWDIRNAME='::cwdirname::'
KW_UPDIR='::updir::'
KW_UPDIRNAME='::updirname::'
KW_NEXTSITE='::nextsite::'
KW_NEXTSITENAME='::nextsitename::'
KW_PREVSITE='::prevsite::'
KW_PREVSITENAME='::prevsitename::'
KW_HEADER='::header::'
KW_FOOTER='::footer::'	

KW_DEFPAGE='::defaultpage::'
KW_TABWIDTH ='::tabwidth::'

KW_CTS_HDR1 = '::contents-header1::'
KW_CTS_HDR2 = '::contents-header2::'
	
KW_CMP_TITLE='::compiler-title::'
KW_CMP_FONT='::compiler-font::'
KW_CMP_DEFTOPIC='::compiler-defaulttopic::'
KW_CMP_OUTFILE='::compiler-outputfile::'
KW_CMP_KEEPPROJ='::compiler-keepprojectfiles::'
KW_CMP_LOG='::compiler-logfile::'
KW_CMP_ERRLOG='::compiler-errorlog::'
KW_CMP_KEEPSITELOG='::compiler-keepsitelog::'


ILLEGALCHARS =  '/\:?*<>"|'

OPTIONS=(KW_DEFPAGE,
					KW_TABWIDTH)
EXPRESSIONS=(KW_DEF, 
								KW_HEADER,
								KW_FOOTER)
SITETOKENS=(KW_SITE,
							KW_FOLDER,
							KW_ITEM)
KEYWORDS=(KW_ROOT, 
							KW_ROOTSITE,
							KW_ROOTSITENAME,
							KW_CWDIR,
							KW_CWDIRNAME,
							KW_UPDIR,
							KW_UPDIRNAME,
							KW_NEXTSITE,
							KW_NEXTSITENAME,
							KW_PREVSITE,
							KW_PREVSITENAME)
CONTENTSTOKENS=(KW_CTS_HDR1,
										KW_CTS_HDR2)
COMPILEROPTIONS=(KW_CMP_TITLE,
										KW_CMP_FONT, 
										KW_CMP_DEFTOPIC,
										KW_CMP_OUTFILE,
										KW_CMP_KEEPPROJ,
										KW_CMP_LOG,
										KW_CMP_ERRLOG,
										KW_CMP_KEEPSITELOG)

TOKENS= SITETOKENS+EXPRESSIONS+CONTENTSTOKENS+	 \
				COMPILEROPTIONS+OPTIONS

ESCAPETOKENS=TOKENS + KEYWORDS
RxTokensPat=sre.compile( r'(\\?)(%s)' % '|'.join(ESCAPETOKENS))
RxCommentsPat=sre.compile( r'(\\?)(#)')

## these keyqords expect bool values
EXPECTINGBOOL= (KW_CMP_KEEPPROJ,KW_CMP_LOG, KW_CMP_ERRLOG, KW_CMP_KEEPSITELOG)

def MakeValue(token, value):
	if token in  EXPECTINGBOOL:
		return bool(value=='True') 
	return value
	

## default css
CSS ='''
body, th, td {
	font-family: verdana, Arial, sans-serif;
	font-size: 100%;}

pre, P, DL, table {
	margin-left: 2em;
	margin-right: 2em;}

table {
	background-color: #E1E1E1;
	}

.import {
	color: blue;
	font-family: verdana, Arial, sans-serif;}

/*  default gray pre */
pre {background-color: #E5E5E5;
				padding: 7pt;
				font: 90% verdana, Arial, sans-serif;
				white-space: pre;
				width: 100%;}

DT{
	font-weight: bold;
	font-style: italic;
	font-size: 100%;
	}

tt, code {
	font-size: 110% ;
	font-family: verdana, Arial, sans-serif;
	font-weight: bold;
	}

H1, H2, H3, H4, H5, H6 {
	font-family: verdana, Arial, sans-serif;}

A:link { color:#0000A0; }
A:visited { color:#6060CA; }
A:hover { color:#0000A0; background-color: #EBEBEB; }

'''

HREF = '<a href="%s">%s</a><br>\n'
HNAME = '<a name="%s">%s</a><p>\n'
H1='<H1>%s</H1>\n'
H2='<H2><a NAME="%s">%s</a></H2>\n'
H3='<H3>%s</H3>\n'
H4='<H4>%s</H4>\n'
P='<p>\n'
BLQ='<blockquote>\n'
ENDBLQ='</blockquote>\n'

FOOTER = '\n</BODY></HTML>'
def HEADER(title, cssUpLevel=None):
		#cssUpLevel=cssUpLevel*'../'
		hd = '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN"><HTML>
		<HEAD>
		<TITLE> %s </TITLE>
		<META NAME="Generator" CONTENT="WndDoc">
		<META NAME="Author" CONTENT="">
		<META NAME="Keywords" CONTENT="">
		<META NAME="Description" CONTENT="">
		<link rel="stylesheet" type="text/css" href="%sdefault.css">
		</HEAD>
		<BODY>
		''' % (title, cssUpLevel or '')
		return hd.replace('\t', '')


MAX_PATH = 260

ERR_OK = 0
ERR_MAX_PATH = 1
ERR_MAX_TOKENNAME = 2
ERR_ILEGALCHAR = 3

ERRORS = {
ERR_OK: 0,
ERR_MAX_TOKENNAME: 'token name to long: %s %s',
ERR_ILEGALCHAR: '%s %s\n	token names may not contain these chars: /\:?*<>"|',
}

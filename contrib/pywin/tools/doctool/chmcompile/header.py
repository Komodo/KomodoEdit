
import tempfile, os, sre, shutil, bsddb, subprocess
import _winreg as reg

os_join = os.path.join
os_splitext = os.path.splitext
os_isfile = os.path.isfile
os_isdir = os.path.isdir
os_islink = os.path.islink
os_dirname=os.path.dirname
os_basename=os.path.basename
os_split = os.path.split
os_normpath=os.path.normpath

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

EOF=''
QUOTE = lambda s: '"%s"' % s

cleanPat = sre.compile(r'[\t\n\r\s]+')
CLEANSTRING = lambda s: cleanPat.subn(' ', s)[0].strip()
rxFlags = sre.S|sre.M|sre.I|sre.X	
rxGetNamesPat =sre.compile(
	r'''<\s* A\s+ .*? NAME\s* =\s* "([^"]+?)" .*? \s*> 
	(.*?)
	<\s*/\s*a\s*>''',	rxFlags)
rxStripTags = sre.compile(r'<.*?>', rxFlags)
rxCleanString = sre.compile(r'[\t\n\r]+')
rxGetTitle  = sre.compile( r'<\s*title\s*>(.*?)<\s*/title\s*>', rxFlags)



def UL(level=0): return '%s<UL>\n' % ('\t'*level)
def END_UL(level=0): return  '%s</UL>\n' % ('\t'*level)
FOOTER = '\n</BODY></HTML>'
CONTENTS_HEADER = '''<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">
<HTML><HEAD>
<meta name="GENERATOR" content="Microsoft&reg; HTML Help Workshop 4.1">
<!-- Sitemap 1.0 -->
</HEAD><BODY>\n
<OBJECT type="text/site properties">
<param name="Window Styles" value="0x800027">
<param name="ImageType" value="Folder">
</OBJECT>\n
'''

INDEX_HEADER='''<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">
<HTML><HEAD>
<meta name="GENERATOR" content="Microsoft&reg; HTML Help Workshop 4.1">
<!-- Sitemap 1.0 -->
</HEAD>
<BODY>
<OBJECT type="text/site properties">
</OBJECT>\n
'''


OPTIONS={
'Auto Index':'Yes',							# ??
'Binary TOC':'Yes',
'Enhanced decompilation':'Yes',		# ??
'Compatibility':'1.1 or later',
'Display compile progress':'Yes',
'Full-text search':'Yes',
'Default Window':'main',
'Default Font':'Arial,8,0',
'Compiled file':None,
'Contents file':None,
'Index file':None,
'Default topic':None,
'Title':None,
'Error log file':None
}

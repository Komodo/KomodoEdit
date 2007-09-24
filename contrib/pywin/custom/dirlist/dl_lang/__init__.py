"""language support for the view"""

import imp, os

_PATH= os.path.split(__file__)[0]
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

def get_lang(lang_code):
	try:
		return imp.load_source('dl_lang_%s' %  lang_code, os.path.join(_PATH, '%s.py' % lang_code))
	except:
		return imp.load_source('lang_en', os.path.join(_PATH, 'en.py'))



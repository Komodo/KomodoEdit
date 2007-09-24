#!/usr/home/sweetapp/bin/python

import cgitb; cgitb.enable()
import cgi
from SilverCity import LanguageInfo
import urllib
import sys
import source2html
import os

# change this to point to the correct template file
default_template_name = 'cgi-styler-url-template.html'
template_path = './styler-templates'

encodings = [
    ("utf-8" , "utf-8 (Unicode, worldwide)"),
    ("utf-16" , "utf-16 (Unicode, worldwide)"),
    ("iso-8859-1" , "iso-8859-1 (Western Europe)"),
    ("iso-8859-2" , "iso-8859-2 (Central Europe"),
    ("iso-8859-3" , "iso-8859-3 (Southern Europe)"),
    ("iso-8859-4" , "iso-8859-3 (Baltic Rim)"),
    ("iso-8859-5" , "iso-8859-5 (Cyrillic)"),
    ("iso-8859-7" , "iso-8859-7 (Greek)"),
    ("iso-8859-9" , "iso-8859-9 (Turkish)"),

    ("windows-1250" , "windows-1250 (Central Europe)"),
    ("windows-1251" , "windows-1251 (Cyrillic)"),
    ("windows-1252" , "windows-1252 (Western Europe)"),
    ("windows-1253" , "windows-1252 (Greek)"),
    ("windows-1254" , "windows-1254 (Turkish)"),
    ("windows-1255" , "windows-1255 (Hebrew)"),
    ("windows-1256" , "windows-1256 (Arabic)"),
    ("windows-1257" , "windows-1257 (Baltic Rim)"),
]

def guess_language(url, content):
    if url is not None:
        ext = url.split('.')[-1]
        extension_guesses = LanguageInfo.guess_languages_for_extension(ext)
    else:
        extension_guesses = []
    
    if len(extension_guesses) == 1:
        return extension_guesses[0]
    else:
        shebang = content.split('\n')[0]
        shebang_guesses = LanguageInfo.guess_languages_for_shebang(shebang)

        if len(extension_guesses) > 0:
            guesses = [eg for eg in extension_guesses
                           if eg in shebang_guesses]
        else:
            guesses = shebang_guesses

        if len(guesses) == 1:
            return guesses[0]

        from SilverCity import NULL
        return NULL.null_language_info
    
def create_generator(source_url, generator_name, content):
    if generator_name:
        return LanguageInfo.find_generator_by_name(generator_name)()
    else:
        return guess_language(source_url, content).get_default_html_generator()()

def handle_submit(form):
    if form.has_key('source'):
        source_uri = None
        source = form['source'].value
        title = "SilverCity Styled Source"
    else:
        if form.has_key('uploadedfile'):
            source_uri = form['uploadedfile'].filename
            source = form['uploadedfile'].file.read()

            if source_uri.count('\\') > source_uri.count('/'):
                title = source_uri.split('\\')[-1]
            else:
                title = source_uri.split('/')[-1]                
        else:        
            source_uri = form['sourceuri'].value
            source = urllib.urlopen(source_uri).read()
        
            title = source_uri.split('/')[-1]
        
    style_uri = form['styleuri'].value
    encoding = form['encoding'].value

    if encoding != 'Auto':
        source = unicode(source, encoding).encode('utf-8')
    else:
        source = unicode(source)
        
    if form['lexer'].value == 'Auto':
        generator = create_generator(source_uri, None, source)
    else:
        generator = create_generator(source_uri, form['lexer'].value, source)

    print source2html.xhtml_prefix % {
        'title' : title,
        'css' : style_uri}
    
    generator.generate_html(sys.stdout, source)    
    print source2html.suffix

def handle_form(template_name):
    template = file(os.path.join(template_path, template_name), 'r').read()

    generators = LanguageInfo.get_generator_names_descriptions()
    generators.sort()

    template = template % {
        'template' : template_name,
        'generators' : '\n'.join(['<option value="%s">%s</option>' % (name, description) for name, description in generators]),
        'encodings' : '\n'.join(['<option value="%s">%s</option>' % (value, name) for value, name in encodings])}

    print template    

print 'Content-type: text/html'
print
    
form = cgi.FieldStorage(keep_blank_values=True)
    
if form.has_key('submit'):
    handle_submit(form)
else:
    if form.has_key('template'):
        template = form['template'].value
    else:
        template = os.path.join(default_template_name)
    
    handle_form(template)

# make kpf files
import fnmatch, os, string
import os

def Walk( root, recurse=0, pattern='*', return_folders=0, norm_root=''):
    # initialize
    result = []

    # must have at least root folder
    try:
        names = os.listdir(root)
    except os.error:
        return result

    # expand pattern
    if not pattern:
        pat_list = ['*']
    elif ';' in pattern:
        pat_list = string.split(pattern, ';')
    else:
        pat_list = [pattern]

    # check each file
    for name in names:
        fullname = os.path.normpath(os.path.join(root, name))
        # grab if it matches our pattern and entry type
        for pat in pat_list:
            if fnmatch.fnmatch(name, pat):
                if os.path.isfile(fullname) or (return_folders and os.path.isdir(fullname)):
                    if fullname.startswith(norm_root):
                        fullname = fullname[len(norm_root):]
                    result.append(fullname)
                continue

        # recursively scan other folders, appending results
        if recurse:
            if os.path.isdir(fullname) and not os.path.islink(fullname):
                result = result + Walk( fullname, recurse, pattern, return_folders, norm_root )

    return result


mappings = (
    ('xul.pkf', '../src/chrome/komodo/content', '*.xul'),
    ('js.kpf', '../src/chrome/komodo/content', '*.js'),
    ('editor.kpf', '../src/editor:../src/chrome/komodo/content/editor:../src/chrome/komodo/locale/en-US/editor', '*.py;*.idl;*.js;*.xul;*.dtd'),
    ('lint.kpf', '../src/lint', '*.py;*.idl'),
    ('debugger.kpf', '../src/debugger', '*.py;*.idl'),
    ('projects.kpf', '../src/projects', '*.py;*.idl'),
    ('prefs.kpf', '../src/pref:../src/chrome/komodo/content/pref:../src/chrome/komodo/locale/en-US/pref', '*.py;*.idl;*.js;*.xul;*.dtd'),
    ('find.kpf', '../src/find:../src/chrome/komodo/content/find:../src/chrome/komodo/locale/en-US/find', 'Conscript;*.py;*.idl;*.js;*.xul;*.dtd'),
    ('languages.kpf', '../src/languages', '*.py;*.idl'),
    ('scintilla.kpf', '../src/scintilla:../src/SciMoz', '*.cxx;*.c;*.cpp;*.idl;*.py'),
    )

for fname, pathset, pattern in mappings:
    files = []
    for path in pathset.split(':'):
        files += Walk(path, recurse=1, pattern=pattern, return_folders=0, norm_root='..\\')
    print "fname = ", fname
    data = '<project name="%s">\n    <files>\n' % fname
    for file in files:
        data += '        <file url="%s"/>\n' % file.replace('\\', '/')
    data += '</files>\n</project>'
    open(os.path.join('..', fname), 'w').write(data)
    print "made", fname
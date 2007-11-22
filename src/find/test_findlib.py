#!python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****


def test():
    r"""
    Simple usage of 'find' and 'findall':

        >>> import findlib
        >>> result = findlib.find("hello there", "he")
        >>> print result
        0-2: found 'he'
        >>> results = findlib.findall("hello there", "he")
        >>> for result in results:
        ...     print result
        ...
        0-2: found 'he'
        7-9: found 'he'
        >>>

    Simple usage of 'replace' and 'replaceall':

        >>> result = findlib.replace("Hello there", "he", "foo")
        >>> print result
        0-2: replace 'He' with 'foo'
        >>> results = findlib.replaceall("Hello there", "he", "foo")
        >>> for result in results:
        ...     print result
        ...
        0-2: replace 'He' with 'foo'
        7-9: replace 'he' with 'foo'
        >>>

    Specify a starting offset:

        >>> import findlib
        >>> result = findlib.find("Hello there", "he", 4)
        >>> print result
        7-9: found 'he'
        >>>

    Using some options (case-sensitivity):

        >>> import findlib
        >>> options = {}
        >>> options["case"] = "sensitive"
        >>> results = findlib.findall("Hello there", "he", **options)
        >>> for result in results:
        ...     print result
        ...
        7-9: found 'he'
        >>>
        >>> options["case"] = "insensitive"
        >>> results = findlib.findall("Hello there", "he", **options)
        >>> for result in results:
        ...     print result
        ...
        0-2: found 'He'
        7-9: found 'he'
        >>> options["case"] = "smart"
        >>> results = findlib.findall("Hello there", "he", **options)
        >>> for result in results:
        ...     print result
        ...
        0-2: found 'He'
        7-9: found 'he'
        >>> results = findlib.findall("Hello there", "He", **options)
        >>> for result in results:
        ...     print result
        ...
        0-2: found 'He'
        >>>

    Using some options (wildcard and regex-python searches):

        >>> import findlib
        >>> options = {}
        >>> options["patternType"] = "simple"
        >>> results = findlib.findall("fe fi fo fum", "f", **options)
        >>> for result in results:
        ...     print result
        ...
        0-1: found 'f'
        3-4: found 'f'
        6-7: found 'f'
        9-10: found 'f'
        >>> options["patternType"] = "wildcard"
        >>> results = findlib.findall("fe fi fo fum", "f?", **options)
        >>> for result in results:
        ...     print result
        ...
        0-2: found 'fe'
        3-5: found 'fi'
        6-8: found 'fo'
        9-11: found 'fu'
        >>> options["matchWord"] = 1
        >>> results = findlib.findall("fe fi fo fum", "f?", **options)
        >>> for result in results:
        ...     print result
        ...
        0-2: found 'fe'
        3-5: found 'fi'
        6-8: found 'fo'
        >>> options["patternType"] = "regex-python"
        >>> options["matchWord"] = 0
        >>> results = findlib.findall("fe fi fo fum", "f[eu]m?", **options)
        >>> for result in results:
        ...     print result
        ...
        0-2: found 'fe'
        9-12: found 'fum'

    Searching backwards:

        >>> import findlib
        >>> options = {}
        >>> options["patternType"] = "wildcard"
        >>> options["searchBackward"] = 0
        >>> results = findlib.findall("fe fi fo fum", "f?", **options)
        >>> for result in results:
        ...     print result
        ...
        0-2: found 'fe'
        3-5: found 'fi'
        6-8: found 'fo'
        9-11: found 'fu'
        >>> options["searchBackward"] = 1
        >>> result = findlib.find("fe fi fo fum", "f?", 11, **options)
        >>> print result
        9-11: found 'fu'

    Finding and replacing with \ characters:
    (http://bugs.activestate.com/show_bug.cgi?id=19447)

        >>> import findlib
        >>> results = findlib.findall('quoted \\"string\\" here', '\\')
        >>> for result in results:
        ...     print result
        ...
        7-8: found '\'
        15-16: found '\'

        >>> print findlib.find('quoted \\"string\\" here', '\\')
        7-8: found '\'

        >>> print findlib.replace('quoted \\"string\\" here', '\\', '')
        7-8: replace '\' with ''

        >>> print findlib.replace('quoted \\\\"string\\\\" here', '\\\\', 'a')
        7-9: replace '\\' with 'a'

        >>> print findlib.replace('quoted \\\\"string\\\\" here', '\\\\', '\\')
        7-9: replace '\\' with '\'

        >>> print findlib.replace('quoted \\\\"string\\\\" here', '\\\\', '\\\\a\\')
        7-9: replace '\\' with '\a\'

        >>> print findlib.replace('quoted \\\\"string\\\\" here', '\\\\', '\\\\\\')
        7-9: replace '\\' with '\\\'

        >>> print findlib.replace('quoted "string" here', '(str)ing', '\\1', patternType="regex-python")
        8-14: replace 'string' with 'str'

        >>> print findlib.replace('quoted "string" here', '(str)ing', '\\g<1>', patternType="regex-python")
        8-14: replace 'string' with 'str'

        >>> print findlib.replace('quoted "string" here', '(?P<var>str)ing', '\\g<var>', patternType="regex-python")
        8-14: replace 'string' with 'str'

    XXX find, replace, and replaceall in all of the above
    """
    import doctest
    return doctest.testmod()

if __name__ == "__main__":
    test()


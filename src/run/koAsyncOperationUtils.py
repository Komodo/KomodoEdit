#!/usr/bin/python

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
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2008
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

from xpcom import components, nsError, ServerException

class koAsyncOperationBase(object):
    """Utility class to help creating asynchronous operations"""

    _com_interfaces_ = components.interfaces.koIAsyncOperation

    STATUS_RUNNING = components.interfaces.koIAsyncOperation.STATUS_RUNNING
    STATUS_STOPPING = components.interfaces.koIAsyncOperation.STATUS_STOPPING

    def __init__(self, run_function, *args, **kwargs):
        # status can only be one of: running, stopping
        self.status = self.STATUS_RUNNING
        self.func = run_function
        self.args = args
        self.kwargs = kwargs

    # stop the asynchronous command. Does not have to be implemented,
    # which by default will raise an exception "Cannot be stopped"
    def stop(self):
        raise ServerException(nsError.NS_ERROR_FAILURE, "Cannot be stopped")

    # Private method: called by the koIAsyncService
    def run(self):
        return self.func(*self.args, **self.kwargs)

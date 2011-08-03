#===============================================================================
#    Copyright 2005-2007 Tassos Koutsovassilis
#
#    This file is part of Porcupine.
#    Porcupine is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 2.1 of the License, or
#    (at your option) any later version.
#    Porcupine is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#    You should have received a copy of the GNU Lesser General Public License
#    along with Porcupine; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#===============================================================================
"Security Policy related classes"

import types

from porcupine.db import db
from porcupine import serverExceptions

def policymethod(policyid):
    class PolicyMethod(object):
        def __init__(self, function):
            self.func = function
            self.name = function.func_name
            self.__doc__ = function.func_doc
            
        def __get__(self, servlet, servlet_class):
            policy = db.getItem(policyid)
            user = servlet.session.user
            
            if self.userHasPolicy(user, policy):
                return types.MethodType(self.func, servlet, servlet_class)
            else:
                raise serverExceptions.PolicyViolation, \
                "This action is restricted due to policy '%s'" \
                % policy.displayName.value
                
        def userHasPolicy(self, user, policy):
            policyGranted = policy.policyGranted.value
            
            userID = user._id
            if userID in policyGranted or user.isAdmin():
                return True
            
            memberOf = ['everyone']
            memberOf.extend(user.memberof.value)
            if hasattr(user, 'authenticate'):
                memberOf.extend(['authusers']) 
            
            for groupid in memberOf:
                if groupid in policyGranted:
                    return True
            
            return False
    
    return PolicyMethod
    


        
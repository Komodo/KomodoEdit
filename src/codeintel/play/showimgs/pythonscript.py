import os

__privateGlobalVar = 1
_protectedGlobalVar = 1
publicGlobalVar = 1

class __PrivateClass: pass
class _ProtectedClass: pass
class PublicClass:
    __privateClassVar = 1
    _protectedClassVar = 1
    publicClassVar = 1
    def __privateFunction(self): pass
    def _protectedFunction(self): pass
    def publicFunction(self):
        self._protectedInstanceVar = 1
        self.__privateInstanceVar = 1
        self.publicInstanceVar = 1

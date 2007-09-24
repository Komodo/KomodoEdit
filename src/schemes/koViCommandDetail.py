from xpcom import components, ServerException
from xpcom.server import WrapObject, UnwrapObject

# xpcom class used for storing vi command details
class koViCommandDetail:
    _com_interfaces_ = [components.interfaces.koIViCommandDetail]
    _reg_clsid_ = "{09cfa345-845c-4569-81f1-a1535ab5a5c0}"
    _reg_contractid_ = "@activestate.com/koViCommandDetail;1"
    _reg_desc_ = "Vi Command Details"

    def __init__(self):
        self.startLine = 0;
        self.endLine = 0;
        self.forced = False;
        self.commandName = "";
        self.leftover = "";
        self.arguments = [];
        self.rawCommandString = "";

    def getArguments(self):
        return self.arguments

    def setArguments(self, args):
        self.arguments = args

    def clear(self):
        self.startLine = 0;
        self.endLine = 0;
        self.forced = False;
        self.commandName = "";
        self.leftover = "";
        self.arguments = [];
        self.rawCommandString = "";

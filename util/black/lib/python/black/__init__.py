# The Black Tool main Python package


# The primary Black exception

class BlackError(Exception):
    pass


# The Black version is made up of the following parts (others, like a
# "quality" whose value could be "beta" may be added later):
#   "major": <int>      Marketing number.
#   "minor": <int>      Incremented for incompatible changes in basic
#                       functionality
#   "patch": <int>      Incremented for bug fixes and changes in the
#                       configuration item library (i.e. changes in
#                       lib/python/black/configure/...)
_version_ = {"major": 0,
             "minor": 4,
             "patch": 1,
            }

def GetVersionTuple():
    return _version_["major"], _version_["minor"], _version_["patch"]

def GetPrettyVersion():
    return "%d.%d.%d" % GetVersionTuple()



from xpcom import components, COMException

class PreferenceSerializer(object):
    """A helper class to help serialize objects and Komodo preferences.

    The 'serialize_items' parameter must be a list of (name, type) tuples, with
    'name' being the attribute name that is to be serialized and 'type' being
    the Komodo preference type to store/retrieve with.

    Example:
        class myObj(PreferenceSerializer):
            prefmap = [('mynum', 'long')]
            def __init__(self):
                self.PreferenceSerializer.__init__(self, prefmap)
                self.mynum = 1
                koPref = self.serializeToPreference()
                self.mynum = 0
                self.unserializeFromPreference(koPref)
                assert (self.mynum == 1)
    """
    def __init__(self, serialize_items=None, ignore_missing_fields=False):
        self.__serialize_items = serialize_items or []
        self.__ignore_missing_fields = ignore_missing_fields

    def serializeToPreference(self):
        pref = components.classes[
                    '@activestate.com/koPreferenceSet;1'].createInstance()
        for attr_name, attr_type in self.__serialize_items:
            val = getattr(self, attr_name, None)
            if val is not None:
                if attr_type in ("int", "long", "number"):
                    pref.setLongPref(attr_name, val)
                elif attr_type in ("float", "double"):
                    pref.setDoublePref(attr_name, val)
                elif attr_type in ("bool", "boolean"):
                    pref.setBooleanPref(attr_name, val)
                elif attr_type in ("str", "string"):
                    pref.setStringPref(attr_name, val)
                elif attr_type in ("pref", "prefset", "koIPref", "koIPreferenceContainer"):
                    # Warning: unused code path
                    pref.setPref(attr_name, val)
        return pref

    def unserializeFromPreference(self, pref):
        for attr_name, attr_type in self.__serialize_items:
            try:
                if attr_type in ("int", "long", "number"):
                    setattr(self, attr_name, pref.getLongPref(attr_name))
                elif attr_type in ("float", "double"):
                    setattr(self, attr_name, pref.getDoublePref(attr_name))
                elif attr_type in ("bool", "boolean"):
                    setattr(self, attr_name, pref.getBooleanPref(attr_name))
                elif attr_type in ("str", "string"):
                    setattr(self, attr_name, pref.getStringPref(attr_name))
                elif attr_type in ("pref", "prefset", "koIPref", "koIPreferenceContainer"):
                    # Warning: unused code path
                    setattr(self, attr_name, pref.getPref(attr_name))
            except COMException:
                # Pref did not exist
                if not self.__ignore_missing_fields:
                    raise



"""Apply these patches to the Mozilla CVS head."""

def applicable(config):
    if config.mozSrcType != "cvs":
        raise ValueError("don't know if should apply these patches: "
                         "mozSrcType != 'cvs'")
    elif config.mozSrcCvsTag is None: # i.e. the HEAD
        return True
    else:
        return False


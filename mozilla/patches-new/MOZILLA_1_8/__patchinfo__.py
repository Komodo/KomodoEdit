
"""Apply these patches to Mozilla CVS branches starting with
'MOZILLA_1_8'."""

def applicable(config):
    if config.mozSrcType != "cvs":
        raise ValueError("don't know if should apply these patches: "
                         "mozSrcType != 'cvs'")
    elif config.mozSrcCvsTag is not None \
         and config.mozSrcCvsTag.startswith("MOZILLA_1_8"):
        return True
    else:
        return False


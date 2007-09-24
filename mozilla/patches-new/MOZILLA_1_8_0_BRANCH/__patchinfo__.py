
"""Apply these patches to the MOZILLA_1_8_0_BRANCH Mozilla CVS branch."""

def applicable(config):
    if config.mozSrcType != "cvs":
        raise ValueError("don't know if should apply these patches: "
                         "mozSrcType != 'cvs'")
    elif config.mozSrcCvsTag == "MOZILLA_1_8_0_BRANCH":
        return True
    else:
        return False


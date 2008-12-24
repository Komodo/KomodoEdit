
"""Apply these patches to the Mozilla Mercurial 1.9.1 branch."""

def applicable(config):
    if config.mozSrcType != "hg":
        return False
    elif config.mozSrcHgTag is None: # i.e. the 1.9.1
        return True
    else:
        return False


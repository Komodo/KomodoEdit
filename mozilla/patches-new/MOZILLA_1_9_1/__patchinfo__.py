
"""Apply these patches to the Mozilla Mercurial 1.9.1 branch."""

def applicable(config):
    return hasattr(config, "mozVer") and config.mozVer == 1.91

def patchfile_applicable(config, filepath):
    if (filepath.endswith("xpcom_abort_threaded_cycle_collector.patch") or
        filepath.endswith("pyxpcom_crashreporter_log_last_call.patch")):
        # Apply this patch when not using a "blessed" build. Typcially blessed
        # builds are only used for official releases.
        return not hasattr(config, "blessed") or not config.blessed
    return True

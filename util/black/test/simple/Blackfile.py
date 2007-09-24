# Blackfile for project "simple"
#
# This project demonstrate the most basic use of Black: using it to
# generate configuration files containing only standard (i.e. built-in to
# Black) configuration items.
#
# Try this to see how it works:
#   > bk
#   ...shows help for this "hello" project...
#   > bk configure
#   ...configures the "hello" project (bkconfig.* are created)...
# These generated configuration files can be used for whatever build
# system is used to build "simple". As well, they are used by other standard
# Black commands.

import black.configure.std, black.configure.mozilla


# Define the configuration items for this project.
configuration = {
    # It is good practice to define a name and version for a project.
    "version": "0.1",
    "name": "simple",

    # Determine some system information about a Python installation that
    # might be useful for building later.
    # NOTE: The Black configuration mechanism is currently limited in
    #       that configuration items must be named the same as the 
    #       internal name used for the configuration item. I.e.,
    #         "pythonExeName" must be used for PythonExeName() because
    #         PythonExeName().name == "pythonExeName".
    "pythonExeName": black.configure.std.PythonExeName(),
    "pythonVersion": black.configure.std.PythonVersion(),
    "pythonInstallDir": black.configure.std.PythonInstallDir(),

    # Use the standard mozilla configuration module.
    # - "bk configure" will result in the default setting of
    #   "MOZILLA_OFFICIAL" in "bkconfig.{sh|bat}"
    # - "bk help configure" will show that the "--mozilla-official"
    #   option can be used to set the MOZILLA_OFFICIAL value
    # - Try "bk configure --mozilla-official=0" and see the result in
    #   "bkconfig.{sh|bat}".
    "MOZILLA_OFFICIAL": black.configure.mozilla.SetMozillaOfficial(),
}



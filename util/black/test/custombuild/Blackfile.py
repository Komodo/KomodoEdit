# Blackfile for project "custombuild"
#
#
# Currently Black has no ability to build a project. However,
# it can invoke a custom build procedure as expressed in the
# commandOverrides['build'] variable in a project Blackfile.py.
#
# This test project demonstrates how to do this.
#
# try running the following commands:
#   > bk
#   > bk configure
#   > bk                  # notice the change
#   > bk build
#   > bk build 42
#   > bk -v build 42
#

import os
import black, black.configure.std


# Define the configuration items for this project.
configuration = {
    # It is good practice to define a name and version for a project.
    "version": "0.1",
    "name": "simple",

    "perlBinDir": black.configure.std.PerlBinDir(),
}


# The custom build procedure.
def SayHello(projectConfig, argv):
    # a custom build procedure is launched "in" the project root directory
    print "the cwd is", os.getcwd()
    # a custom build procedure is passed the command line arg vector
    print "the command line args are", argv[1:]
    # the project configuration module (i.e. bkconfig.py) is passed in so the
    # routine can determine configuration items:
    #  - invoke perl using the configured Perl bin directory
    if len(argv[1:]) > 0:
        try:
            exitValue = int(argv[1])
        except ValueError:
            exitValue = 0
    else:
        exitValue = 0
    perlExe = os.path.join(projectConfig.perlBinDir, "perl")
    retval = os.system(''' %s -e "print 'hello'; exit(%d);" ''' %\
                       (perlExe, exitValue))
    # the standard black.BlackError exception can be raised, it
    # will be presented appropriately to the user
    if retval == 0:
        return retval
    else:   
        raise black.BlackError("unexpected return value: %s" % retval)

# override the Black "build" command
commandOverrides = {
    "build": SayHello,
}

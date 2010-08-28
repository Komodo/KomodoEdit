# To build this script into a PerlSvc, select:
#   Tools | Build Standalone Perl Application...
#
# Note: This functionality is only available if the Perl Dev Kit is
# installed. See: http://www.activestate.com/perl-dev-kit
#

package PerlSvc;
use strict;

# the short name by which your service will be known (cannot be 'my')
our $Name = "Example";
# the display name. This is the name that the Windows Control Panel
# will display (cannot be 'my')
our $DisplayName = "Example Service";

# the startup routine is called when the service starts
sub Startup {
    while (ContinueRun()) {
	# your service code goes in here
	sleep(5);
    }
}

sub Install {
    # add your additional install messages or functions here
    print "The $Name Service has been installed.\n";
    print "Start the service with the command: net start $Name\n";
}

sub Remove {
    # add your additional remove messages or functions here
    print "The $Name Service has been removed.\n";
}

sub Help {
    # add your additional help messages or functions here
    print "$Name Service -- add custom help message here.\n";
}


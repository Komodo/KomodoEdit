#!/usr/bin/perl -w

use strict;
use Tk;

# Create main window
my $main = MainWindow->new;

# Add a Label and a Button to main window
$main->Label(-text => 'Hello, world!')->pack;
$main->Button(-text => 'Quit',
	      -command => [$main => 'destroy']
	     )->pack;

# Spin the message loop
MainLoop;

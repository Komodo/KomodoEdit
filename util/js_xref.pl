#!perl
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

# JavaScript Cross Reference
#
# Searches through a list of JavaScript files, generating a report in some
# output format showing which files call which functions in which other files.
# The output format can be:
#  --text --> produces a textual cross reference report.
#  --dot  --> produces a file for feeding into the dot tool from
#             AT&T's graphviz project (www.graphviz.org), which produces
#             a graph visualization of the function calls.
#
# Run the script without any arguments for help on usage.

my $option = shift @ARGV;
if($option eq '--dot') {
    print STDERR "Generating dot file...\n";
    generate_dot();
}
elsif($option eq '--text') {
    print STDERR "Generating text report...\n";
    generate_text();
}
else {
    print STDERR "JavaScript Cross Reference Generator\n";
    print STDERR "Copyright (c) 2000-2006 ActiveState Software Inc.\n\n";
    print STDERR "Usage:\n";
    print STDERR "  $0 [--dot|--text] files...\n";
}

sub gen_xref() {
    my %functions = (); # FunctionDefn=>File
    my %calls = ();     # File=>Function
    my %files = ();     # File=>FunctionDefn
    my %revcalls = ();  # Function=>File
    my %callscalls = (); # Function=>Function
    my %classes = ();

    my $current_function = "";
    my $current_class = "";

    while(<>) {
        my $file = $ARGV;

        if(/(\w+)\.prototype\s*=/) {
            $current_class = $1;
        }
        elsif(/(\w+)\s*:\s*function\(/) {
            $current_function = $current_class . "::" . $1;
            $classes{$current_class}{$1}++;
        }
        
        elsif(/^\s*function\s+(\w+)\(/) {
            $current_function = $1;
            $functions{$current_function}{$file}++;
            $files{$file}{$current_function}++;
        }
        elsif(/[^.](\w+)\s*\(/) {
            $calls{$file}{$1}++;
            $revcalls{$1}{$file}++;
            $callscalls{$current_function}{$1}++;
        }
    }

    foreach $f1(sort keys %callscalls) {
        foreach $f2(sort keys %{$callscalls{$f1}}) {
            unless(exists $functions{$f2}) {
                delete $callscalls{$f1}{$f2};
            }
        }
    }

    return(\%functions, \%calls, \%files, \%revcalls, \%callscalls, \%classes);
}

sub generate_text () {
    my @foo = gen_xref();

    my %functions = %{shift(@foo)};
    my %calls = %{shift(@foo)};
    my %files = %{shift(@foo)};
    my %revcalls = %{shift(@foo)};

    print "JavaScript Cross Reference Report\n\n";

    print "Function Definitions:\n";
    foreach $filename(sort keys %files) {
        print "\nIn File: $filename\n";
        foreach $function(sort keys %{$files{$filename}}) {
            print "  $function" . "()\n";
        }
    }

    print "\n\nCalls to functions defined in local files:\n";
    foreach $filename(sort keys %calls) {
        print "From File: $filename\n";

        foreach $function (sort keys %{$calls{$filename}}) {
            if($functions{$function} &&
               !exists($functions{$function}{$filename})) {
                foreach(sort keys %{$functions{$function}}) {
                    print "  calls $function" . "() in file $_\n";
                }
            }
        }
    }
    
    print "\n\nPublic functions by file:\n";
    foreach $filename(sort keys %files) {
        print "File: $filename\n";
        
        foreach $function (sort keys %{$files{$filename}}) {
            if(exists $functions{$function}) {
                my @callers = keys %{$revcalls{$function}};
                if(scalar(@callers) > 1 ||
                   (scalar(@callers) == 1 && $callers[0] ne $filename)) {
                    print "  $function(): called from ";
                    print join(", ", sort(keys(%{$revcalls{$function}})));
                    print "\n";
                }
            }
        }
    }

    print "\n\nCalls to functions defined elsewhere... (or not at all!)\n";
    foreach $filename(sort keys %calls) {
        print "From File: $filename\n";

        foreach $function (sort keys %{$calls{$filename}}) {
            if(!$functions{$function}) {
                print "  calls $function" . "() in file $_\n";
            }
        }
    }
}

sub generate_dot() {
    my @foo = gen_xref();

    my %functions = %{shift(@foo)};
    my %calls = %{shift(@foo)};
    my %files = %{shift(@foo)};
    my %revcalls = %{shift(@foo)};
    my %callscalls = %{shift(@foo)};
    my %classes = %{shift(@foo)};

    print "digraph foo {\n";

#    foreach(sort keys %files) {
#        print "  \"$_\";\n";
#    }

    foreach $class(sort keys %classes) {
        print "  subgraph cluster_$class {\n";
        foreach $function(sort keys %{$classes{$class}}) {
            print "    \"$class" . "::" . "$function" . "()\";\n";
        }
        print "  }";
    }

    foreach $f1(sort keys %callscalls) {
        foreach $f2(sort keys %{$callscalls{$f1}}) {
            print "    \"$f1" . "()\"->" . "\"$f2" . "()\";\n";
        }
    }
    
#    foreach $filename(sort keys %calls) {
#        foreach $function (sort keys %{$calls{$filename}}) {
#            if($functions{$function} &&
#               !exists($functions{$function}{$filename})) {
#                foreach(sort keys %{$functions{$function}}) {
#                    print "    \"$filename:$function" . "()\"->" . "\"$_\";\n";
#                }
#            }
#        }
#    }

    print "}";
}



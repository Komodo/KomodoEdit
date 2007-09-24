#!perl
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

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



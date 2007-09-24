#
# ParseModule.pm - Modulized module parser
#
#
package ParseModule;

use strict;
use warnings;
use Tokenizer;
use ActiveState::Indenter;
# The indenter module currently in 
# //depot/main/Apps/PDK/src/ActiveState-Utils/lib/ActiveState/Indenter.pm
# and not buildable on Windows

my %packageNameParts;
$packageNameParts{+SCE_PL_WORD} = 1;
$packageNameParts{+SCE_PL_IDENTIFIER} = 1;

my %builtinVars = ('@ISA' => 1,
		   '@EXPORT' => 1,
		   '@EXPORT_OK' => 1,
		   );

my $indenter;

# It's a parser -- make these global.
my ($tkzr, $ttype, $tval);
my $showWarnings;

# Global Vars for gathering parsed data
my %moduleInfo;
my $thisNS;
my $thisParent;
my $thisFunction;
my $thisVar;
my $thisArg;

# Prototypes
sub isKeyword($$$);
sub isNameToken($);
sub isStmtEndOp($$);
sub warnAbout($);

sub doStartNS;
sub doEndNS;
sub doSetParent;
sub doStartFn;
sub doEndFn;
sub doSetVar;

sub addImportedModule;
sub collectMultipleArgs ($);
sub collectSingleArg($$);
sub getFQName();

sub getParentNamespaces();
sub getListOfVarNames();
sub getListOfStrings();
sub getStringArray($$$);
sub getOurVars();
sub getUsedVars();

sub processModule($);
sub processPackageInnerContents($);
sub processSubContents();
sub skipAnonSubContents ();
sub skipToEndOfStmt;

sub printDocInfo($);
sub printClassParents($);
sub printImports($);
sub printVariables($);
sub printFunctions($);
sub printContents($);
sub printHeader($);
sub printTrailer();

# ---------------- misc routines

sub isKeyword($$$) {
    my($ttype, $tval, $target) = @_;
    return 0 if $ttype != SCE_PL_WORD;
    return $tval eq $target;
}

sub isNameToken($) {
    return exists $packageNameParts{$_[0]};
}

sub isStmtEndOp($$) {
    my $ttype = shift;
    my $tval = shift;
    if ($ttype == SCE_PL_WORD && $tval eq 'or') { return 1 }
    elsif ($ttype == SCE_PL_OPERATOR) {
	return ($tval eq ';' || $tval eq '||');
    } else {
	return 0;
    }
}

sub warnAbout($) {
    my ($msg) = @_;
    if ($showWarnings) {
	$msg .= "\n" unless $msg =~ /\n$/;
	print STDERR $msg;
    }
}

# ---------------- info-gathering routines

sub doStartNS {
    my %attrInfo = @_;
    if (!$attrInfo{name}) {
	die "perlcile.pl: doStartNS: name not given";
    }
    my $name = $attrInfo{name};
    if ($thisNS = $moduleInfo{modules}{$name}) {
	# Do nothing, we've re-enabled it
    }
    else {
	$thisNS = { name => $name,
		    line => $attrInfo{lineNo} || 0,
		    aFunc => [],
		    aVar => [],
		    aParent => [],
		    aDocs => [],
		    aImports => [],
		};
	$moduleInfo{modules}{$name} = $thisNS;
    }
}

sub doEndNS {
    # Remove all args where the name is all caps
    @{$thisNS->{aFunc}} = grep { $_->{'name'} =~ /[_a-z]/} @{$thisNS->{aFunc}};
    my $modules = $moduleInfo{modules};
    my $nsName = $thisNS->{name};
    my $oldNSInfo = $modules->{$nsName};
    if ($oldNSInfo ne $thisNS) {
	# Processing a package that spans more than one area.
	push (@{$oldNSInfo->{aFunc}}, @{$thisNS->{aFunc}});
	push (@{$oldNSInfo->{aVar}}, @{$thisNS->{aVar}});
	push (@{$oldNSInfo->{aParent}}, @{$thisNS->{aParent}});
    }
    $thisNS = 0;
}

sub doSetParent {
    my %attrInfo = @_;
    if (my $ns = $attrInfo{'ns'}) {
	push @{$thisNS->{aParent}}, $ns;
    }
}

sub doStartFn {
    my %attrInfo = @_;
    $thisFunction = { name => $attrInfo{'name'},
		      aDocs => [],
		      aArg => [],
		      resultType => [],
		      };
    $thisFunction->{isConstructor} = 1 if $attrInfo{isConstructor};
    $thisFunction->{line} = $attrInfo{lineNo} if defined $attrInfo{lineNo};
}

sub doEndFn {
    push @{$thisNS->{'aFunc'}}, $thisFunction;
    $thisFunction = 0;
}


sub doSetVar {
    my %attrInfo = @_;
    $thisVar = {};
    if ($attrInfo{'name'}) {
	return if $builtinVars{$attrInfo{'name'}};
	$thisVar->{'name'} = $attrInfo{'name'};
    }
    foreach my $field (qw(column line type)) {
	$thisVar->{$field} = $attrInfo{$field} if defined $attrInfo{$field};
    }
    # Decide whether to put this in the 
    if ($thisFunction) {
	push @{$thisFunction->{'aArg'}}, $thisVar;
    }
    else {
	push @{$thisNS->{'aVar'}}, $thisVar;
    }
}

# ---------------- parse routines

sub addImportedModule {
    my $moduleName = shift;
    my $tlineNo = $tkzr->getCurrLineNo();
    
    #XXX: Further parsing to determine which names we're importing,
    # but this is hard to do with Perl (as hard as with Python's
    # from ... import *).
    
    if ($thisNS) {
	push @{$thisNS->{aImports}}, [$tval, $tlineNo];
    }
    skipToEndOfStmt();
}


sub collectMultipleArgs ($) {
    my $origLineNo = shift;
    
    # Get the list of names
    my @nameList;
    while (1) {
        ($ttype, $tval) = $tkzr->getNextToken();
        if (isVarName($ttype)) {
            push @nameList, [$tval, $tkzr->getCurrLineNo(),
			     $tkzr->getCurrCol($tval)];
        } else {
            last;
        }
        
        ($ttype, $tval) = $tkzr->getNextToken();
        if ($ttype == SCE_PL_OPERATOR) {
            if ($tval eq ")") { last; }
            elsif ($tval ne ",") { last; }
        }
    }
    
    return unless (isOp ($ttype, $tval, ")"));
    ($ttype, $tval) = $tkzr->getNextToken();
    
    return unless (isOp ($ttype, $tval, "="));
    ($ttype, $tval) = $tkzr->getNextToken();
    return unless (($ttype == SCE_PL_ARRAY) && ($tval eq '@_'));
    
    ($ttype, $tval) = $tkzr->getNextToken();
    if (isStmtEndOp($ttype, $tval)) {
	foreach my $varInfo (@nameList) {
	    doSetVar(name => $varInfo->[0],
		     line => $varInfo->[1],
		     column => $varInfo->[2]);
	}
    }         
}

# Expect = shift ;
sub collectSingleArg($$) {
    my $varName = shift;
    my $origLineNo = shift;
    my $column = $tkzr->getCurrCol($varName);

    # Expect an '='
    ($ttype, $tval) = $tkzr->getNextToken();
    return unless (isOp($ttype, $tval, "="));

    # Expect 'shift'
    ($ttype, $tval) = $tkzr->getNextToken();

    return unless (isKeyword($ttype, $tval, "shift"));
    doSetVar(name => $varName,
	     line => $origLineNo,
	     column => $column);
}


sub getFQName() {
    my $fqName = "";
    my $startingLineNo = -1;
    while (1) {
	($ttype, $tval) = $tkzr->getNextToken();
	if (isNameToken($ttype) || isOp ($ttype, $tval, '::')) {
	    $fqName .= $tval;
	    $startingLineNo = $tkzr->getCurrLineNo() if $startingLineNo == -1;
	} else {
	    $tkzr->putBack($ttype, $tval);
	    if (length($fqName) > 0) {
		return (SCE_PL_IDENTIFIER, $fqName, $startingLineNo);
	    } else {
		return ($ttype, $tval);
	    }
	}
    }
}

# Look for = stringList...
sub getParentNamespaces() {
    ($ttype, $tval) = $tkzr->getNextToken();
    return unless (isOp ($ttype, $tval, "="));
    ($ttype, $tval) = $tkzr->getNextToken();
    my @parentNamespaces = getListOfStrings();
    foreach my $parentInfo (@parentNamespaces) {
	push @{$thisNS->{aParent}}, $parentInfo;
    }
}

sub getListOfStrings() {
    my @resArray;
    if (isOp ($ttype, $tval, "(")) {
        while (1) {
            # Simple -- either a string or a qw here as well
            ($ttype, $tval) = $tkzr->getNextToken();
            if (isString($ttype)) {
                my @newArray;
                getStringArray(\@newArray, $ttype, $tval);
                push @resArray, @newArray;
            } else {
                last;
            }
            ($ttype, $tval) = $tkzr->getNextToken();
            if ($ttype == SCE_PL_OPERATOR ) {
                last if ($tval eq ')');
                next if ($tval eq ',');
                last; 
            }
        }
    }
    elsif (isString($ttype)) {
        getStringArray(\@resArray, $ttype, $tval);
    }
    return @resArray;
}


sub getListOfVarNames() {
    my @resArray;
    while (1) {
        ($ttype, $tval) = $tkzr->getNextToken();
        if (isVarName($ttype)) {
            push @resArray, [$tval, $tkzr->getCurrLineNo(),
			     $tkzr->getCurrCol($tval)];
        } else {
            last;
        }
        
        ($ttype, $tval) = $tkzr->getNextToken();
        last unless (isOp($ttype, $tval, ','));
    }
    return @resArray;
}


sub getStringArray($$$) {
    my ($res, $ttype, $tval) = @_;
    my $column = $tkzr->getCurrCol($tval);
    if ($ttype == SCE_PL_STRING) {
        $tval =~ s/^.(.*).$/$1/;
        push @$res, [$tval, $tkzr->getCurrLineNo(), $column];
    } elsif ($ttype == SCE_PL_STRING_Q) {
        $tval =~ s/^q.(.*).$/$1/;
        push @$res, [$tval, $tkzr->getCurrLineNo(), $column];
    } elsif ($ttype == SCE_PL_STRING_QQ) {
        $tval =~ s/^qq.(.*).$/$1/;
        push @$res, [$tval, $tkzr->getCurrLineNo(), $column];
    } elsif ($ttype == SCE_PL_STRING_QW) {
        $tval =~ s/^(qw.\s*)(.*)\s*.\s*$/$2/s;
        my $startPart = $1;
        my @tmp = split(/\s+/, $tval);
        my $lineNo = $tkzr->getCurrLineNo();
        foreach my $a (@tmp) {
	    push @$res, [$a, $lineNo,
			 $column + index($tval, $a) + length($startPart)];
        }
    }
}


sub getOurVars() {
    my @varNames;
    ($ttype, $tval) = $tkzr->getNextToken();
    if (isOp($ttype, $tval, "(")) {
        @varNames = getListOfVarNames();
    } elsif (isVarName($ttype)) {
        $tval =~ s/^\s*(.*?)\s*$/$1/;
        if ($tval eq '@ISA') {
            getParentNamespaces();
        } else {
	    @varNames =  ([$tval, $tkzr->getCurrLineNo(),
			   $tkzr->getCurrCol($tval)]);
        }
    }
    foreach my $varInfo (@varNames) {
	doSetVar(name => $varInfo->[0],
		 line => $varInfo->[1],
		 column => $varInfo->[2]);
    }
}

sub getUsedVars() {
    ($ttype, $tval) = $tkzr->getNextToken();
    my @varNames;
    if (isString($ttype) || isOp ($ttype, $tval, "(")) {
        @varNames = getListOfStrings();
    } else {
        @varNames = getListOfVarNames();
    }
    foreach my $varInfo (@varNames) {
	doSetVar(name => $varInfo->[0],
		 line => $varInfo->[1],
		 column => $varInfo->[2]);
    }
}

sub processModule($) {
    my ($moduleName) = @_;
    my $tOrigLineNo = $tkzr->getCurrLineNo();
    # Clean the info when parsing multiple input files.
    %moduleInfo = ();
    doStartNS('name' => 'main',
	      'lineNo' => $tOrigLineNo
	      );
    processPackageInnerContents(1);
    doEndNS();

    printHeader($moduleName);
    printContents($moduleName);
    printTrailer();
}


# This routine does package processing at both top-level as well as
# inner nested levels.

sub processPackageInnerContents($) {
    my $doingTopLevel = shift;
    my $currPackage = $thisNS->{name};
    my $popNS = 0;
    
    while (1) {
        ($ttype, $tval) = $tkzr->getNextToken();
	last if ($ttype == SCE_PL_UNUSED);
        if ($ttype == SCE_PL_WORD) {
	    if ($tval eq 'package') {
		my $packageName;
		($ttype, $packageName) = getFQName();
		if (length $packageName != 0) {
		    doEndNS();
		    doStartNS('name' => $packageName,
			      'lineNo' => $tkzr->getCurrLineNo(),
			      );
		    $popNS = 1;
		}
	    }
            elsif ($tval eq 'sub') {
		if (isOp ($ttype, $tval, '{')) {
		    $tkzr->putBack($ttype, $tval);
		    skipToEndOfStmt();
		} else {
		    my $startLineNo = $tkzr->getCurrLineNo();
		    ($ttype, $tval) = getFQName();
		    if ($packageNameParts{$ttype}) {
			my $fnName = $tval;
			if ($fnName =~ /^(.+)::([^:]+)$/) {
			    warnAbout("perlcile: processPackageInnerContents ignoring package part $1 for sub $2\n");
			    skipAnonSubContents();
			}
			else {
			    doStartFn(name => $fnName, lineNo => $startLineNo);
			    processSubContents();
			    doEndFn();
			}
		    } else {
			warnAbout("Type of $tval: $ttype");
		    }
		}
            } elsif ($tval =~ /^(BEGIN|END|AUTOLOAD)$/) {
                skipAnonSubContents();
            } elsif ($tval eq 'our') {
                getOurVars();
		
                # Small warning: vars defined at this lexical level belong to
		# the containing package, but are visible without
		# qualification in other packages in the same file.
                
            } elsif ($tval eq 'use') {
                # Watch out -- use in effect
                ($ttype, $tval) = getFQName();
                if ($ttype == SCE_PL_IDENTIFIER) {
                    if ($tval eq 'vars') {
                        getUsedVars();
		    } elsif ($tval =~ /^[a-z]+$/) {
			# Skip -- don't enter pragmata.
                    } else {
			addImportedModule($tval);
                    }
                }
            } else {
		skipToEndOfStmt();
	    }
        } elsif ($ttype == SCE_PL_ARRAY) {
            if ($tval eq '@ISA') {
                getParentNamespaces();
            }
	} elsif ($ttype eq SCE_PL_OPERATOR) {
	    if ($tval eq '{') {
		processPackageInnerContents(0);
	    } elsif ($tval eq '}') {
		if (!$doingTopLevel) {
		    if ($popNS) {
			doEndNS();
			doStartNS('name' => $currPackage);
		    }
		    last;
		}
	    }
        }
    }
}

sub processSubContents() {
    # Get to the open brace or semicolon (outside the parens)
    
    my $braceCount = 0;
    my $parenCount = 0;
    while (1) {
        ($ttype, $tval) = $tkzr->getNextToken();
        if ($ttype == SCE_PL_UNUSED) {
            return;
        }
        # Expect a paren for args, the open-brace, or a semi-colon
        if ($parenCount > 0) {
            $parenCount-- if ($ttype==SCE_PL_OPERATOR &&  $tval eq ')');
        } elsif ($ttype==SCE_PL_OPERATOR) {
            if ($tval eq '(') {
                ++$parenCount;
            } elsif ($tval eq '{') {
                $braceCount = 1;
                last;
            } elsif ($tval eq ';') {
                return;
            }
        }
    }
    
    # So now look for these different things:
    # '}' taking us to brace count of 0
    # my, name, =, shift;
    # my (..., ..., ...) = @_;
    # bless => mark this as a constructor
    # return => try to figure out what we're looking at    
    
    while (1) {
        ($ttype, $tval) = $tkzr->getNextToken();
        last if ($ttype == SCE_PL_UNUSED);

        if ($ttype == SCE_PL_OPERATOR) {
            if ($tval eq '{') { ++$braceCount }
            elsif ($tval eq '}') {
                --$braceCount;
                last if (!$braceCount);
            }
        } elsif ($ttype == SCE_PL_WORD) {
	    my $tlineNo = $tkzr->getCurrLineNo();
            if ($tval eq 'my') {
                ($ttype, $tval) = $tkzr->getNextToken();
                if (isOp($ttype, $tval, '(')) {
                    collectMultipleArgs($tlineNo);
                } elsif (isVarName($ttype)) {
                    collectSingleArg($tval, $tlineNo);
                    if (isOp($ttype, $tval, '{')) {
                        ++$braceCount;
                    }
                }
            } elsif ($tval eq 'bless') {
		$thisFunction->{'isConstructor'} = 1;
            } elsif ($tval eq 'return') {
                # If we return something of type (<(module)name ('::' name)*> "->" new)
                # Return an instance of type (module)
                # Either it returned an identifier, or it put the token back
                ($ttype, $tval) = getFQName();
                if ($ttype == SCE_PL_IDENTIFIER) {
                    my $subclass = $tval;
                    ($ttype, $tval) = $tkzr->getNextToken();
                    if ($tval ne '->') {
                        $tkzr->putBack($ttype, $tval);
                    } else {
                        ($ttype, $tval) = $tkzr->getNextToken();
                        if ($tval eq 'new') { 
			    if ($thisFunction) {
				push @{$thisFunction->{'resultType'}}, $subclass;
			    }
                        } else {
                            $tkzr->putBack($ttype, $tval);
                            $tkzr->putBack(SCE_PL_OPERATOR, '->');
                        }
                    }
                }
            } else {
		skipToEndOfStmt();
	    }
        }
    }
}

# If we're here, we want to use simple knowledge of Perl's syntax
# to skip quickly through code to the next item.

my %opHash = ("(" => [0, 1],
	      ")" => [0, -1],
	      "{" => [1, 1],
	      "}" => [1, -1],
	      "[" => [2, 1],
	      "]" => [2, -1]);

sub skipAnonSubContents () {
    ($ttype, $tval) = $tkzr->getNextToken();
    if (isOp ($ttype, $tval, '{')) {
	# Shouldn't find any nested packages, but we might.
	processPackageInnerContents(0);
    }
}


sub skipToEndOfStmt {
    my $nestedCount = 0;
    while (1) {
	($ttype, $tval) = $tkzr->getNextToken();
	if ($ttype == SCE_PL_UNUSED) {
	    last;
	}
	elsif ($ttype eq SCE_PL_OPERATOR) {
	    if ($opHash{$tval}) {
		my $vals = $opHash{$tval};
		if ($vals->[1] == 1) {
		    ++$nestedCount;
		}
		elsif (--$nestedCount <= 0) {
		    $nestedCount = 0;
		    if ($tval eq '}') {
			$tkzr->putBack($ttype, $tval);
			last;
		    }
		}
	    }
	    elsif (($tval eq ';') && !$nestedCount) {
		# Don't worry about commas, since they don't separate
		# declaration-type things.
		last;
	    }
	}
    }
}

# ---------------- print routines

sub printDocInfo($) {
    my ($modInfo) = @_;
    if (@{$modInfo->{aDocs}}) {
	$indenter->print(qq(<doc>));
	my @adocs = @{$modInfo->{aDocs}};
	my $docCountSub1 = scalar @adocs - 1;
	for (my $i = 0; ; $i++) {
	    $indenter->print(qq(<![CDATA[$adocs[$i]]]>));
	    if ($i < $docCountSub1) {
		$indenter->print("\n");
	    } else {
		last;
	    }
	}
	$indenter->print(qq(</doc>\n));
    }
}

sub printClassParents($) {
    my ($modInfo) = @_;
    return unless $modInfo->{aParent};
    foreach my $info (@{$modInfo->{aParent}}) {
	$indenter->print(qq(<classref name="$info->[0]">\n));
	$indenter->over();
	$indenter->print(qq(<type/>\n));
	$indenter->back();
	$indenter->print(qq(</classref>\n));
    }
}

sub printImports($) {
    my ($modInfo) = @_;
    return unless $modInfo->{aImports};
    foreach my $import (@{$modInfo->{aImports}}) {
	$indenter->print(qq(<import line="$import->[1]" module="$import->[0]"/>\n));
    }
}

sub printVariables($) {
    my ($modInfo) = @_;
    return unless $modInfo->{aVar};
    foreach my $varInfo (@{$modInfo->{aVar}}) {
	$indenter->print(qq(<variable line="$varInfo->{line}" name="$varInfo->{name}">\n));
	$indenter->over();
	$indenter->print(qq(<type/>\n));
	$indenter->back();
	$indenter->print(qq(</variable>\n));
    }
}

sub printFunctions($) {
    my ($modInfo) = @_;
    return unless $modInfo->{aFunc};
    my @functions = @{$modInfo->{aFunc}};
    foreach my $funcInfo (@functions) {
	$indenter->print(qq(<function name="$funcInfo->{name}"));
	$indenter->print(qq( line="$funcInfo->{line}")) if defined $funcInfo->{line};
	$indenter->print(qq( isConstructor="1")) if $funcInfo->{isConstructor};
	$indenter->print(qq(>\n));
	$indenter->over();
	$indenter->print(qq(<arguments>\n));
	$indenter->over();
	foreach my $argInfo (@{$funcInfo->{aArg}}) {
	    $indenter->print(qq(<variable name="$argInfo->{name}"));
	    my $line = $argInfo->{line};
	    if (defined $line) {
		$indenter->print(qq( line="$line"));
	    }
	    $indenter->print(">\n");
	    $indenter->over();
	    $indenter->print(qq(<type/>\n));
	    $indenter->back();
	    $indenter->print(qq(</variable>\n));
	}
	$indenter->back();
	$indenter->print(qq(</arguments>\n));
	$indenter->back();
	$indenter->print(qq(</function>\n));
    }
}

sub printContents($) {
    my ($moduleName) = @_;
    # Print the main part first, if there is one
    my $root;
    eval {
	require File::Basename;
	($root, undef, undef) = File::Basename::fileparse($moduleName, qr/\..*$/);
    };
    if (!$root) {
	($root) = ($moduleName =~ m@.*[/\\]([^/\\]+)(\.[^/\\]*)?$@);
	$root = $moduleName unless $root;
    }
    $indenter->print(qq(<module name="$root">\n));
    $indenter->over();

    my $mainInfo;
    if ($mainInfo = $moduleInfo{modules}{main}) {
	printDocInfo($mainInfo);
	printImports($mainInfo);
	printVariables($mainInfo);
    }
    
    # Do this to circumvent shared-iterator problem while debugging
    my @packages = keys %{$moduleInfo{modules}};
    my $innerModules = $moduleInfo{modules};
    @packages = sort { my $amod = $innerModules->{$a};
		       my $bmod = $innerModules->{$b};
		       if ($amod->{line} && $bmod->{line}) {
			   return $amod->{line} <=> $bmod->{line};
		       } else {
			   return $amod->{name} cmp $bmod->{name};
		       }
		   } @packages;
    foreach my $k (@packages) {
	next if $k eq 'main';
	my $modInfo = $moduleInfo{modules}{$k};
	$indenter->print(qq(<class name="$modInfo->{name}" line="$modInfo->{line}">\n));
	$indenter->over();
	printClassParents($modInfo);
	printDocInfo($modInfo);
	printImports($modInfo);
	printVariables($modInfo);
	printFunctions($modInfo);
	$indenter->back();
	$indenter->print(qq(</class>\n));
    }
    # And do main's functions after its classes
    if ($mainInfo) {
	printFunctions($mainInfo);
    }
    $indenter->back();
    $indenter->print(qq(</module>\n));
}

sub printHeader($) {
    my ($moduleName) = @_;
    $indenter->print(qq(<?xml version="1.0" encoding="UTF-8"?>\n));
    $indenter->print(qq(<codeintel version="0.1">\n));
    $indenter->over();
    
    my $modulePath = $moduleName;
    # For now just dump the base
    use File::Basename qw(fileparse);
    my($bname) = fileparse($moduleName, qr@\.+$@ );
    $indenter->print(qq(<file ));
    $indenter->over_cur();
    my $md5;
    eval {
	use Digest::MD5;
	my $ctx = Digest::MD5->new;
	my $fh;
	open $fh, "<", $moduleName or die "perlstile::ParseModule - Can't open file \"$moduleName\": $!";
	$ctx->addfile($fh);
	close $fh;
	$md5 = $ctx->b64digest;
    };
    if ($@) {
	$md5 = '????';
	warnAbout($@);
    }
	
    $indenter->print(qq(generator="Perl" language="Perl"\nmd5="$md5"));
    $indenter->soft_space();
    $indenter->print(qq(path="$moduleName">\n));
    $indenter->back();
    $indenter->over();
}

sub printTrailer() {
    $indenter->back();
    $indenter->print(qq(</file>\n));
    $indenter->back();
    $indenter->print(qq(</codeintel>\n));
}

# ---------------- Setup

sub new {
    my $invocant = shift;
    my $class = ref($invocant) || $invocant;
    my %options = @_;
    my $outFH = delete $options{output};
    $indenter = ActiveState::Indenter->new($outFH);
    die "Can't create an indenter object" unless $indenter;
    my $self = {
		useCache => 0,
		verbose => 0,
		%options
		};
    if (exists $self->{lexerLocation} && $self->{lexerLocation}) {
	use File::Basename;
	my $dirname = dirname($self->{lexerLocation});
    }
    else {
	die "ParseModule: No lexer location specified";
    }
    return bless $self, $class;
}

sub initTokenizer($) {
    my $self = shift;
    my $moduleName;
    if (!($moduleName = $self->{moduleName})) {
	$moduleName = shift;
	die "ParseModule::initTokenizer - no moduleName specified to parse" unless $moduleName;
	$self->{moduleName} = $moduleName;
    }
    my $tkzr = Tokenizer->initParser($moduleName, $self->{lexerLocation});
    if (!$tkzr) {
        die "ParseModule::initTokenizer - Can't init the tokenizer";
    }
    return $tkzr;
}

sub parse {
    my $self = shift;
    $tkzr = $self->initTokenizer();
    $showWarnings = $self->{showWarnings};
    processModule($self->{moduleName});
}

1;

package PerlModule;
use vars qw ($myscalar @myarray %myhash);
require Exporter;
@ISA = qw(Exporter);
@EXPORT = qw(myfunc $myscalar @myarray %myhash);
@EXPORT_OK = qw();
%EXPORT_TAGS = (all => [ @EXPORT_OK, @EXPORT ]);

sub myfunc {
    my ($a, $b) = @_;
}

$myscalar = 42;
@myarray = ('a', 'b', 'c');
%myhash = ('one'=>1, 'two'=>2, 'three'=>3);


package PerlModule::SubModule;
use vars qw ($subscalar @subarray %subhash);
require Exporter;
@ISA = qw(Exporter);
@EXPORT = qw(subfunc $subscalar @subarray %subhash);
@EXPORT_OK = qw();
%EXPORT_TAGS = (all => [ @EXPORT_OK, @EXPORT ]);

sub subfunc {
    my ($a, $b) = @_;
}

$subscalar = 42;
@subarray = ('a', 'b', 'c');
%subhash = ('one'=>1, 'two'=>2, 'three'=>3);

1;

# To build this script into a PerlCtrl, select:
#   Tools | Build Standalone Perl Application...
# After it is built, the control must be registered using:
#   regsvr32 <PDK - PerlCtrl>.dll
#
# Note: This functionality is only available if the Perl Dev Kit is
# installed. See: http://www.activestate.com/perl-dev-kit
#
# The Hello method is included as a sample of how to specify method
# signatures for the PerlCOM compiler. The pod documentation is
# essential for the perlCOM compiler to build a proper COM dll. See the
# PDK documentation for more details.

package MyPackage;
use strict;

# Properties
our $Name = "Me";

# Methods
sub Hello {
    return "$Name says: Hello, World";
}


=pod

=begin PerlCtrl

    %TypeLib = (
        PackageName     => 'MyPackage::MyName',
        TypeLibGUID     => '{[[%guid]]}', # do NOT edit this line
        ControlGUID     => '{[[%guid]]}', # do NOT edit this line either
        DispInterfaceIID=> '{[[%guid]]}', # or this one
        ControlName     => 'MyObject',
        ControlVer      => 1,  # increment if new object with same ProgID
                               # create new GUIDs as well
        ProgID          => 'MyApp.MyObject',
        LCID            => 0,
        DefaultMethod   => 'MyMethodName1',
        Methods         => {
            MyMethodName1 => {
                DispID              =>  0,
                RetType             =>  VT_I4,
                TotalParams         =>  5,
                NumOptionalParams   =>  2,
                ParamList           =>[ ParamName1 => VT_I4,
                                        ParamName2 => VT_BSTR,
                                        ParamName3 => VT_BOOL,
                                        ParamName4 => VT_I4,
                                        ParamName5 => VT_UI1 ],
            },
            MyMethodName2 => {
                DispID              =>  1,
                RetType             =>  VT_I4,
                TotalParams         =>  2,
                NumOptionalParams   =>  0,
                ParamList           =>[ ParamName1 => VT_I4,
                                        ParamName2 => VT_BSTR ],
            },
        },  # end of 'Methods'
        Properties        => {
            MyIntegerProp => {
                DispID            => 2,
                Type              => VT_I4,
                ReadOnly          => 0,
            },
            MyStringProp => {
                DispID            => 3,
                Type              => VT_BSTR,
                ReadOnly          => 0,
            },
            Color => {
                DispID            => 4,
                Type              => VT_BSTR,
                ReadOnly          => 0,
            },
            MyReadOnlyIntegerProp => {
                DispID            => 5,
                Type              => VT_I4,
                ReadOnly          => 1,
            },
        },  # end of 'Properties'
    );  # end of %TypeLib

=end PerlCtrl

=cut

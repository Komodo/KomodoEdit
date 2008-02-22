// Cile test cases for properly handling function arguments, see bug:
// http://bugs.activestate.com/show_bug.cgi?id=75068

function function_args_bug75068(xyz){
        xyz=0;
        function b(){
                xyz=1;
        }
}

// Cile tests for bug:
// http://bugs.activestate.com/show_bug.cgi?id=75068

//case 1:
function case1(){
        var case1_xyz;
        var c=(function b(){
                case1_xyz=2;
        })
}

//case 2:
function case2(){
        var case2_xyz;
        func(function(){
                case2_xyz=2;
        })
}

//case 3:
function case3(case3_xyz){
        var b=(function(){
                function(){
                        case3_xyz = 1;
                }
        })();
}


###
##
#
#### The first subprocess is the fast multiplication script
#### from the profiling tutorial.
#
##
###

proc multiply {n m} {
    set res 0
    while {$n > 0} {
	if {($n % 2) == 1} {
	    incr n -1
	    incr res $m
	} else {
	    set n [expr {$n/2}]
	    incr m $m
	}
    }
    return $res
}

##
## Try the multiply command with various arguments.
##

puts "    2 x  3 = [multiply     2  3]"
puts "    5 x  2 = [multiply     5  2]"
puts " 5000 x 20 = [multiply  5000 20]"
puts "10000 x 10 = [multiply 10000 10]"

exit

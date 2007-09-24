
###
##
#
#### Spawning and debugging a subprocess.
#
##
###

# Simple command to spawn a tcl based subprocess.

# Name and signature (have to) match the definition of ats_run found in
# ats_run.pdx (Wrapped in the debugger. Use tclvfse to look at this
# file, it is not byte-compiled). The functionality has to match too.

proc ats_run {cmd args} {
    return [eval [linsert $args 0 \
	    exec [info nameofexecutable] $cmd]]
}

puts "Running the profiled multipliers in parallel"

ats_run [file join [file dirname [info script]] subprocess1.tcl]
ats_run [file join [file dirname [info script]] subprocess2.tcl]

puts "Launch complete"

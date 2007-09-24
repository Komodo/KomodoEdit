
set string {
	proc foo {a} {
		puts $a
	}
}

eval $string
foo 5


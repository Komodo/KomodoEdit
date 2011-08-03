
namespace eval ::foo {

    variable a {}
    proc glibber {} {}

    namespace eval bar {
	variable d 1

	proc snarf {} {}
    }
}

global f
set f 2

proc a {} {}

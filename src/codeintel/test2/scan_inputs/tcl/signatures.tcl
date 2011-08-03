
proc a {} {}
proc b {args} {}
proc c {d e f} {}
proc d {a args} {}
proc e {a args b} {}
proc f {a b {c {}}} {}
proc g {a b {c barf}} {}
proc h {a b {c barf} args} {}
proc i {a b args {c barf}} {}

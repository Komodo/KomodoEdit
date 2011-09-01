proc inner {item} {
    if {[regexp -- \{ $item]} {
    }
}

proc inner2 {item} {
    switch -- item {
        "If" { regexp -lineanchor -- "moo\{" thing }
        "What" {
            if {1} {
                puts \{
            } else {
                puts \[
            }
        }
    }
    if {[regexp -- \{ $item]} {
    }
}

proc main {args} {
}
main $argv

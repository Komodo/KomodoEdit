#!/bin/sh
# -*- tcl -*-
# The next line is executed by /bin/sh, but not tcl \
exec tclsh "$0" ${1+"$@"}

# Framework for the creation of a socket based server. The code makes
# no assumptions about the actual protocol being run. It just sets up
# the machinery for accepting connections and handling requests via
# file events. The tcllib log module is used to introspect on the
# activity of the framework.

# Slot the custom functionality of your system into the definitions of
# following procedures:
#
# [port]   - Return the port number the server is starting from
#
# [handle] - Called whenever data arrives, behaviour is custom to the
#            actual protocol
#
# Configure the log module to suppress or enable logging, to redirect
# the generated logs, to post-process the log inside of the server.

# Notes:
# - Change [accept] and/or [handle] to implement access control.
# - Change [accept] and/or [handle] to reconfigure the channel when
#   necessary for the actual protocol (encoding, translation, ...)

#################################################################

package require log ; # tcllib/log - logging of internal behaviour

proc main {} {
    start_server [port]

    # Enter event loop, will stop when global variable "forever" is
    # written to.

    vwait ::forever
    return
}

proc start_server {port} {
    log::log debug "[info level 0]"

    socket -server [list accept $port] $port

    log::log debug "[info level 0], accepting requests ..."
    return
}

proc accept {serverport channel host port} {
    log::log debug "[info level 0]"

    fconfigure $channel -blocking 0
    fileevent  $channel readable \
	    [list collect $serverport $channel $host $port]

    log::log debug "[info level 0], new connection ready"
    return
}

proc collect {serverport channel host port} {
    set data [read $channel]
    set bl   [string bytelength $data]

    if {$bl > 0} {
	log::log debug "[info level 0], handling $bl bytes"
	handle $data $serverport $channel $host $port
    }

    if {[eof $channel]} {
	log::log debug "[info level 0], eof, closing connection"
	close $channel
    }

    return
}

#################################################################
#
# Define custom functionality ...

proc port {} {
    # Return the port the server shall listen on
    return -code error "Not implemented"
}

proc handle {data serverport channel host port} {
    # Process the incoming data according to the actually implemented
    # protocol
    return -code error "Not implemented"
}

#
#
#################################################################
#

main

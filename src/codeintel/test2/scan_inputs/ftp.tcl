# ftp.tcl --
#
#	FTP library package for Tcl 8.2+.  Originally written by Steffen
#	Traeger (Steffen.Traeger@t-online.de); modified by Peter MacDonald
#	(peter@pdqi.com) to support multiple simultaneous FTP sessions;
#	Modified by Steve Ball (Steve.Ball@zveno.com) to support
#	asynchronous operation.
#
# Copyright (c) 1996-1999 by Steffen Traeger <Steffen.Traeger@t-online.de>
# Copyright (c) 2000 by Ajuba Solutions
# Copyright (c) 2000 by Zveno Pty Ltd
#
# See the file "license.terms" for information on usage and redistribution
# of this file, and for a DISCLAIMER OF ALL WARRANTIES.
# 
# RCS: @(#) $Id: ftp.tcl,v 1.37 2004/01/25 07:29:40 andreas_kupries Exp $
#
#   core ftp support: 	ftp::Open <server> <user> <passwd> <?options?>
#			ftp::Close <s>
#			ftp::Cd <s> <directory>
#			ftp::Pwd <s>
#			ftp::Type <s> <?ascii|binary|tenex?>	
#			ftp::List <s> <?directory?>
#			ftp::NList <s> <?directory?>
#			ftp::FileSize <s> <file>
#			ftp::ModTime <s> <file> <?newtime?>
#			ftp::Delete <s> <file>
#			ftp::Rename <s> <from> <to>
#			ftp::Put <s> <(local | -data "data" -channel chan)> <?remote?>
#			ftp::Append <s> <(local | -data "data" | -channel chan)> <?remote?>
#			ftp::Get <s> <remote> <?(local | -variable varname | -channel chan)?>
#			ftp::Reget <s> <remote> <?local?>
#			ftp::Newer <s> <remote> <?local?>
#			ftp::MkDir <s> <directory>
#			ftp::RmDir <s> <directory>
#			ftp::Quote <s> <arg1> <arg2> ...
#
# Internal documentation. Contents of a session state array.
#
# ---------------------------------------------
# key             value
# ---------------------------------------------
# State           Current state of the session and the currently executing command.
# RemoteFileName  Name of the remote file, for put/get
# LocalFileName   Name of local file, for put/get
# inline          1 - Put/Get is inline (from data, to variable)
# filebuffer  
# PutData         Data to move when inline
# SourceCI        Channel to read from, "Put"
# ---------------------------------------------
#

package require Tcl 8.2
package require log     ; # tcllib/log, general logging facility.

namespace eval ::ftp {
    namespace export DisplayMsg Open Close Cd Pwd Type List NList \
	    FileSize ModTime Delete Rename Put Append Get Reget \
	    Newer Quote MkDir RmDir

    set serial 0
    set VERBOSE 0
    set DEBUG 0
}

#############################################################################
#
# DisplayMsg --
#
# This is a simple procedure to display any messages on screen.
# Can be intercepted by the -output option to Open
#
#	namespace ftp {
#		proc DisplayMsg {msg} {
#			......
#		}
#	}
#
# Arguments:
# msg - 		message string
# state -		different states {normal, data, control, error}
#
proc ::ftp::DisplayMsg {s msg {state ""}} {

    upvar ::ftp::ftp$s ftp

    if { ([info exists ftp(Output)]) && ($ftp(Output) != "") } {
        eval [concat $ftp(Output) {$s $msg $state}]
        return
    }

    # FIX #476729. Instead of changing the documentation this
    #              procedure is changed to enforce the documented
    #              behaviour. IOW, this procedure will not throw
    #              errors anymore. At the same time printing to stdout
    #              is exchanged against calls into the 'log' module
    #              tcllib, which is much easier to customize for the
    #              needs of any application using the ftp module. The
    #              variable VERBOSE is still relevant as it controls
    #              whether this procedure is called or not.

    switch -exact -- $state {
        data    {log::log debug "$state | $msg"}
        control {log::log debug "$state | $msg"}
        error   {log::log error "$state | E: $msg"}
        default {log::log debug "$state | $msg"}
    }
    return
}

#############################################################################
#
# Timeout --
#
# Handle timeouts
# 
# Arguments:
#  -
#
proc ::ftp::Timeout {s} {
    upvar ::ftp::ftp$s ftp

    after cancel $ftp(Wait)
    set ftp(state.control) 1

    DisplayMsg "" "Timeout of control connection after $ftp(Timeout) sec.!" error
    Command $ftp(Command) timeout
    return
}

#############################################################################
#
# WaitOrTimeout --
#
# Blocks the running procedure and waits for a variable of the transaction 
# to complete. It continues processing procedure until a procedure or 
# StateHandler sets the value of variable "finished". 
# If a connection hangs the variable is setting instead of by this procedure after 
# specified seconds in $ftp(Timeout).
#  
# 
# Arguments:
#  -		
#

proc ::ftp::WaitOrTimeout {s} {
    upvar ::ftp::ftp$s ftp

    set retvar 1

    if { ![string length $ftp(Command)] && [info exists ftp(state.control)] } {

        set ftp(Wait) [after [expr {$ftp(Timeout) * 1000}] [list [namespace current]::Timeout $s]]

        vwait ::ftp::ftp${s}(state.control)
        set retvar $ftp(state.control)
    }

    if {$ftp(Error) != ""} {
        set errmsg $ftp(Error)
        set ftp(Error) ""
        DisplayMsg $s $errmsg error
    }

    return $retvar
}

#############################################################################
#
# WaitComplete --
#
# Transaction completed.
# Cancel execution of the delayed command declared in procedure WaitOrTimeout.
# 
# Arguments:
# value -	result of the transaction
#			0 ... Error
#			1 ... OK
#

proc ::ftp::WaitComplete {s value} {
    upvar ::ftp::ftp$s ftp

    if {![info exists ftp(Command)]} {
	set ftp(state.control) $value
	return $value
    }
    if { ![string length $ftp(Command)] && [info exists ftp(state.data)] } {
        vwait ::ftp::ftp${s}(state.data)
    }

    catch {after cancel $ftp(Wait)}
    set ftp(state.control) $value
    return $ftp(state.control)
}

#############################################################################
#
# PutsCtrlSocket --
#
# Puts then specified command to control socket,
# if DEBUG is set than it logs via DisplayMsg
# 
# Arguments:
# command - 		ftp command
#

proc ::ftp::PutsCtrlSock {s {command ""}} {
    upvar ::ftp::ftp$s ftp
    variable DEBUG
	
    if { $DEBUG } {
        DisplayMsg $s "---> $command"
    }

    puts $ftp(CtrlSock) $command
    flush $ftp(CtrlSock)
    return
}

#############################################################################
#
# StateHandler --
#
# Implements a finite state handler and a fileevent handler
# for the control channel
# 
# Arguments:
# sock - 		socket name
#			If called from a procedure than this argument is empty.
# 			If called from a fileevent than this argument contains
#			the socket channel identifier.

proc ::ftp::StateHandler {s {sock ""}} {
    upvar ::ftp::ftp$s ftp
    variable DEBUG 
    variable VERBOSE

    # disable fileevent on control socket, enable it at the and of the state machine
    # fileevent $ftp(CtrlSock) readable {}
		
    # there is no socket (and no channel to get) if called from a procedure

    set rc "   "
    set msgtext {}

    if { $sock != "" } {

        set number [gets $sock bufline]

        if { $number > 0 } {

            # get return code, check for multi-line text
            
            if {![regexp -- "^-?(\[0-9\]+)( |-)?(.*)$" $bufline all rc multi_line msgtext]} {
		set errmsg "C: Internal Error @ line 255.\
			Regex pattern not matching the input \"$bufline\""
		if {$VERBOSE} {
		    DisplayMsg $s $errmsg control
		}
	    } else {
		set buffer $bufline
			
		# multi-line format detected ("-"), get all the lines
		# until the real return code

		while { [string equal $multi_line "-"] } {
		    set number [gets $sock bufline]	
		    if { $number > 0 } {
			append buffer \n "$bufline"
			regexp -- "(^\[0-9\]+)( |-)?(.*)$" $bufline all rc multi_line
		    }
		}
	    }
        } elseif { [eof $ftp(CtrlSock)] } {
            # remote server has closed control connection
            # kill control socket, unset State to disable all following command
            
            set rc 421
            if { $VERBOSE } {
                DisplayMsg $s "C: 421 Service not available, closing control connection." control
            }
            set ftp(Error) "Service not available!"
            CloseDataConn $s
            WaitComplete $s 0
	    Command $ftp(Command) terminated
            catch {unset ftp(State)}
            catch {close $ftp(CtrlSock); unset ftp(CtrlSock)}
            return
        } else {
	    # Fix SF bug #466746: Incomplete line, do nothing.
	    return	   
	}
    } 
	
    if { $DEBUG } {
        DisplayMsg $s "-> rc=\"$rc\"\n-> msgtext=\"$msgtext\"\n-> state=\"$ftp(State)\""
    }

    # In asynchronous mode, should we move on to the next state?
    set nextState 0
	
    # system status replay
    if { [string equal $rc "211"] } {
        return
    }

    # use only the first digit 
    regexp -- "^\[0-9\]?" $rc rc
	
    switch -exact -- $ftp(State) {
        user { 
            switch -exact -- $rc {
                2 {
                    PutsCtrlSock $s "USER $ftp(User)"
                    set ftp(State) passwd
		    Command $ftp(Command) user
                }
                default {
                    set errmsg "Error connecting! $msgtext"
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        passwd {
            switch -exact -- $rc {
                2 {
                    set complete_with 1
		    Command $ftp(Command) password
                }
                3 {
                    PutsCtrlSock $s "PASS $ftp(Passwd)"
                    set ftp(State) connect
		    Command $ftp(Command) password
                }
                default {
                    set errmsg "Error connecting! $msgtext"
                    set complete_with 0
		    Command $ftp(Command) error $msgtext
                }
            }
        }
        connect {
            switch -exact -- $rc {
                2 {
		    # The type is set after this, and we want to report
		    # that the connection is complete once the type is done
		    set nextState 1
		    if {[info exists ftp(NextState)] && ![llength $ftp(NextState)]} {
			Command $ftp(Command) connect $s
		    } else {
			set complete_with 1
		    }
                }
                default {
                    set errmsg "Error connecting! $msgtext"
                    set complete_with 0
		    Command $ftp(Command) error $msgtext
                }
            }
        }   
	connect_last {
	    Command $ftp(Command) connect $s
	    set complete_with 1
	}
        quit {
            PutsCtrlSock $s "QUIT"
            set ftp(State) quit_sent
        }
        quit_sent {
            switch -exact -- $rc {
                2 {
                    set complete_with 1
		    set nextState 1
		    Command $ftp(Command) quit
                }
                default {
                    set errmsg "Error disconnecting! $msgtext"
                    set complete_with 0
		    Command $ftp(Command) error $msgtext
                }
            }
        }
        quote {
            PutsCtrlSock $s $ftp(Cmd)
            set ftp(State) quote_sent
        }
        quote_sent {
            set complete_with 1
            set ftp(Quote) $buffer
	    set nextState 1
	    Command $ftp(Command) quote $buffer
        }
        type {
            if { [string equal $ftp(Type) "ascii"] } {
                PutsCtrlSock $s "TYPE A"
            } elseif { [string equal $ftp(Type) "binary"] } {
                PutsCtrlSock $s "TYPE I"
            } else {
                PutsCtrlSock $s "TYPE L"
            }
            set ftp(State) type_sent
        }
        type_sent {
            switch -exact -- $rc {
                2 {
                    set complete_with 1
		    set nextState 1
		    Command $ftp(Command) type $ftp(Type)
                }
                default {
                    set errmsg "Error setting type \"$ftp(Type)\"!"
                    set complete_with 0
		    Command $ftp(Command) error "error setting type \"$ftp(Type)\""
                }
            }
        }
	type_change {
	    set ftp(Type) $ftp(type:changeto)
	    set ftp(State) type
	    StateHandler $s
	}
        nlist_active {
            if { [OpenActiveConn $s] } {
                PutsCtrlSock $s "PORT $ftp(LocalAddr),$ftp(DataPort)"
                set ftp(State) nlist_open
            } else {
                set errmsg "Error setting port!"
            }
        }
        nlist_passive {
            PutsCtrlSock $s "PASV"
            set ftp(State) nlist_open
        }
        nlist_open {
            switch -exact -- $rc {
                1 {}
		2 {
                    if { [string equal $ftp(Mode) "passive"] } {
                        if { ![OpenPassiveConn $s $buffer] } {
                            set errmsg "Error setting PASSIVE mode!"
                            set complete_with 0
			    Command $ftp(Command) error "error setting passive mode"
                        }
                    }   
                    PutsCtrlSock $s "NLST$ftp(Dir)"
                    set ftp(State) list_sent
                }
                default {
                    if { [string equal $ftp(Mode) "passive"] } {
                        set errmsg "Error setting PASSIVE mode!"
                    } else {
                        set errmsg "Error setting port!"
                    }  
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        list_active {
            if { [OpenActiveConn $s] } {
                PutsCtrlSock $s "PORT $ftp(LocalAddr),$ftp(DataPort)"
                set ftp(State) list_open
            } else {
                set errmsg "Error setting port!"
		Command $ftp(Command) error $errmsg
            }
        }
        list_passive {
            PutsCtrlSock $s "PASV"
            set ftp(State) list_open
        }
        list_open {
            switch -exact -- $rc {
                1 {}
		2 {
                    if { [string equal $ftp(Mode) "passive"] } {
                        if { ![OpenPassiveConn $s $buffer] } {
                            set errmsg "Error setting PASSIVE mode!"
                            set complete_with 0
			    Command $ftp(Command) error $errmsg
                        }
                    }   
                    PutsCtrlSock $s "LIST$ftp(Dir)"
                    set ftp(State) list_sent
                }
                default {
                    if { [string equal $ftp(Mode) "passive"] } {
                        set errmsg "Error setting PASSIVE mode!"
                    } else {
                        set errmsg "Error setting port!"
                    }  
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        list_sent {
            switch -exact -- $rc {
                1 -
		2 {
                    set ftp(State) list_close
                }
                default {  
                    if { [string equal $ftp(Mode) "passive"] } {
                        unset ftp(state.data)
                    }    
                    set errmsg "Error getting directory listing!"
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        list_close {
            switch -exact -- $rc {
                1 {}
		2 {
		    set nextState 1
		    if {[info exists ftp(NextState)] && ![llength $ftp(NextState)]} {
			Command $ftp(Command) list [ListPostProcess $ftp(List)]
		    } else {
			set complete_with 1
		    }
                }
                default {
                    set errmsg "Error receiving list!"
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
	list_last {
	    Command $ftp(Command) list [ListPostProcess $ftp(List)]
	    set complete_with 1
	}
        size {
            PutsCtrlSock $s "SIZE $ftp(File)"
            set ftp(State) size_sent
        }
        size_sent {
            switch -exact -- $rc {
                2 {
                    regexp -- "^\[0-9\]+ (.*)$" $buffer all ftp(FileSize)
                    set complete_with 1
		    set nextState 1
		    Command $ftp(Command) size $ftp(File) $ftp(FileSize)
                }
                default {
                    set errmsg "Error getting file size!"
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        } 
        modtime {
            if {$ftp(DateTime) != ""} {
              PutsCtrlSock $s "MDTM $ftp(DateTime) $ftp(File)"
            } else { ;# No DateTime Specified
              PutsCtrlSock $s "MDTM $ftp(File)"
            }
            set ftp(State) modtime_sent
        }  
        modtime_sent {
            switch -exact -- $rc {
                2 {
                    regexp -- "^\[0-9\]+ (.*)$" $buffer all ftp(DateTime)
                    set complete_with 1
		    set nextState 1
		    Command $ftp(Command) modtime $ftp(File) [ModTimePostProcess $ftp(DateTime)]
                }
                default {
                    if {$ftp(DateTime) != ""} {
                      set errmsg "Error setting modification time! No server MDTM support?"
                    } else {
                      set errmsg "Error getting modification time!"
                    }
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        } 
        pwd {
            PutsCtrlSock $s "PWD"
            set ftp(State) pwd_sent
        }
        pwd_sent {
            switch -exact -- $rc {
                2 {
                    regexp -- "^.*\"(.*)\"" $buffer temp ftp(Dir)
                    set complete_with 1
		    set nextState 1
		    Command $ftp(Command) pwd $ftp(Dir)
                }
                default {
                    set errmsg "Error getting working dir!"
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        cd {
            PutsCtrlSock $s "CWD$ftp(Dir)"
            set ftp(State) cd_sent
        }
        cd_sent {
            switch -exact -- $rc {
                1 {}
		2 {
                    set complete_with 1
		    set nextState 1
		    Command $ftp(Command) cd $ftp(Dir)
                }
                default {
                    set errmsg "Error changing directory to \"$ftp(Dir)\""
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        mkdir {
            PutsCtrlSock $s "MKD $ftp(Dir)"
            set ftp(State) mkdir_sent
        }
        mkdir_sent {
            switch -exact -- $rc {
                2 {
                    set complete_with 1
		    set nextState 1
		    Command $ftp(Command) mkdir $ftp(Dir)
                }
                default {
                    set errmsg "Error making dir \"$ftp(Dir)\"!"
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        rmdir {
            PutsCtrlSock $s "RMD $ftp(Dir)"
            set ftp(State) rmdir_sent
        }
        rmdir_sent {
            switch -exact -- $rc {
                2 {
                    set complete_with 1
		    set nextState 1
		    Command $ftp(Command) rmdir $ftp(Dir)
                }
                default {
                    set errmsg "Error removing directory!"
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        delete {
            PutsCtrlSock $s "DELE $ftp(File)"
            set ftp(State) delete_sent
        }
        delete_sent {
            switch -exact -- $rc {
                2 {
                    set complete_with 1
		    set nextState 1
		    Command $ftp(Command) delete $ftp(File)
                }
                default {
                    set errmsg "Error deleting file \"$ftp(File)\"!"
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        rename {
            PutsCtrlSock $s "RNFR $ftp(RenameFrom)"
            set ftp(State) rename_to
        }
        rename_to {
            switch -exact -- $rc {
                3 {
                    PutsCtrlSock $s "RNTO $ftp(RenameTo)"
                    set ftp(State) rename_sent
                }
                default {
                    set errmsg "Error renaming file \"$ftp(RenameFrom)\"!"
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        rename_sent {
            switch -exact -- $rc {
                2 {
                    set complete_with 1
		    set nextState 1
		    Command $ftp(Command) rename $ftp(RenameFrom) $ftp(RenameTo)
                }
                default {
                    set errmsg "Error renaming file \"$ftp(RenameFrom)\"!"
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        put_active {
            if { [OpenActiveConn $s] } {
                PutsCtrlSock $s "PORT $ftp(LocalAddr),$ftp(DataPort)"
                set ftp(State) put_open
            } else {
                set errmsg "Error setting port!"
		Command $ftp(Command) error $errmsg
            }
        }
        put_passive {
            PutsCtrlSock $s "PASV"
            set ftp(State) put_open
        }
        put_open {
            switch -exact -- $rc {
                1 -
		2 {
                    if { [string equal $ftp(Mode) "passive"] } {
                        if { ![OpenPassiveConn $s $buffer] } {
                            set errmsg "Error setting PASSIVE mode!"
                            set complete_with 0
			    Command $ftp(Command) error $errmsg
                        }
                    } 
                    PutsCtrlSock $s "STOR $ftp(RemoteFilename)"
                    set ftp(State) put_sent
                }
                default {
                    if { [string equal $ftp(Mode) "passive"] } {
                        set errmsg "Error setting PASSIVE mode!"
                    } else {
                        set errmsg "Error setting port!"
                    }  
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        put_sent {
            switch -exact -- $rc {
                1 -
		2 {
                    set ftp(State) put_close
                }
                default {
                    if { [string equal $ftp(Mode) "passive"] } {
                        # close already opened DataConnection
                        unset ftp(state.data)
                    }  
                    set errmsg "Error opening connection!"
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        put_close {
            switch -exact -- $rc {
		1 {
		    # Keep going
		    return
		}
                2 {
                    set complete_with 1
		    set nextState 1
		    Command $ftp(Command) put $ftp(RemoteFilename)
                }
                default {
		    DisplayMsg $s "rc = $rc msgtext = \"$msgtext\""
                    set errmsg "Error storing file \"$ftp(RemoteFilename)\" due to \"$msgtext\""
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        append_active {
            if { [OpenActiveConn $s] } {
                PutsCtrlSock $s "PORT $ftp(LocalAddr),$ftp(DataPort)"
                set ftp(State) append_open
            } else {
                set errmsg "Error setting port!"
		Command $ftp(Command) error $errmsg
            }
        }
        append_passive {
            PutsCtrlSock $s "PASV"
            set ftp(State) append_open
        }
        append_open {
            switch -exact -- $rc {
		1 -
                2 {
                    if { [string equal $ftp(Mode) "passive"] } {
                        if { ![OpenPassiveConn $s $buffer] } {
                            set errmsg "Error setting PASSIVE mode!"
                            set complete_with 0
			    Command $ftp(Command) error $errmsg
                        }
                    }   
                    PutsCtrlSock $s "APPE $ftp(RemoteFilename)"
                    set ftp(State) append_sent
                }
                default {
                    if { [string equal $ftp(Mode) "passive"] } {
                        set errmsg "Error setting PASSIVE mode!"
                    } else {
                        set errmsg "Error setting port!"
                    }  
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        append_sent {
            switch -exact -- $rc {
                1 {
                    set ftp(State) append_close
                }
                default {
                    if { [string equal $ftp(Mode) "passive"] } {
                        # close already opened DataConnection
                        unset ftp(state.data)
                    }  
                    set errmsg "Error opening connection!"
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        append_close {
            switch -exact -- $rc {
                2 {
                    set complete_with 1
		    set nextState 1
		    Command $ftp(Command) append $ftp(RemoteFilename)
                }
                default {
                    set errmsg "Error storing file \"$ftp(RemoteFilename)\"!"
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        reget_active {
            if { [OpenActiveConn $s] } {
                PutsCtrlSock $s "PORT $ftp(LocalAddr),$ftp(DataPort)"
                set ftp(State) reget_restart
            } else {
                set errmsg "Error setting port!"
		Command $ftp(Command) error $errmsg
            }
        }
        reget_passive {
            PutsCtrlSock $s "PASV"
            set ftp(State) reget_restart
        }
        reget_restart {
            switch -exact -- $rc {
                2 { 
                    if { [string equal $ftp(Mode) "passive"] } {
                        if { ![OpenPassiveConn $s $buffer] } {
                            set errmsg "Error setting PASSIVE mode!"
                            set complete_with 0
			    Command $ftp(Command) error $errmsg
                        }
                    }   
                    if { $ftp(FileSize) != 0 } {
                        PutsCtrlSock $s "REST $ftp(FileSize)"
                        set ftp(State) reget_open
                    } else {
                        PutsCtrlSock $s "RETR $ftp(RemoteFilename)"
                        set ftp(State) reget_sent
                    } 
                }
                default {
                    set errmsg "Error restarting filetransfer of \"$ftp(RemoteFilename)\"!"
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        reget_open {
            switch -exact -- $rc {
                2 -
                3 {
                    PutsCtrlSock $s "RETR $ftp(RemoteFilename)"
                    set ftp(State) reget_sent
                }
                default {
                    if { [string equal $ftp(Mode) "passive"] } {
                        set errmsg "Error setting PASSIVE mode!"
                    } else {
                        set errmsg "Error setting port!"
                    }  
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        reget_sent {
            switch -exact -- $rc {
                1 {
                    set ftp(State) reget_close
                }
                default {
                    if { [string equal $ftp(Mode) "passive"] } {
                        # close already opened DataConnection
                        unset ftp(state.data)
                    }  
                    set errmsg "Error retrieving file \"$ftp(RemoteFilename)\"!"
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        reget_close {
            switch -exact -- $rc {
                2 {
                    set complete_with 1
		    set nextState 1
		    Command $ftp(Command) get $ftp(RemoteFilename):$ftp(From):$ftp(To)
		    unset ftp(From) ftp(To)
                }
                default {
                    set errmsg "Error retrieving file \"$ftp(RemoteFilename)\"!"
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        get_active {
            if { [OpenActiveConn $s] } {
                PutsCtrlSock $s "PORT $ftp(LocalAddr),$ftp(DataPort)"
                set ftp(State) get_open
            } else {
                set errmsg "Error setting port!"
		Command $ftp(Command) error $errmsg
            }
        } 
        get_passive {
            PutsCtrlSock $s "PASV"
            set ftp(State) get_open
        }
        get_open {
            switch -exact -- $rc {
                1 -
		2 -
                3 {
                    if { [string equal $ftp(Mode) "passive"] } {
                        if { ![OpenPassiveConn $s $buffer] } {
                            set errmsg "Error setting PASSIVE mode!"
                            set complete_with 0
			    Command $ftp(Command) error $errmsg
                        }
                    }   
                    PutsCtrlSock $s "RETR $ftp(RemoteFilename)"
                    set ftp(State) get_sent
                }
                default {
                    if { [string equal $ftp(Mode) "passive"] } {
                        set errmsg "Error setting PASSIVE mode!"
                    } else {
                        set errmsg "Error setting port!"
                    }  
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        get_sent {
            switch -exact -- $rc {
                1 {
                    set ftp(State) get_close
                }
                default {
                    if { [string equal $ftp(Mode) "passive"] } {
                        # close already opened DataConnection
                        unset ftp(state.data)
                    }  
                    set errmsg "Error retrieving file \"$ftp(RemoteFilename)\"!"
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
        get_close {
            switch -exact -- $rc {
                2 {
                    set complete_with 1
		    set nextState 1
		    if {$ftp(inline)} {
			upvar #0 $ftp(get:varname) returnData
			set returnData $ftp(GetData)
			Command $ftp(Command) get $ftp(GetData)
		    } else {
			Command $ftp(Command) get $ftp(RemoteFilename)
		    }
                }
                default {
                    set errmsg "Error retrieving file \"$ftp(RemoteFilename)\"!"
                    set complete_with 0
		    Command $ftp(Command) error $errmsg
                }
            }
        }
	default {
	    error "Unknown state \"$ftp(State)\""
	}
    }

    # finish waiting 
    if { [info exists complete_with] } {
        WaitComplete $s $complete_with
    }

    # display control channel message
    if { [info exists buffer] } {
        if { $VERBOSE } {
            foreach line [split $buffer \n] {
                DisplayMsg $s "C: $line" control
            }
        }
    }
	
    # Rather than throwing an error in the event loop, set the ftp(Error)
    # variable to hold the message so that it can later be thrown after the
    # the StateHandler has completed.

    if { [info exists errmsg] } {
        set ftp(Error) $errmsg
    }

    # If operating asynchronously, commence next state
    if {$nextState && [info exists ftp(NextState)] && [llength $ftp(NextState)]} {
	# Pop the head of the NextState queue
	set ftp(State) [lindex $ftp(NextState) 0]
	set ftp(NextState) [lreplace $ftp(NextState) 0 0]
	StateHandler $s
    }

    # enable fileevent on control socket again
    #fileevent $ftp(CtrlSock) readable [list ::ftp::StateHandler $ftp(CtrlSock)]

}

#############################################################################
#
# Type --
#
# REPRESENTATION TYPE - Sets the file transfer type to ascii or binary.
# (exported)
#
# Arguments:
# type - 		specifies the representation type (ascii|binary)
# 
# Returns:
# type	-		returns the current type or {} if an error occurs

proc ::ftp::Type {s {type ""}} {
    upvar ::ftp::ftp$s ftp

    if { ![info exists ftp(State)] } {
        if { ![string is digit -strict $s] } {
            DisplayMsg $s "Bad connection name \"$s\"" error
        } else {
            DisplayMsg $s "Not connected!" error
        }
        return {}
    }

    # return current type
    if { $type == "" } {
        return $ftp(Type)
    }

    # save current type
    set old_type $ftp(Type) 
	
    set ftp(Type) $type
    set ftp(State) type
    StateHandler $s
	
    # wait for synchronization
    set rc [WaitOrTimeout $s]
    if { $rc } {
        return $ftp(Type)
    } else {
        # restore old type
        set ftp(Type) $old_type
        return {}
    }
}

#############################################################################
#
# NList --
#
# NAME LIST - This command causes a directory listing to be sent from
# server to user site.
# (exported)
# 
# Arguments:
# dir - 		The $dir should specify a directory or other system 
#			specific file group descriptor; a null argument 
#			implies the current directory. 
#
# Arguments:
# dir - 		directory to list 
# 
# Returns:
# sorted list of files or {} if listing fails

proc ::ftp::NList {s { dir ""}} {
    upvar ::ftp::ftp$s ftp

    if { ![info exists ftp(State)] } {
        if { ![string is digit -strict $s] } {
            DisplayMsg $s "Bad connection name \"$s\"" error
        } else {
            DisplayMsg $s "Not connected!" error
        }
        return {}
    }

    set ftp(List) {}
    if { $dir == "" } {
        set ftp(Dir) ""
    } else {
        set ftp(Dir) " $dir"
    }

    # save current type and force ascii mode
    set old_type $ftp(Type)
    if { $ftp(Type) != "ascii" } {
	if {[string length $ftp(Command)]} {
	    set ftp(NextState) [list nlist_$ftp(Mode) type_change list_last]
	    set ftp(type:changeto) $old_type
	    Type $s ascii
	    return {}
	}
        Type $s ascii
    }

    set ftp(State) nlist_$ftp(Mode)
    StateHandler $s

    # wait for synchronization
    set rc [WaitOrTimeout $s]

    # restore old type
    if { [Type $s] != $old_type } {
        Type $s $old_type
    }

    unset ftp(Dir)
    if { $rc } { 
        return [lsort $ftp(List)]
    } else {
        CloseDataConn $s
        return {}
    }
}

#############################################################################
#
# List --
#
# LIST - This command causes a list to be sent from the server
# to user site.
# (exported)
# 
# Arguments:
# dir - 		If the $dir specifies a directory or other group of 
#			files, the server should transfer a list of files in 
#			the specified directory. If the $dir specifies a file
#			then the server should send current information on the
# 			file.  A null argument implies the user's current 
#			working or default directory.  
# 
# Returns:
# list of files or {} if listing fails

proc ::ftp::List {s {dir ""}} {

    upvar ::ftp::ftp$s ftp

    if { ![info exists ftp(State)] } {
        if { ![string is digit -strict $s] } {
            DisplayMsg $s "Bad connection name \"$s\"" error
        } else {
            DisplayMsg $s "Not connected!" error
        }
        return {}
    }

    set ftp(List) {}
    if { $dir == "" } {
        set ftp(Dir) ""
    } else {
        set ftp(Dir) " $dir"
    }

    # save current type and force ascii mode

    set old_type $ftp(Type)
    if { ![string equal "$ftp(Type)" "ascii"] } {
	if {[string length $ftp(Command)]} {
	    set ftp(NextState) [list list_$ftp(Mode) type_change list_last]
	    set ftp(type:changeto) $old_type
	    Type $s ascii
	    return {}
	}
        Type $s ascii
    }

    set ftp(State) list_$ftp(Mode)
    StateHandler $s

    # wait for synchronization

    set rc [WaitOrTimeout $s]

    # restore old type

    if { ![string equal "[Type $s]" "$old_type"] } {
        Type $s $old_type
    }

    unset ftp(Dir)
    if { $rc } { 
	return [ListPostProcess $ftp(List)]
    } else {
        CloseDataConn $s
        return {}
    }
}

proc ::ftp::ListPostProcess l {

    # clear "total"-line

    set l [split $l "\n"]
    set index [lsearch -regexp $l "^total"]
    if { $index != "-1" } { 
	set l [lreplace $l $index $index]
    }

    # clear blank line

    set index [lsearch -regexp $l "^$"]
    if { $index != "-1" } { 
	set l [lreplace $l $index $index]
    }

    return $l
}

#############################################################################
#
# FileSize --
#
# REMOTE FILE SIZE - This command gets the file size of the
# file on the remote machine. 
# ATTENTION! Doesn't work properly in ascii mode!
# (exported)
# 
# Arguments:
# filename - 		specifies the remote file name
# 
# Returns:
# size -		files size in bytes or {} in error cases

proc ::ftp::FileSize {s {filename ""}} {
    upvar ::ftp::ftp$s ftp

    if { ![info exists ftp(State)] } {
        if { ![string is digit -strict $s] } {
            DisplayMsg $s "Bad connection name \"$s\"" error
        } else {
            DisplayMsg $s "Not connected!" error
        }
        return {}
    }
	
    if { $filename == "" } {
        return {}
    } 

    set ftp(File) $filename
    set ftp(FileSize) 0
	
    set ftp(State) size
    StateHandler $s

    # wait for synchronization
    set rc [WaitOrTimeout $s]
	
    if {![string length $ftp(Command)]} {
	unset ftp(File)
    }
		
    if { $rc } {
        return $ftp(FileSize)
    } else {
        return {}
    }
}


#############################################################################
#
# ModTime --
#
# MODIFICATION TIME - This command gets the last modification time of the
# file on the remote machine.
# (exported)
# 
# Arguments:
# filename - 		specifies the remote file name
# datetime -            optional new timestamp for file
# 
# Returns:
# clock -		files date and time as a system-depentend integer
#			value in seconds (see tcls clock command) or {} in 
#			error cases
# if MDTM not supported on server, returns original timestamp

proc ::ftp::ModTime {s {filename ""} {datetime ""}} {
    upvar ::ftp::ftp$s ftp

    if { ![info exists ftp(State)] } {
        if { ![string is digit -strict $s] } {
            DisplayMsg $s "Bad connection name \"$s\"" error
        } else {
            DisplayMsg $s "Not connected!" error
        } 
        return {}
    }
	
    if { $filename == "" } {
        return {}
    } 

    set ftp(File) $filename

    if {$datetime != ""} {
      set datetime [clock format $datetime -format "%Y%m%d%H%M%S"]
    }
    set ftp(DateTime) $datetime
	
    set ftp(State) modtime
    StateHandler $s

    # wait for synchronization
    set rc [WaitOrTimeout $s]
	
    if {![string length $ftp(Command)]} {
	unset ftp(File)
    }
    if { ![string length $ftp(Command)] && $rc } {
        return [ModTimePostProcess $ftp(DateTime)]
    } else {
        return {}
    }
}

proc ::ftp::ModTimePostProcess {clock} {
    foreach {year month day hour min sec} {1 1 1 1 1 1} break

    # Bug #478478. Special code to detect ftp servers with a Y2K patch
    # gone bad and delivering, hmmm, non-standard date information.

    if {[string length $clock] == 15} {
        scan $clock "%2s%3s%2s%2s%2s%2s%2s" cent year month day hour min sec
        set year [expr {($cent * 100) + $year}]
	log::log warning "data | W: server with non-standard time, bad Y2K patch."
    } else {
        scan $clock "%4s%2s%2s%2s%2s%2s" year month day hour min sec
    }

    set clock [clock scan "$month/$day/$year $hour:$min:$sec" -gmt 1]
    return $clock
}

#############################################################################
#
# Pwd --
#
# PRINT WORKING DIRECTORY - Causes the name of the current working directory.
# (exported)
# 
# Arguments:
# None.
# 
# Returns:
# current directory name

proc ::ftp::Pwd {s } {
    upvar ::ftp::ftp$s ftp

    if { ![info exists ftp(State)] } {
        if { ![string is digit -strict $s] } {
            DisplayMsg $s "Bad connection name \"$s\"" error
        } else {
            DisplayMsg $s "Not connected!" error
        }
        return {}
    }

    set ftp(Dir) {}

    set ftp(State) pwd
    StateHandler $s

    # wait for synchronization
    set rc [WaitOrTimeout $s]
	
    if { $rc } {
        return $ftp(Dir)
    } else {
        return {}
    }
}

#############################################################################
#
# Cd --
#   
# CHANGE DIRECTORY - Sets the working directory on the server host.
# (exported)
# 
# Arguments:
# dir -			pathname specifying a directory
#
# Returns:
# 0 -			ERROR
# 1 - 			OK

proc ::ftp::Cd {s {dir ""}} {
    upvar ::ftp::ftp$s ftp

    if { ![info exists ftp(State)] } {
        if { ![string is digit -strict $s] } {
            DisplayMsg $s "Bad connection name \"$s\"" error
        } else {
            DisplayMsg $s "Not connected!" error
        }
        return 0
    }

    if { $dir == "" } {
        set ftp(Dir) ""
    } else {
        set ftp(Dir) " $dir"
    }

    set ftp(State) cd
    StateHandler $s

    # wait for synchronization
    set rc [WaitOrTimeout $s] 

    if {![string length $ftp(Command)]} {
	unset ftp(Dir)
    }
	
    if { $rc } {
        return 1
    } else {
        return 0
    }
}

#############################################################################
#
# MkDir --
#
# MAKE DIRECTORY - This command causes the directory specified in the $dir
# to be created as a directory (if the $dir is absolute) or as a subdirectory
# of the current working directory (if the $dir is relative).
# (exported)
# 
# Arguments:
# dir -			new directory name
#
# Returns:
# 0 -			ERROR
# 1 - 			OK

proc ::ftp::MkDir {s dir} {
    upvar ::ftp::ftp$s ftp

    if { ![info exists ftp(State)] } {
        DisplayMsg $s "Not connected!" error
        return 0
    }

    set ftp(Dir) $dir

    set ftp(State) mkdir
    StateHandler $s

    # wait for synchronization
    set rc [WaitOrTimeout $s] 

    if {![string length $ftp(Command)]} {
	unset ftp(Dir)
    }
	
    if { $rc } {
        return 1
    } else {
        return 0
    }
}

#############################################################################
#
# RmDir --
#
# REMOVE DIRECTORY - This command causes the directory specified in $dir to 
# be removed as a directory (if the $dir is absolute) or as a 
# subdirectory of the current working directory (if the $dir is relative).
# (exported)
#
# Arguments:
# dir -			directory name
#
# Returns:
# 0 -			ERROR
# 1 - 			OK

proc ::ftp::RmDir {s dir} {
    upvar ::ftp::ftp$s ftp

    if { ![info exists ftp(State)] } {
        DisplayMsg $s "Not connected!" error
        return 0
    }

    set ftp(Dir) $dir

    set ftp(State) rmdir
    StateHandler $s

    # wait for synchronization
    set rc [WaitOrTimeout $s] 

    if {![string length $ftp(Command)]} {
	unset ftp(Dir)
    }
	
    if { $rc } {
        return 1
    } else {
        return 0
    }
}

#############################################################################
#
# Delete --
#
# DELETE - This command causes the file specified in $file to be deleted at 
# the server site.
# (exported)
# 
# Arguments:
# file -			file name
#
# Returns:
# 0 -			ERROR
# 1 - 			OK

proc ::ftp::Delete {s file} {
    upvar ::ftp::ftp$s ftp

    if { ![info exists ftp(State)] } {
        DisplayMsg $s "Not connected!" error
        return 0
    }

    set ftp(File) $file

    set ftp(State) delete
    StateHandler $s

    # wait for synchronization
    set rc [WaitOrTimeout $s] 

    if {![string length $ftp(Command)]} {
	unset ftp(File)
    }
	
    if { $rc } {
        return 1
    } else {
        return 0
    }
}

#############################################################################
#
# Rename --
#
# RENAME FROM TO - This command causes the file specified in $from to be 
# renamed at the server site.
# (exported)
# 
# Arguments:
# from -			specifies the old file name of the file which 
#				is to be renamed
# to -				specifies the new file name of the file 
#				specified in the $from agument
# Returns:
# 0 -			ERROR
# 1 - 			OK

proc ::ftp::Rename {s from to} {
    upvar ::ftp::ftp$s ftp

    if { ![info exists ftp(State)] } {
        DisplayMsg $s "Not connected!" error
        return 0
    }

    set ftp(RenameFrom) $from
    set ftp(RenameTo) $to

    set ftp(State) rename

    StateHandler $s

    # wait for synchronization
    set rc [WaitOrTimeout $s] 

    if {![string length $ftp(Command)]} {
	unset ftp(RenameFrom)
	unset ftp(RenameTo)
    }
	
    if { $rc } {
        return 1
    } else {
        return 0
    }
}

#############################################################################
#
# ElapsedTime --
#
# Gets the elapsed time for file transfer
# 
# Arguments:
# stop_time - 		ending time

proc ::ftp::ElapsedTime {s stop_time} {
    variable VERBOSE
    upvar ::ftp::ftp$s ftp

    set elapsed [expr {$stop_time - $ftp(Start_Time)}]
    if { $elapsed == 0 } {
        set elapsed 1
    }
    set persec [expr {$ftp(Total) / $elapsed}]
    if { $VERBOSE } {
        DisplayMsg $s "$ftp(Total) bytes sent in $elapsed seconds ($persec Bytes/s)"
    }
    return
}

#############################################################################
#
# PUT --
#
# STORE DATA - Causes the server to accept the data transferred via the data 
# connection and to store the data as a file at the server site.  If the file
# exists at the server site, then its contents shall be replaced by the data
# being transferred.  A new file is created at the server site if the file
# does not already exist.
# (exported)
#
# Arguments:
# source -			local file name
# dest -			remote file name, if unspecified, ftp assigns
#				the local file name.
# Returns:
# 0 -			file not stored
# 1 - 			OK

proc ::ftp::Put {s args} {
    upvar ::ftp::ftp$s ftp

    if { ![info exists ftp(State)] } {
        DisplayMsg $s "Not connected!" error
        return 0
    }
    if {([llength $args] < 1) || ([llength $args] > 4)} {
        DisplayMsg $s \
		"wrong # args: should be \"ftp::Put handle (-data \"data\" | -channel chan | localFilename) remoteFilename\"" error
	return 0    
    }

    set ftp(inline) 0
    set flags 1
    set source ""
    set dest ""
    foreach arg $args {
        if {[string equal $arg "--"]} {
            set flags 0
        } elseif {($flags) && ([string equal $arg "-data"])} {
            set ftp(inline) 1
            set ftp(filebuffer) ""
        } elseif {($flags) && ([string equal $arg "-channel"])} {
            set ftp(inline) 2
	} elseif {$source == ""} {
            set source $arg
	} elseif {$dest == ""} {
            set dest $arg
	} else {
            DisplayMsg $s "wrong # args: should be \"ftp::Put handle (-data \"data\" | -channel chan | localFilename) remoteFilename\"" error
	    return 0
        }
    }

    if {($source == "")} {
        DisplayMsg $s "Must specify a valid data source to Put" error
        return 0
    }        

    set ftp(RemoteFilename) $dest

    if {$ftp(inline) == 1} {
        set ftp(PutData) $source
        if { $dest == "" } {
            set dest ftp.tmp
        }
        set ftp(RemoteFilename) $dest
    } else {
	if {$ftp(inline) == 0} {
	    # File transfer

	    set ftp(PutData) ""
	    if { ![file exists $source] } {
		DisplayMsg $s "File \"$source\" not exist" error
		return 0
	    }
	    if { $dest == "" } {
		set dest [file tail $source]
	    }
	    set ftp(LocalFilename) $source
	    set ftp(SourceCI) [open $ftp(LocalFilename) r]
	} else {
	    # Channel transfer. We fake the rest of the system into
	    # believing that a file transfer is happening. This makes
	    # the handling easier.

	    set ftp(SourceCI) $source
	    set ftp(inline) 0
	}
        set ftp(RemoteFilename) $dest

	# TODO: read from source file asynchronously
        if { [string equal $ftp(Type) "ascii"] } {
            fconfigure $ftp(SourceCI) -buffering line -blocking 1
        } else {
            fconfigure $ftp(SourceCI) -buffering line -translation binary -blocking 1
        }
    }

    set ftp(State) put_$ftp(Mode)
    StateHandler $s

    # wait for synchronization
    set rc [WaitOrTimeout $s]
    if { $rc } {
	if {![string length $ftp(Command)]} {
	    ElapsedTime $s [clock seconds]
	}
        return 1
    } else {
        CloseDataConn $s
        return 0
    }
}

#############################################################################
#
# APPEND --
#
# APPEND DATA - Causes the server to accept the data transferred via the data 
# connection and to store the data as a file at the server site.  If the file
# exists at the server site, then the data shall be appended to that file; 
# otherwise the file specified in the pathname shall be created at the
# server site.
# (exported)
#
# Arguments:
# source -			local file name
# dest -			remote file name, if unspecified, ftp assigns
#				the local file name.
# Returns:
# 0 -			file not stored
# 1 - 			OK

proc ::ftp::Append {s args} {
    upvar ::ftp::ftp$s ftp

    if { ![info exists ftp(State)] } {
        DisplayMsg $s "Not connected!" error
        return 0
    }

    if {([llength $args] < 1) || ([llength $args] > 4)} {
        DisplayMsg $s "wrong # args: should be \"ftp::Append handle (-data \"data\" | -channel chan | localFilename) remoteFilename\"" error
        return 0
    }

    set ftp(inline) 0
    set flags 1
    set source ""
    set dest ""
    foreach arg $args {
        if {[string equal $arg "--"]} {
            set flags 0
        } elseif {($flags) && ([string equal $arg "-data"])} {
            set ftp(inline) 1
            set ftp(filebuffer) ""
        } elseif {($flags) && ([string equal $arg "-channel"])} {
            set ftp(inline) 2
        } elseif {$source == ""} {
            set source $arg
        } elseif {$dest == ""} {
            set dest $arg
        } else {
            DisplayMsg $s "wrong # args: should be \"ftp::Append handle (-data \"data\" | -channel chan | localFilename) remoteFilename\"" error
            return 0
        }
    }

    if {($source == "")} {
        DisplayMsg $s "Must specify a valid data source to Append" error
        return 0
    }   

    set ftp(RemoteFilename) $dest

    if {$ftp(inline) == 1} {
        set ftp(PutData) $source
        if { $dest == "" } {
            set dest ftp.tmp
        }
        set ftp(RemoteFilename) $dest
    } else {
	if {$ftp(inline) == 0} {
	    # File transfer

	    set ftp(PutData) ""
	    if { ![file exists $source] } {
		DisplayMsg $s "File \"$source\" not exist" error
		return 0
	    }
			
	    if { $dest == "" } {
		set dest [file tail $source]
	    }

	    set ftp(LocalFilename) $source
	    set ftp(SourceCI) [open $ftp(LocalFilename) r]
	} else {
	    # Channel transfer. We fake the rest of the system into
	    # believing that a file transfer is happening. This makes
	    # the handling easier.

	    set ftp(SourceCI) $source
	    set ftp(inline) 0
	}
        set ftp(RemoteFilename) $dest

        if { [string equal $ftp(Type) "ascii"] } {
            fconfigure $ftp(SourceCI) -buffering line -blocking 1
        } else {
            fconfigure $ftp(SourceCI) -buffering line -translation binary \
                    -blocking 1
        }
    }

    set ftp(State) append_$ftp(Mode)
    StateHandler $s

    # wait for synchronization
    set rc [WaitOrTimeout $s]
    if { $rc } {
	if {![string length $ftp(Command)]} {
	    ElapsedTime $s [clock seconds]
	}
        return 1
    } else {
        CloseDataConn $s
        return 0
    }
}


#############################################################################
#
# Get --
#
# RETRIEVE DATA - Causes the server to transfer a copy of the specified file
# to the local site at the other end of the data connection.
# (exported)
#
# Arguments:
# source -			remote file name
# dest -			local file name, if unspecified, ftp assigns
#				the remote file name.
# Returns:
# 0 -			file not retrieved
# 1 - 			OK

proc ::ftp::Get {s args} {
    upvar ::ftp::ftp$s ftp

    if { ![info exists ftp(State)] } {
        DisplayMsg $s "Not connected!" error
        return 0
    }

    if {([llength $args] < 1) || ([llength $args] > 4)} {
        DisplayMsg $s "wrong # args: should be \"ftp::Get handle remoteFile ?(-variable varName | -channel chan | localFilename)?\"" error
	return 0    
    }

    set ftp(inline) 0
    set flags 1
    set source ""
    set dest ""
    set varname "**NONE**"
    foreach arg $args {
        if {[string equal $arg "--"]} {
            set flags 0
        } elseif {($flags) && ([string equal $arg "-variable"])} {
            set ftp(inline) 1
            set ftp(filebuffer) ""
        } elseif {($flags) && ([string equal $arg "-channel"])} {
            set ftp(inline) 2
	} elseif {($ftp(inline) == 1) && ([string equal $varname "**NONE**"])} {
            set varname $arg
	    set ftp(get:varname) $varname
	} elseif {($ftp(inline) == 2) && ([string equal $varname "**NONE**"])} {
	    set ftp(get:channel) $arg
	} elseif {$source == ""} {
            set source $arg
	} elseif {$dest == ""} {
            set dest $arg
	} else {
            DisplayMsg $s "wrong # args: should be \"ftp::Get handle remoteFile
?(-variable varName | -channel chan | localFilename)?\"" error
	    return 0
        }
    }

    if {($ftp(inline) != 0) && ($dest != "")} {
        DisplayMsg $s "Cannot return data in a variable or channel, and place it in destination file." error
        return 0
    }

    if {$source == ""} {
        DisplayMsg $s "Must specify a valid data source to Get" error
        return 0
    }

    if {$ftp(inline) == 0} {
	if { $dest == "" } {
	    set dest $source
	} else {
	    if {[file isdirectory $dest]} {
		set dest [file join $dest [file tail $source]]
	    }
	}
	if {![file exists [file dirname $dest]]} {
	    return -code error "ftp::Get, directory \"[file dirname $dest]\" for destination \"$dest\" does not exist"
	}
	set ftp(LocalFilename) $dest
    }

    set ftp(RemoteFilename) $source

    if {$ftp(inline) == 2} {
	set ftp(inline) 0
    }
    set ftp(State) get_$ftp(Mode)
    StateHandler $s

    # wait for synchronization
    set rc [WaitOrTimeout $s]

    # It is important to unset 'get:channel' in all cases or it will
    # interfere with any following ftp command (as its existence
    # suppresses the closing of the destination channel identifier
    # (DestCI). We cannot do it earlier than just before the 'return'
    # or code depending on it for the current command may not execute
    # correctly.

    if { $rc } {
	if {![string length $ftp(Command)]} {
	    ElapsedTime $s [clock seconds]
	    if {$ftp(inline)} {
		catch {unset ftp(get:channel)}
		upvar $varname returnData
		set returnData $ftp(GetData)
	    }
	}
	catch {unset ftp(get:channel)}
        return 1
    } else {
        if {$ftp(inline)} {
	    catch {unset ftp(get:channel)}
            return ""
	}
        CloseDataConn $s
	catch {unset ftp(get:channel)}
        return 0
    }
}

#############################################################################
#
# Reget --
#
# RESTART RETRIEVING DATA - Causes the server to transfer a copy of the specified file
# to the local site at the other end of the data connection like get but skips over 
# the file to the specified data checkpoint. 
# (exported)
#
# Arguments:
# source -			remote file name
# dest -			local file name, if unspecified, ftp assigns
#				the remote file name.
# Returns:
# 0 -			file not retrieved
# 1 - 			OK

proc ::ftp::Reget {s source {dest ""} {from_bytes 0} {till_bytes -1}} {
    upvar ::ftp::ftp$s ftp
    
    if { ![info exists ftp(State)] } {
        DisplayMsg $s "Not connected!" error
        return 0
    }

    if { $dest == "" } {
        set dest $source
    }
    if {![file exists [file dirname $dest]]} {
	return -code error \
	"ftp::Reget, directory \"[file dirname $dest]\" for destination \"$dest\" does not exist"
    }

    set ftp(RemoteFilename) $source
    set ftp(LocalFilename) $dest
    set ftp(From) $from_bytes


    # Assumes that the local file has a starting offset of $from_bytes
    # The following calculation ensures that the download starts from the
    # correct offset

    if { [file exists $ftp(LocalFilename)] } {
	set ftp(FileSize) [ expr {[file size $ftp(LocalFilename)] + $from_bytes }]
	 	
	if { $till_bytes != -1 } {
	    set ftp(To)   $till_bytes	
	    set ftp(Bytes_to_go) [ expr {$till_bytes - $ftp(FileSize)} ]
	
	    if { $ftp(Bytes_to_go) <= 0 } {return 0}

	} else {
	    # till_bytes not set
	    set ftp(To)   end
	}

    } else {
	# local file does not exist
        set ftp(FileSize) $from_bytes
		  
	if { $till_bytes != -1 } {
	    set ftp(Bytes_to_go) [ expr {$till_bytes - $from_bytes }]
	    set ftp(To) $till_bytes
	} else {
	    #till_bytes not set
	    set ftp(To)   end
	}
    }
	
    set ftp(State) reget_$ftp(Mode)
    StateHandler $s

    # wait for synchronization
    set rc [WaitOrTimeout $s]
    if { $rc } {
	if {![string length $ftp(Command)]} {
	    ElapsedTime $s [clock seconds]
	}
        return 1
    } else {
        CloseDataConn $s
        return 0
    }
}

#############################################################################
#
# Newer --
#
# GET NEWER DATA - Get the file only if the modification time of the remote 
# file is more recent that the file on the current system. If the file does
# not exist on the current system, the remote file is considered newer.
# Otherwise, this command is identical to get. 
# (exported)
#
# Arguments:
# source -			remote file name
# dest -			local file name, if unspecified, ftp assigns
#				the remote file name.
#
# Returns:
# 0 -			file not retrieved
# 1 - 			OK

proc ::ftp::Newer {s source {dest ""}} {
    upvar ::ftp::ftp$s ftp

    if { ![info exists ftp(State)] } {
        DisplayMsg $s "Not connected!" error
        return 0
    }

    if {[string length $ftp(Command)]} {
	return -code error "unable to retrieve file asynchronously (not implemented yet)"
    }

    if { $dest == "" } {
        set dest $source
    }
    if {![file exists [file dirname $dest]]} {
	return -code error "ftp::Newer, directory \"[file dirname $dest]\" for destination \"$dest\" does not exist"
    }

    set ftp(RemoteFilename) $source
    set ftp(LocalFilename) $dest

    # get remote modification time
    set rmt [ModTime $s $ftp(RemoteFilename)]
    if { $rmt == "-1" } {
        return 0
    }

    # get local modification time
    if { [file exists $ftp(LocalFilename)] } {
        set lmt [file mtime $ftp(LocalFilename)]
    } else {
        set lmt 0
    }
	
    # remote file is older than local file
    if { $rmt < $lmt } {
        return 0
    }

    # remote file is newer than local file or local file doesn't exist
    # get it
    set rc [Get $s $ftp(RemoteFilename) $ftp(LocalFilename)]
    return $rc
		
}

#############################################################################
#
# Quote -- 
#
# The arguments specified are sent, verbatim, to the remote ftp server.     
#
# Arguments:
# 	arg1 arg2 ...
#
# Returns:
#  string sent back by the remote ftp server or null string if any error
#

proc ::ftp::Quote {s args} {
    upvar ::ftp::ftp$s ftp

    if { ![info exists ftp(State)] } {
        DisplayMsg $s "Not connected!" error
        return 0
    }

    set ftp(Cmd) $args
    set ftp(Quote) {}

    set ftp(State) quote
    StateHandler $s

    # wait for synchronization
    set rc [WaitOrTimeout $s] 

    unset ftp(Cmd)

    if { $rc } {
        return $ftp(Quote)
    } else {
        return {}
    }
}


#############################################################################
#
# Abort -- 
#
# ABORT - Tells the server to abort the previous ftp service command and 
# any associated transfer of data. The control connection is not to be 
# closed by the server, but the data connection must be closed.
# 
# NOTE: This procedure doesn't work properly. Thus the ftp::Abort command
# is no longer available!
#
# Arguments:
# None.
#
# Returns:
# 0 -			ERROR
# 1 - 			OK
#
# proc Abort {} {
#
# }

#############################################################################
#
# Close -- 
#
# Terminates a ftp session and if file transfer is not in progress, the server
# closes the control connection.  If file transfer is in progress, the 
# connection will remain open for result response and the server will then
# close it. 
# (exported)
# 
# Arguments:
# None.
#
# Returns:
# 0 -			ERROR
# 1 - 			OK

proc ::ftp::Close {s } {
    variable connections
    upvar ::ftp::ftp$s ftp

    if { ![info exists ftp(State)] } {
        DisplayMsg $s "Not connected!" error
        return 0
    }

    if {[info exists \
            connections($ftp(User),$ftp(Passwd),$ftp(RemoteHost),afterid)]} {
        unset connections($ftp(User),$ftp(Passwd),$ftp(RemoteHost),afterid)
        unset connections($ftp(User),$ftp(Passwd),$ftp(RemoteHost))
    }

    set ftp(State) quit
    StateHandler $s

    # wait for synchronization
    WaitOrTimeout $s

    catch {close $ftp(CtrlSock)}
    catch {unset ftp}
    return 1
}

proc ::ftp::LazyClose {s } {
    variable connections
    upvar ::ftp::ftp$s ftp

    if { ![info exists ftp(State)] } {
        DisplayMsg $s "Not connected!" error
        return 0
    }

    if {[info exists connections($ftp(User),$ftp(Passwd),$ftp(RemoteHost))]} {
        set connections($ftp(User),$ftp(Passwd),$ftp(RemoteHost),afterid) \
                [after 5000 [list ftp::Close $s]]
    }
    return 1
}

#############################################################################
#
# Open --
#
# Starts the ftp session and sets up a ftp control connection.
# (exported)
# 
# Arguments:
# server - 		The ftp server hostname.
# user -		A string identifying the user. The user identification 
#			is that which is required by the server for access to 
#			its file system.  
# passwd -		A string specifying the user's password.
# options -		-blocksize size		writes "size" bytes at once
#						(default 4096)
#			-timeout seconds	if non-zero, sets up timeout to
#						occur after specified number of
#						seconds (default 120)
#			-progress proc		procedure name that handles callbacks
#						(no default)  
#			-output proc		procedure name that handles output
#						(no default)  
#			-mode mode		switch active or passive file transfer
#						(default active)
#			-port number		alternative port (default 21)
#			-command proc		callback for completion notification
#						(no default)
# 
# Returns:
# 0 -			Not logged in
# 1 - 			User logged in

proc ::ftp::Open {server user passwd args} {
    variable DEBUG 
    variable VERBOSE
    variable serial
    variable connections

    set s $serial
    incr serial
    upvar ::ftp::ftp$s ftp
#    if { [info exists ftp(State)] } {
#        DisplayMsg $s "Mmh, another attempt to open a new connection? There is already a hot wire!" error
#        return 0
#    }

    # default NO DEBUG
    if { ![info exists DEBUG] } {
        set DEBUG 0
    }

    # default NO VERBOSE
    if { ![info exists VERBOSE] } {
        set VERBOSE 0
    }
	
    if { $DEBUG } {
        DisplayMsg $s "Starting new connection with: "
    }

    set ftp(inline) 	0
    set ftp(User)       $user
    set ftp(Passwd) 	$passwd
    set ftp(RemoteHost) $server
    set ftp(LocalHost) 	[info hostname]
    set ftp(DataPort) 	0
    set ftp(Type) 	{}
    set ftp(Error) 	""
    set ftp(Progress) 	{}
    set ftp(Command)	{}
    set ftp(Output) 	{}
    set ftp(Blocksize) 	4096	
    set ftp(Timeout) 	600	
    set ftp(Mode) 	active	
    set ftp(Port) 	21	

    set ftp(State) 	user
	
    # set state var
    set ftp(state.control) ""
	
    # Get and set possible options
    set options {-blocksize -timeout -mode -port -progress -output -command}
    foreach {option value} $args {
        if { [lsearch -exact $options $option] != "-1" } {
            if { $DEBUG } {
                DisplayMsg $s "  $option = $value"
            }
            regexp -- {^-(.?)(.*)$} $option all first rest
            set option "[string toupper $first]$rest"
            set ftp($option) $value
        } 
    }
    if { $DEBUG && ([llength $args] == 0) } {
        DisplayMsg $s "  no option"
    }

    if {[info exists \
            connections($ftp(User),$ftp(Passwd),$ftp(RemoteHost),afterid)]} {
        after cancel $connections($ftp(User),$ftp(Passwd),$ftp(RemoteHost),afterid)
	Command $ftp(Command) connect $connections($ftp(User),$ftp(Passwd),$ftp(RemoteHost))
        return $connections($ftp(User),$ftp(Passwd),$ftp(RemoteHost))
    }


    # No call of StateHandler is required at this time.
    # StateHandler at first time is called automatically
    # by a fileevent for the control channel.

    # Try to open a control connection
    if { ![OpenControlConn $s [expr {[string length $ftp(Command)] > 0}]] } {
        return -1
    }

    # waits for synchronization
    #   0 ... Not logged in
    #   1 ... User logged in
    if {[string length $ftp(Command)]} {
	# Don't wait - asynchronous operation
	set ftp(NextState) {type connect_last}
        set connections($ftp(User),$ftp(Passwd),$ftp(RemoteHost)) $s
	return $s
    } elseif { [WaitOrTimeout $s] } {
        # default type is binary
        Type $s binary
        set connections($ftp(User),$ftp(Passwd),$ftp(RemoteHost)) $s
	Command $ftp(Command) connect $s
        return $s
    } else {
        # close connection if not logged in
        Close $s
        return -1
    }
}

#############################################################################
#
# CopyNext --
#
# recursive background copy procedure for ascii/binary file I/O
# 
# Arguments:
# bytes - 		indicates how many bytes were written on $ftp(DestCI)

proc ::ftp::CopyNext {s bytes {error {}}} {
    upvar ::ftp::ftp$s ftp
    variable DEBUG
    variable VERBOSE

    # summary bytes

    incr ftp(Total) $bytes

    # update bytes_to_go and blocksize

    if { [info exists ftp(Bytes_to_go)] } {
	set ftp(Bytes_to_go) [expr {$ftp(Bytes_to_go) - $bytes}]
	 
	if { $ftp(Blocksize) <= $ftp(Bytes_to_go) } {
	    set blocksize $ftp(Blocksize)
	} else {
	    set blocksize $ftp(Bytes_to_go)
	}
    } else {
	set blocksize $ftp(Blocksize)
    } 
    
    # callback for progress bar procedure
    
    if { ([info exists ftp(Progress)]) && \
	    [string length $ftp(Progress)] && \
	    ([info commands [lindex $ftp(Progress) 0]] != "") } { 
        eval $ftp(Progress) $ftp(Total)
    }

    # setup new timeout handler

    catch {after cancel $ftp(Wait)}
    set ftp(Wait) [after [expr {$ftp(Timeout) * 1000}] [namespace current]::Timeout $s]

    if { $DEBUG } {
        DisplayMsg $s "-> $ftp(Total) bytes $ftp(SourceCI) -> $ftp(DestCI)" 
    }

    if { $error != "" } {
	# Protect the destination channel from destruction if it came
	# from the caller. Closing it is not our responsibility in that case.

	if {![info exists ftp(get:channel)]} {
	    catch {close $ftp(DestCI)}
	}
        catch {close $ftp(SourceCI)}
        unset ftp(state.data)
        DisplayMsg $s $error error

    } elseif { ([eof $ftp(SourceCI)] || ($blocksize <= 0)) } {
	# Protect the destination channel from destruction if it came
	# from the caller. Closing it is not our responsibility in that case.

	if {![info exists ftp(get:channel)]} {
	    close $ftp(DestCI)
	}
        close $ftp(SourceCI)
        unset ftp(state.data)
        if { $VERBOSE } {
            DisplayMsg $s "D: Port closed" data
        }

    } else {
	fcopy $ftp(SourceCI) $ftp(DestCI) \
		-command [list [namespace current]::CopyNext $s] \
		-size $blocksize
    }
    return
}

#############################################################################
#
# HandleData --
#
# Handles ascii/binary data transfer for Put and Get 
# 
# Arguments:
# sock - 		socket name (data channel)

proc ::ftp::HandleData {s sock} {
    upvar ::ftp::ftp$s ftp

    # Turn off any fileevent handlers

    fileevent $sock writable {}		
    fileevent $sock readable {}

    # create local file for ftp::Get 

    if { [string match "get*" $ftp(State)]  && (!$ftp(inline))} {

	# A channel was specified by the caller. Use that instead of a
	# file.

	if {[info exists ftp(get:channel)]} {
	    set ftp(DestCI) $ftp(get:channel)
	    set rc 0
	} else {
	    set rc [catch {set ftp(DestCI) [open $ftp(LocalFilename) w]} msg]
	}
        if { $rc != 0 } {
            DisplayMsg $s "$msg" error
            return 0
        }
	# TODO: Use non-blocking I/O
        if { [string equal $ftp(Type) "ascii"] } {
            fconfigure $ftp(DestCI) -buffering line -blocking 1
        } else {
            fconfigure $ftp(DestCI) -buffering line -translation binary -blocking 1
        }
    }	

    # append local file for ftp::Reget 

    if { [string match "reget*" $ftp(State)] } {
        set rc [catch {set ftp(DestCI) [open $ftp(LocalFilename) a]} msg]
        if { $rc != 0 } {
            DisplayMsg $s "$msg" error
            return 0
        }
	# TODO: Use non-blocking I/O
        if { [string equal $ftp(Type) "ascii"] } {
            fconfigure $ftp(DestCI) -buffering line -blocking 1
        } else {
            fconfigure $ftp(DestCI) -buffering line -translation binary -blocking 1
        }
    }	


    set ftp(Total) 0
    set ftp(Start_Time) [clock seconds]
	 
    # calculate blocksize
	 
    if { [ info exists ftp(Bytes_to_go) ] } {
			
	if { $ftp(Blocksize) <= $ftp(Bytes_to_go) } {
	    set Blocksize $ftp(Blocksize)
	} else {
	    set Blocksize $ftp(Bytes_to_go)
	}
	
    } else {
	set Blocksize $ftp(Blocksize)
    }
	
    # perform fcopy
    fcopy $ftp(SourceCI) $ftp(DestCI) \
	    -command [list [namespace current]::CopyNext $s ] \
	    -size $Blocksize
    return 1
}

#############################################################################
#
# HandleList --
#
# Handles ascii data transfer for list commands
# 
# Arguments:
# sock - 		socket name (data channel)

proc ::ftp::HandleList {s sock} {
    upvar ::ftp::ftp$s ftp
    variable VERBOSE

    if { ![eof $sock] } {
        set buffer [read $sock]
        if { $buffer != "" } {
            set ftp(List) [append ftp(List) $buffer]
        }	
    } else {
        close $sock
        catch {unset ftp(state.data)}
        if { $VERBOSE } {
            DisplayMsg $s "D: Port closed" data
        }
    }
    return
}

#############################################################################
#
# HandleVar --
#
# Handles data transfer for get/put commands that use buffers instead
# of files.
# 
# Arguments:
# sock - 		socket name (data channel)

proc ::ftp::HandleVar {s sock} {
    upvar ::ftp::ftp$s ftp
    variable VERBOSE

    if {$ftp(Start_Time) == -1} {
        set ftp(Start_Time) [clock seconds]
    }

    if { ![eof $sock] } {
        set buffer [read $sock]
        if { $buffer != "" } {
            append ftp(GetData) $buffer
            incr ftp(Total) [string length $buffer]
        }	
    } else {
        close $sock
        catch {unset ftp(state.data)}
        if { $VERBOSE } {
            DisplayMsg $s "D: Port closed" data
        }
    }
    return
}

#############################################################################
#
# HandleOutput --
#
# Handles data transfer for get/put commands that use buffers instead
# of files.
# 
# Arguments:
# sock - 		socket name (data channel)

proc ::ftp::HandleOutput {s sock} {
    upvar ::ftp::ftp$s ftp
    variable VERBOSE

    if {$ftp(Start_Time) == -1} {
        set ftp(Start_Time) [clock seconds]
    }

    if { $ftp(Total) < [string length $ftp(PutData)] } {
        set substr [string range $ftp(PutData) $ftp(Total) \
                [expr {$ftp(Total) + $ftp(Blocksize)}]]
        if {[catch {puts -nonewline $sock "$substr"} result]} {
            close $sock
            unset ftp(state.data)
            if { $VERBOSE } {
                DisplayMsg $s "D: Port closed" data
            }
        } else {
            incr ftp(Total) [string length $substr]
        }
    } else {
        fileevent $sock writable {}		
        close $sock
        catch {unset ftp(state.data)}
        if { $VERBOSE } {
            DisplayMsg $s "D: Port closed" data
        }
    }
    return
}

############################################################################
#
# CloseDataConn -- 
#
# Closes all sockets and files used by the data conection
#
# Arguments:
# None.
#
# Returns:
# None.
#
proc ::ftp::CloseDataConn {s } {
    upvar ::ftp::ftp$s ftp

    # Protect the destination channel from destruction if it came
    # from the caller. Closing it is not our responsibility.

    if {[info exists ftp(get:channel)]} {
	catch {unset ftp(get:channel)}
	catch {unset ftp(DestCI)}
    }

    catch {after cancel $ftp(Wait)}
    catch {fileevent $ftp(DataSock) readable {}}
    catch {close $ftp(DataSock); unset ftp(DataSock)}
    catch {close $ftp(DestCI); unset ftp(DestCI)} 
    catch {close $ftp(SourceCI); unset ftp(SourceCI)}
    catch {close $ftp(DummySock); unset ftp(DummySock)}
    return
}

#############################################################################
#
# InitDataConn --
#
# Configures new data channel for connection to ftp server 
# ATTENTION! The new data channel "sock" is not the same as the 
# server channel, it's a dummy.
# 
# Arguments:
# sock -		the name of the new channel
# addr -		the address, in network address notation, 
#			of the client's host,
# port -		the client's port number

proc ::ftp::InitDataConn {s sock addr port} {
    upvar ::ftp::ftp$s ftp
    variable VERBOSE

    # If the new channel is accepted, the dummy channel will be closed

    catch {close $ftp(DummySock); unset ftp(DummySock)}

    set ftp(state.data) 0

    # Configure translation and blocking modes

    set blocking 1
    if {[string length $ftp(Command)]} {
	set blocking 0
    }

    if { [string equal $ftp(Type) "ascii"] } {
        fconfigure $sock -buffering line -blocking $blocking
    } else {
        fconfigure $sock -buffering line -translation binary -blocking $blocking
    }

    # assign fileevent handlers, source and destination CI (Channel Identifier)

    # NB: this really does need to be -regexp [PT] 18Mar03
    switch -regexp -- $ftp(State) {
        list {
            fileevent $sock readable [list [namespace current]::HandleList $s $sock]
            set ftp(SourceCI) $sock
        }
        get {
            if {$ftp(inline)} {
                set ftp(GetData) ""
                set ftp(Start_Time) -1
                set ftp(Total) 0
                fileevent $sock readable [list [namespace current]::HandleVar $s $sock]
	    } else {
                fileevent $sock readable [list [namespace current]::HandleData $s $sock]
                set ftp(SourceCI) $sock
	    }
        }
        append -
        put {
            if {$ftp(inline)} {
                set ftp(Start_Time) -1
                set ftp(Total) 0
                fileevent $sock writable [list [namespace current]::HandleOutput $s $sock]
	    } else {
                fileevent $sock writable [list [namespace current]::HandleData $s $sock]
                set ftp(DestCI) $sock
	    }
        }
	default {
	    error "Unknown state \"$ftp(State)\""
	}
    }

    if { $VERBOSE } {
        DisplayMsg $s "D: Connection from $addr:$port" data
    }
    return
}

#############################################################################
#
# OpenActiveConn --
#
# Opens a ftp data connection
# 
# Arguments:
# None.
# 
# Returns:
# 0 -			no connection
# 1 - 			connection established

proc ::ftp::OpenActiveConn {s } {
    upvar ::ftp::ftp$s ftp
    variable VERBOSE

    # Port address 0 is a dummy used to give the server the responsibility 
    # of getting free new port addresses for every data transfer.
    
    set rc [catch {set ftp(DummySock) [socket -server [list [namespace current]::InitDataConn $s] 0]} msg]
    if { $rc != 0 } {
        DisplayMsg $s "$msg" error
        return 0
    }

    # get a new local port address for data transfer and convert it to a format
    # which is useable by the PORT command

    set p [lindex [fconfigure $ftp(DummySock) -sockname] 2]
    if { $VERBOSE } {
        DisplayMsg $s "D: Port is $p" data
    }
    set ftp(DataPort) "[expr {$p / 256}],[expr {$p % 256}]"

    return 1
}

#############################################################################
#
# OpenPassiveConn --
#
# Opens a ftp data connection
# 
# Arguments:
# buffer - returned line from server control connection 
# 
# Returns:
# 0 -			no connection
# 1 - 			connection established

proc ::ftp::OpenPassiveConn {s buffer} {
    upvar ::ftp::ftp$s ftp

    if { [regexp -- {([0-9]+),([0-9]+),([0-9]+),([0-9]+),([0-9]+),([0-9]+)} $buffer all a1 a2 a3 a4 p1 p2] } {
        set ftp(LocalAddr) "$a1.$a2.$a3.$a4"
        set ftp(DataPort) "[expr {$p1 * 256 + $p2}]"

        # establish data connection for passive mode

        set rc [catch {set ftp(DataSock) [socket $ftp(LocalAddr) $ftp(DataPort)]} msg]
        if { $rc != 0 } {
            DisplayMsg $s "$msg" error
            return 0
        }

        InitDataConn $s $ftp(DataSock) $ftp(LocalAddr) $ftp(DataPort)
        return 1
    } else {
        return 0
    }
}

#############################################################################
#
# OpenControlConn --
#
# Opens a ftp control connection
# 
# Arguments:
#	s	connection id
#	block	blocking or non-blocking mode
# 
# Returns:
# 0 -			no connection
# 1 - 			connection established

proc ::ftp::OpenControlConn {s {block 1}} {
    upvar ::ftp::ftp$s ftp
    variable DEBUG
    variable VERBOSE

    # open a control channel

    set rc [catch {set ftp(CtrlSock) [socket $ftp(RemoteHost) $ftp(Port)]} msg]
    if { $rc != 0 } {
        if { $VERBOSE } {
            DisplayMsg $s "C: No connection to server!" error
        }
        if { $DEBUG } {
            DisplayMsg $s "[list $msg]" error
        }
        unset ftp(State)
        return 0
    }

    # configure control channel

    fconfigure $ftp(CtrlSock) -buffering line -blocking $block -translation {auto crlf}
    fileevent $ftp(CtrlSock) readable [list [namespace current]::StateHandler $s $ftp(CtrlSock)]
	
    # prepare local ip address for PORT command (convert pointed format
    # to comma format)

    set ftp(LocalAddr) [lindex [fconfigure $ftp(CtrlSock) -sockname] 0]
    set ftp(LocalAddr) [string map {. ,} $ftp(LocalAddr)]

    # report ready message

    set peer [fconfigure $ftp(CtrlSock) -peername]
    if { $VERBOSE } {
        DisplayMsg $s "C: Connection from [lindex $peer 0]:[lindex $peer 2]" control
    }
	
    return 1
}

# ::ftp::Command --
#
#	Wrapper for evaluated user-supplied command callback
#
# Arguments:
#	cb	callback script
#	msg	what happened
#	args	additional info
#
# Results:
#	Depends on callback script

proc ::ftp::Command {cb msg args} {
    if {[string length $cb]} {
	uplevel #0 $cb [list $msg] $args
    }
}

# ==================================================================
# ?????? Hmm, how to do multithreaded for tkcon?
# added TkCon support
# TkCon is (c) 1995-2001 Jeffrey Hobbs, http://tkcon.sourceforge.net/
# started with: tkcon -load ftp
if { [string equal [uplevel "#0" {info commands tkcon}] "tkcon"] } {

    # new ftp::List proc makes the output more readable
    proc ::ftp::__ftp_ls {args} {
        foreach i [eval ::ftp::List_org $args] {
            puts $i
        }
    }

    # rename the original ftp::List procedure
    rename ::ftp::List ::ftp::List_org

    alias ::ftp::List	::ftp::__ftp_ls
    alias bye		catch {::ftp::Close; exit}

    set ::ftp::VERBOSE 1
    set ::ftp::DEBUG 0
}

# ==================================================================
# At last, everything is fine, we can provide the package.

package provide ftp [lindex {Revision: 2.4.1} 1]

@rem Copyright (c) 2000-2006 ActiveState Software Inc.
@rem See the file LICENSE.txt for licensing information.

set PERL5DB=BEGIN { require 'perl5db.pl' }
set PERL5LIB=c:\mozilla_source\moz.26nov.winnt.release\mozilla\dist\WIN32_O.OBJ\bin\chrome\packages\komodo\komodo\content\perl
set PERLDB_OPTS=RemotePort=localhost:9010 RemoteIOPort=localhost:9011 CallKomodo=localhost:9000 PrintRet=0

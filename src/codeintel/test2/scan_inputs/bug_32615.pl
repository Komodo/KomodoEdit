sub autoupdate {
   # As an example -- $mandatorytext shows up as a global variable in the code browser,
   # as well as all four variables in the HTTP content split below
   return 1 unless ($Tk::platform eq 'MSWin32' && ($0 =~ /\.exe$/));
   no strict 'subs';
   my $onlyifmandatory = shift || 0; # This will be true if we are checking on login.
   $updating = 1;
   callbackwait(sub {
                     (http_get($appserver,
                               '/autoupdate/version.txt',
                              )) or
                        paladinmessage("The following error occurred while checking $appserver\n".
                                       "for an updated version of $appname:\n\n$HTTP{'error'}\n\n".
                                       "$appname will now exit, since it requires version information\n".
                                       "to function properly.") && exit 0;
                     $UI{'waitDialog'}->{'autoupdatewait'} = 0;
                    },
                \$UI{'waitDialog'}->{'autoupdatewait'},
                $onlyifmandatory ? 'Checking for mandatory update...':'Checking for update...',
               );

   my ($newestversion, $oldestversion, $releasedate, $description) = split(/\n/, $HTTP{'content'}, 4);
   if ($newestversion > $version) {
      if ($onlyifmandatory && ($version >= $oldestversion)) {
         $updating = 0;
         return 0;
      }
      my $mandatorytext = '';
      if ($version < $oldestversion) { # Mandatory update
         $mandatorytext = <<EndOfText;
This version is a MANDATORY update for all $appname
clients older than version $oldestversion.  Because you are running
$appname $version, $appname will exit if you answer "No" here.

EndOfText
      }
      if (paladinquestion(<<EndOfText)
$releasedate
$appname $newestversion is available!

${mandatorytext}Recent changes and additions:

$description

Would you like to download the upgrade now?
EndOfText
          eq 'Yes') {
         callbackwait(sub {
                           http_get($appserver,
                                    "/autoupdate/$appname-$newestversion",
                                    \&processupdate,
                                   ) or
                              paladinmessage("There was a problem downloading the update.\n".
                                             "Please try again later!");
                           close(DOWNLOAD);
                           $UI{'waitDialog'}->{'autoupdatewait'} = 0;
                          },
                      \$UI{'waitDialog'}->{'autoupdatewait'},
                      "Preparing to download update...",
                     );
      } else {
         if ($version < $oldestversion) {
            paladinmessage("Mandatory upgrade declined.\n$appname will exit now.");
            exit 0;
         }
         $updating = 0;
         return 0;
      }
      if ($HTTP{'error'}) {
         if ($version < $oldestversion) {
            paladinmessage("Mandatory upgrade download failed.\n$appname will exit now.");
            exit 0;
         }
         $updating = 0;
         return 0;
      }
      if ( -e "$progpath/_$progname" ) {
         paladinmessage(<<EndOfMessage
Update download complete!  Please be patient while
$appname version $newestversion restarts and performs
some final cleanup.  It may take a bit longer than
usual for it to start up.
EndOfMessage
                       );
      }
   }
   $updating = 0;
}

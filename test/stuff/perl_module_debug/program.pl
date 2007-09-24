# This is a happy little Perl program 
# which uses a module.  90% of our code
# resides in modules, so the ability
# to debug within modules is essential.

use module;  # My module is named "module."

$senses = {
             nose   => smell,
             eyes   => look,
             skin   => feel,
             tongue => taste,
             ears   => " um, er, hmmm...",
             };

foreach $sense_organ (keys(%$senses)) {
  print "\n";
  print &Make_Funny_Joke ($sense_organ, $senses->{$sense_organ});
  print "\n-------------------------------------\n\n";
}



# This is a module, in which I would like to 
# set a breakpoint.
#
# The joke appears to be on -me-.
#
sub Make_Funny_Joke
{
  my ($organ, $function) = (@_);
  
  # IF you set a breakpoint in this function, Komodo 
  # seems to acknowledge it by putting a green dot in the 
  # margin.  Only thing is: The program doesn't seem to 
  # "heed" the breakpoint.
  # In my code, I get a different symptom.  I get this error:
  #
  #    "Can't find unicode character property definition via main->b or b.pl at unicode/Is/b.pl line 0"
  #
  # I get this message when I have breakpoints in my module, and I 
  # don't get this message when I take away the breakpoint.
  #
  # In this simple example program, I don't get an error message--
  # but I don't get a breakpoint, either.  Something's fishy with
  # breakpoints in modules.

  my $joke  =  "Ike :  I once had a little dog who had no $organ.\n";
     $joke .=  "Mike:  How did he $function?\n";
     $joke .=  "Ike :  Awful!";

  return $joke;
}

" Why must modules return truth?  What is truth?  This!  This must be the truth!";
1;
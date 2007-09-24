sub CheckOnly
{
    my ($section, $line, $input) = @_;
    my (@results,$tmpSection);
    
    $tmpSection = $section;
    $tmpSection =~ /tcno/i;
    my($premsg) = $`;
    my($search) = $&;
    my($postmsg) = $';
    $tmpSection = $search . $postmsg;
    if($tmpSection =~ /check-run-wait/i)
    {
        if($tmpSection =~ /Windows/i)
        {
            $tmpSection =~ /check-run-wait /i;
            $premsg = $`;
            $search = $&;
         }
    }
} 


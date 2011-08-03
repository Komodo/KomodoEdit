
###############################################################################
##                                                                           ##
##    Copyright (c) 1995 - 2002 by Steffen Beyer.                            ##
##    All rights reserved.                                                   ##
##                                                                           ##
##    This package is free software; you can redistribute it                 ##
##    and/or modify it under the same terms as Perl itself.                  ##
##                                                                           ##
###############################################################################

package Date::Calc;

use strict;
use vars qw(@ISA @EXPORT @EXPORT_OK %EXPORT_TAGS $VERSION);

require Exporter;
require DynaLoader;

@ISA = qw(Exporter DynaLoader);

@EXPORT = qw();

@EXPORT_OK = qw(
    Days_in_Year
    Days_in_Month
    Weeks_in_Year
    leap_year
    check_date
    check_time
    check_business_date
    Day_of_Year
    Date_to_Days
    Day_of_Week
    Week_Number
    Week_of_Year
    Monday_of_Week
    Nth_Weekday_of_Month_Year
    Standard_to_Business
    Business_to_Standard
    Delta_Days
    Delta_DHMS
    Delta_YMD
    Delta_YMDHMS
    Normalize_DHMS
    Add_Delta_Days
    Add_Delta_DHMS
    Add_Delta_YM
    Add_Delta_YMD
    Add_Delta_YMDHMS
    System_Clock
    Today
    Now
    Today_and_Now
    This_Year
    Gmtime
    Localtime
    Mktime
    Timezone
    Date_to_Time
    Time_to_Date
    Easter_Sunday
    Decode_Month
    Decode_Day_of_Week
    Decode_Language
    Decode_Date_EU
    Decode_Date_US
    Fixed_Window
    Moving_Window
    Compress
    Uncompress
    check_compressed
    Compressed_to_Text
    Date_to_Text
    Date_to_Text_Long
    English_Ordinal
    Calendar
    Month_to_Text
    Day_of_Week_to_Text
    Day_of_Week_Abbreviation
    Language_to_Text
    Language
    Languages
    Decode_Date_EU2
    Decode_Date_US2
    Parse_Date
    ISO_LC
    ISO_UC
);

%EXPORT_TAGS = (all => [@EXPORT_OK]);

##################################################
##                                              ##
##  "Version()" is available but not exported   ##
##  in order to avoid possible name clashes.    ##
##  Call with "Date::Calc::Version()" instead!  ##
##                                              ##
##################################################

$VERSION = '5.3';

bootstrap Date::Calc $VERSION;

sub Decode_Date_EU2
{
    die "Usage: (\$year,\$month,\$day) = Decode_Date_EU2(\$date);\n"
      if (@_ != 1);

    my($buffer) = @_;
    my($year,$month,$day,$length);

    if ($buffer =~ /^\D*  (\d+)  [^A-Za-z0-9\xC0-\xD6\xD8-\xF6\xF8-\xFF]*  ([A-Za-z\xC0-\xD6\xD8-\xF6\xF8-\xFF]+)  [^A-Za-z0-9\xC0-\xD6\xD8-\xF6\xF8-\xFF]*  (\d+)  \D*$/x)
    {
        ($day,$month,$year) = ($1,$2,$3);
        $month = Decode_Month($month);
        unless ($month > 0)
        {
            return(); # can't decode month!
        }
    }
    elsif ($buffer =~ /^\D*  0*(\d+)  \D*$/x)
    {
        $buffer = $1;
        $length = length($buffer);
        if    ($length == 3)
        {
            $day   = substr($buffer,0,1);
            $month = substr($buffer,1,1);
            $year  = substr($buffer,2,1);
        }
        elsif ($length == 4)
        {
            $day   = substr($buffer,0,1);
            $month = substr($buffer,1,1);
            $year  = substr($buffer,2,2);
        }
        elsif ($length == 5)
        {
            $day   = substr($buffer,0,1);
            $month = substr($buffer,1,2);
            $year  = substr($buffer,3,2);
        }
        elsif ($length == 6)
        {
            $day   = substr($buffer,0,2);
            $month = substr($buffer,2,2);
            $year  = substr($buffer,4,2);
        }
        elsif ($length == 7)
        {
            $day   = substr($buffer,0,1);
            $month = substr($buffer,1,2);
            $year  = substr($buffer,3,4);
        }
        elsif ($length == 8)
        {
            $day   = substr($buffer,0,2);
            $month = substr($buffer,2,2);
            $year  = substr($buffer,4,4);
        }
        else { return(); } # wrong number of digits!
    }
    elsif ($buffer =~ /^\D*  (\d+)  \D+  (\d+)  \D+  (\d+)  \D*$/x)
    {
        ($day,$month,$year) = ($1,$2,$3);
    }
    else { return(); } # no match at all!
    $year = Moving_Window($year);
    if (check_date($year,$month,$day))
    {
        return($year,$month,$day);
    }
    else { return(); } # not a valid date!
}

sub Decode_Date_US2
{
    die "Usage: (\$year,\$month,\$day) = Decode_Date_US2(\$date);\n"
      if (@_ != 1);

    my($buffer) = @_;
    my($year,$month,$day,$length);

    if ($buffer =~ /^[^A-Za-z0-9\xC0-\xD6\xD8-\xF6\xF8-\xFF]*  ([A-Za-z\xC0-\xD6\xD8-\xF6\xF8-\xFF]+)  [^A-Za-z0-9\xC0-\xD6\xD8-\xF6\xF8-\xFF]*  0*(\d+)  \D*$/x)
    {
        ($month,$buffer) = ($1,$2);
        $month = Decode_Month($month);
        unless ($month > 0)
        {
            return(); # can't decode month!
        }
        $length = length($buffer);
        if    ($length == 2)
        {
            $day  = substr($buffer,0,1);
            $year = substr($buffer,1,1);
        }
        elsif ($length == 3)
        {
            $day  = substr($buffer,0,1);
            $year = substr($buffer,1,2);
        }
        elsif ($length == 4)
        {
            $day  = substr($buffer,0,2);
            $year = substr($buffer,2,2);
        }
        elsif ($length == 5)
        {
            $day  = substr($buffer,0,1);
            $year = substr($buffer,1,4);
        }
        elsif ($length == 6)
        {
            $day  = substr($buffer,0,2);
            $year = substr($buffer,2,4);
        }
        else { return(); } # wrong number of digits!
    }
    elsif ($buffer =~ /^[^A-Za-z0-9\xC0-\xD6\xD8-\xF6\xF8-\xFF]*  ([A-Za-z\xC0-\xD6\xD8-\xF6\xF8-\xFF]+)  [^A-Za-z0-9\xC0-\xD6\xD8-\xF6\xF8-\xFF]*  (\d+)  \D+  (\d+)  \D*$/x)
    {
        ($month,$day,$year) = ($1,$2,$3);
        $month = Decode_Month($month);
        unless ($month > 0)
        {
            return(); # can't decode month!
        }
    }
    elsif ($buffer =~ /^\D*  0*(\d+)  \D*$/x)
    {
        $buffer = $1;
        $length = length($buffer);
        if    ($length == 3)
        {
            $month = substr($buffer,0,1);
            $day   = substr($buffer,1,1);
            $year  = substr($buffer,2,1);
        }
        elsif ($length == 4)
        {
            $month = substr($buffer,0,1);
            $day   = substr($buffer,1,1);
            $year  = substr($buffer,2,2);
        }
        elsif ($length == 5)
        {
            $month = substr($buffer,0,1);
            $day   = substr($buffer,1,2);
            $year  = substr($buffer,3,2);
        }
        elsif ($length == 6)
        {
            $month = substr($buffer,0,2);
            $day   = substr($buffer,2,2);
            $year  = substr($buffer,4,2);
        }
        elsif ($length == 7)
        {
            $month = substr($buffer,0,1);
            $day   = substr($buffer,1,2);
            $year  = substr($buffer,3,4);
        }
        elsif ($length == 8)
        {
            $month = substr($buffer,0,2);
            $day   = substr($buffer,2,2);
            $year  = substr($buffer,4,4);
        }
        else { return(); } # wrong number of digits!
    }
    elsif ($buffer =~ /^\D*  (\d+)  \D+  (\d+)  \D+  (\d+)  \D*$/x)
    {
        ($month,$day,$year) = ($1,$2,$3);
    }
    else { return(); } # no match at all!
    $year = Moving_Window($year);
    if (check_date($year,$month,$day))
    {
        return($year,$month,$day);
    }
    else { return(); } # not a valid date!
}

sub Parse_Date
{
    die "Usage: (\$year,\$month,\$day) = Parse_Date(\$date);\n"
      if (@_ != 1);

    my($date) = @_;
    my($year,$month,$day);
    unless ($date =~ /\b([JFMASOND][aepuco][nbrynlgptvc])\s+([0123]??\d)\b/)
    {
        return();
    }
    $month = $1;
    $day   = $2;
    unless ($date =~ /\b(19\d\d|20\d\d)\b/)
    {
        return();
    }
    $year  = $1;
    $month = Decode_Month($month);
    unless ($month > 0)
    {
        return();
    }
    unless (check_date($year,$month,$day))
    {
        return();
    }
    return($year,$month,$day);
}

1;

__END__


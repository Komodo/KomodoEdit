#!/usr/bin/perl -w
use strict;

use DBI;

# Connect to database (a MySQL database in this example)
use DBI;
my $database = "...";
my $dsn = "DBI:mysql:database=$database;mysql_read_default_group=client";
my $user = "mysql";
my $pass = undef; # Get password from /etc/my.cnf config file
my $dbh = DBI->connect($dsn, $user, $pass,
                       {'RaiseError' => 1});
if (!$dbh) {
    die "Can't connect to $dsn: $!";
}

# Prepare statement for execution
my $sth = $dbh->prepare("SELECT * FROM Products");

# Execute statement
$sth->execute;

# Retrieve all rows produced by statement execution
while (my @row = $sth->fetchrow_array) {

    # Print name and value of each field in this record
    printf "%-20s : %s\n", $sth->{NAME}->[$_], $row[$_] for 0..@row-1;
    print "\n";
}

# Disconnect database connection
$dbh->disconnect;

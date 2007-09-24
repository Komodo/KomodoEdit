package WF_Support;

=head1 SYNOPSIS

use WF_Support;

=head1 DESCRIPTION

Es wird eine Reihe unterstützender Routinen bereitgestellt. Gleichzeitig dazu erfolgt die Archivierung der Konfigurationsdateien.

=cut

=head2 read_matrixkeys

    @keys = @{read_matrixkeys($config_file, $tag)};

Liest Matrixzeilenschlüssel ein.
Datenformat: rowkey | colid_1;value_1 | colid_2;value_2 | ... | colid_n;value_n

=cut

sub read_matrixkeys
    {
     use READ_CFG; # Lesen von Konfigurationsdateien

     # Parameter übernehmen
     my ($wf_config_file, $tag) = @_;

 }

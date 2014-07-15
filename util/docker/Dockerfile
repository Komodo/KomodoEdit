FROM     ubuntu:12.04

# make sure the package repository is up to date
RUN apt-get update

RUN apt-get install -y light-themes git vim zip unzip mercurial g++ make autoconf2.13 yasm libgtk2.0-dev libglib2.0-dev libdbus-1-dev libdbus-glib-1-dev libasound2-dev libcurl4-openssl-dev libiw-dev libxt-dev mesa-common-dev libgstreamer0.10-dev libgstreamer-plugins-base0.10-dev libpulse-dev

RUN apt-get install -y openssh-server
RUN mkdir /var/run/sshd

# make the ssh port available
EXPOSE 22
ADD id_rsa.pub /root/.ssh/authorized_keys
RUN chown root:root /root/.ssh/authorized_keys

#ADD komodo /root/komodo/

# start the ssh daemon
CMD ["/usr/sbin/sshd", "-D"]

# Set default config
RUN echo "PATH=/root/komodo/util/black:\$PATH" >> /root/.bashrc
RUN echo "include \"/usr/share/themes/Radiance/gtk-2.0/gtkrc\"" > /root/.gtkrc-2.0
RUN gconftool-2 --type=string --set /desktop/gnome/interface/gtk_theme "Radiance"

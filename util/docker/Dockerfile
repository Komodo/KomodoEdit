FROM     ubuntu:16.04

# make sure the package repository is up to date
RUN apt-get update --fix-missing
RUN apt-get upgrade -y

RUN apt-get install -y libcanberra-gtk-module sudo light-themes git vim zip unzip mercurial g++ make autoconf2.13 yasm libgtk2.0-dev libglib2.0-dev libdbus-1-dev libdbus-glib-1-dev libasound2-dev libcurl4-openssl-dev libiw-dev libxt-dev mesa-common-dev libgstreamer0.10-dev libgstreamer-plugins-base0.10-dev libpulse-dev libffi-dev python-setuptools openssh-server python-dev libssl-dev

# Ubuntu 16 uses gcc 5, but we want gcc 4
RUN apt-get remove -y gcc cpp g++-5
RUN apt-get install -y gcc-4.9 g++-4.9
RUN update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-4.9 100
RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-4.9 100
RUN update-alternatives --install /usr/bin/cpp cpp /usr/bin/cpp-4.9 100

RUN ln -s /usr/bin/gcc /usr/bin/x86_64-linux-gnu-gcc

RUN easy_install pyOpenSSL ndg-httpsclient pyasn1

RUN mkdir /var/run/sshd

# make the ssh port available
EXPOSE 22
ADD id_rsa.pub /root/.ssh/authorized_keys
RUN chown root:root /root/.ssh/authorized_keys
ADD id_rsa.pub /root/.ssh/authorized_keys2
RUN chown root:root /root/.ssh/authorized_keys2

# start the ssh daemon
CMD ["/usr/sbin/sshd", "-D"]

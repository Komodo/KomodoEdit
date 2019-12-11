FROM     ubuntu:17.04

# make sure the package repository is up to date
RUN sed 's/archive/old-releases/g' /etc/apt/sources.list > /tmp/out && cp /tmp/out /etc/apt/sources.list
RUN apt-get update --fix-missing; exit 0
#RUN apt-get upgrade -y

RUN apt-get install -y sudo git vim zip \
        unzip mercurial g++ make autoconf2.13 yasm libgtk2.0-dev libglib2.0-dev \
        libdbus-1-dev libdbus-glib-1-dev libasound2-dev libcurl4-openssl-dev \
        libiw-dev libxt-dev mesa-common-dev libpulse-dev libffi-dev python-setuptools \
        openssh-server python-dev libssl-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
        build-essential

# Ubuntu 17.04 uses gcc 6, but we want gcc 4
RUN apt-get remove -y gcc cpp g++ gcc-6 cpp-6 g++-6
RUN apt-get install -y gcc-4.9 g++-4.9
RUN update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-4.9 100
RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-4.9 100
RUN update-alternatives --install /usr/bin/cpp cpp /usr/bin/cpp-4.9 100

RUN ln -s /usr/bin/gcc /usr/bin/x86_64-linux-gnu-gcc

RUN easy_install pyOpenSSL ndg-httpsclient pyasn1

RUN mkdir /var/run/sshd

# Install Perl 5.22
RUN wget https://activestar-installers.s3.us-east-2.amazonaws.com/ActivePerl-5.22.4.2205-x86_64-linux-glibc-2.15-403863.tar.gz
RUN tar -xzf ActivePerl-5.22.4.2205-x86_64-linux-glibc-2.15-403863.tar.gz
#RUN sed -i 's/perl\/bin\/perl/.\/perl\/bin\/perl/' ActivePerl-5.22.4.2205-x86_64-linux-glibc-2.15-403863/install.sh
RUN cd ActivePerl-5.22.4.2205-x86_64-linux-glibc-2.15-403863 && ./install.sh --license-accepted --no-update-check --no-komodo --no-install-html --prefix /opt/ActivePerl

#RUN \curl -L https://install.perlbrew.pl | bash
#RUN /bin/bash -c "source /root/perl5/perlbrew/etc/bashrc && source /root/.bashrc && perlbrew install 5.22.4 -n --noman -j 5 -Dcc=gcc"
#; exit 0
#RUN tail /root/perl5/perlbrew/build.perl-5.22.4.log; exit 1

# make the ssh port available
EXPOSE 22
ADD id_rsa.pub /root/.ssh/authorized_keys
RUN chown root:root /root/.ssh/authorized_keys
ADD id_rsa.pub /root/.ssh/authorized_keys2
RUN chown root:root /root/.ssh/authorized_keys2

# start the ssh daemon
CMD ["/usr/sbin/sshd", "-D"]

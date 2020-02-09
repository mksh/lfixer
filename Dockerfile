FROM debian:buster

RUN apt-get update && apt-get -y install python3 sudo
RUN useradd runner

COPY out/python3-lfixer_0.1-1_all.deb /opt/python3-lfixer_0.1-1_all.deb
RUN dpkg -i /opt/python3-lfixer_0.1-1_all.deb

HEALTHCHECK --interval=30s --timeout=5s CMD /usr/bin/log-fixer-healthcheck.sh /tmp/progress.db

ENTRYPOINT ["/usr/bin/sudo", "-u", "runner", "/usr/bin/log-fixer.py", "--progress-db-location=/tmp/progress.db"]

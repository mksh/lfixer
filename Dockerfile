FROM debian:buster

ARG VERSION

RUN apt-get update && apt-get -y install python3
RUN useradd runner

COPY out/python3-lfixer_${VERSION}-1_all.deb /opt/python3-lfixer_${VERSION}-1_all.deb
RUN dpkg -i /opt/python3-lfixer_${VERSION}-1_all.deb

HEALTHCHECK --interval=30s --timeout=5s CMD /usr/bin/log-fixer-healthcheck.sh /tmp/progress.db

USER runner
ENTRYPOINT ["/usr/bin/log-fixer.py", "--progress-db-location=/tmp/progress.db"]

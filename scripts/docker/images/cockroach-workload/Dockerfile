FROM cockroachdb/cockroach:v23.1.2

RUN microdnf install time nc

ADD entrypoint.sh /

ENTRYPOINT [ "/entrypoint.sh"]

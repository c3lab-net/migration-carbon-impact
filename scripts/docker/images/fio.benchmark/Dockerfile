FROM gitlab-registry.nrp-nautilus.io/c3lab/common/fio:3.33
MAINTAINER Yibo Guo <nil.yibo@gmail.com>

ADD fio.benchmark.sh /
RUN chmod u+x /fio.benchmark.sh

ENTRYPOINT [ "/fio.benchmark.sh" ]

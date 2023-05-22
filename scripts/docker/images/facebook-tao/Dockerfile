FROM ubuntu:20.04
MAINTAINER Yibo Guo <nil.yibo@gmail.com>

RUN apt-get update
RUN apt-get install -y software-properties-common
RUN add-apt-repository -y ppa:ubuntu-toolchain-r/test
RUN apt-get install -y build-essential cmake g++-11
RUN apt-get install -y git time

RUN apt-get install -y libpq-dev postgresql

RUN tmpdir=$(mktemp -d) && cd $tmpdir && \
    git clone https://github.com/jtv/libpqxx.git libpqxx && cd libpqxx && \
    ./configure CXX=g++-11 && make -j $(nproc) && make install && \
    cd / && rm -rf $tmpdir

ADD taobench /taobench
WORKDIR /taobench
RUN mkdir build && cd build && \
    cmake .. -DWITH_CRDB=ON && make -j $(nproc)

WORKDIR /taobench/build

ENTRYPOINT [ "bash"]

# Source: https://raw.githubusercontent.com/opencoconut/ffmpeg/master/Dockerfile

FROM alpine:3.17.2
MAINTAINER Yibo Guo <nil.yibo@gmail.com>

ARG FFMPEG_VERSION=5.1.2
ARG TMPDIR=/tmp/ffmpeg-build

RUN apk add --update build-base curl nasm tar bzip2 \
    zlib-dev openssl-dev yasm-dev lame-dev libogg-dev x264-dev libvpx-dev \
    libvorbis-dev x265-dev freetype-dev libass-dev libwebp-dev rtmpdump-dev \
    libtheora-dev opus-dev

WORKDIR ${TMPDIR}
RUN curl -s http://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.gz | tar zxvf - -C .

WORKDIR ${TMPDIR}/ffmpeg-${FFMPEG_VERSION}
RUN ./configure \
    --enable-version3 --enable-gpl --enable-nonfree --enable-small --enable-libmp3lame --enable-libx264 \
    --enable-libx265 --enable-libvpx --enable-libtheora --enable-libvorbis --enable-libopus --enable-libass \
    --enable-libwebp --enable-librtmp --enable-postproc --enable-libfreetype --enable-openssl --disable-debug
RUN make && \
    make install && \
    make distclean

WORKDIR /
RUN rm -rf ${TMPDIR} && \
    apk del build-base curl tar bzip2 x264 openssl nasm && rm -rf /var/cache/apk/*

ENTRYPOINT ["ffmpeg"]


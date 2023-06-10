#!/bin/zsh

cd "$(dirname "$0")"

mkdir -p ~/opt && cd ~/opt

set -e

VER=v22.2.10

wget --quiet https://binaries.cockroachdb.com/cockroach-$VER.linux-amd64.tgz
wget --quiet https://binaries.cockroachdb.com/cockroach-$VER.linux-amd64.tgz.sha256sum
shasum -c *.sha256sum

tar zxf cockroach-$VER.linux-amd64.tgz
rm cockroach-$VER.linux-amd64.tgz*

echo -n "cockroach binary installed at:"
find . -type f -name cockroach -exec realpath {} \;


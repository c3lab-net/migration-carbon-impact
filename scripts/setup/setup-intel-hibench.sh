#!/bin/zsh

set -e
# set -x

# Source: https://github.com/Intel-bigdata/HiBench/blob/master/docs/build-hibench.md

# Java 11 throws strange error in mvn build process, so change to java 8.
sudo apt-get remove --purge openjdk-11-'*'
sudo apt-get install -y openjdk-8-jdk

# Dependency #1: mvn
sudo apt update
sudo apt install -y maven

# Dependency #2: scala
#   May not be necessary because Spark 3 comes with Scala.
# sudo apt install -y default-jdk scala

# Dependency #3: spark
#   From https://spark.apache.org/downloads.html
#   Selected Spark 3.0.x and Hadoop 2.7 per https://github.com/Intel-bigdata/HiBench/blob/master/docs/run-sparkbench.md
wget https://dlcdn.apache.org/spark/spark-3.0.3/spark-3.0.3-bin-hadoop2.7.tgz
wget https://downloads.apache.org/spark/spark-3.0.3/spark-3.0.3-bin-hadoop2.7.tgz.sha512
cat spark-3.0.3-bin-hadoop2.7.tgz.sha512 | tr '\n' ' ' | sed 's/ //g' | awk -F ':' '{print tolower($2), $1}' | sha512sum -c - | grep OK
[ $? -eq 0 ] || { echo >&2 "Spark checksum failed"; exit 1 }
rm spark-3.0.3-bin-hadoop2.7.tgz.sha512

mkdir -p ~/opt
tar zxf spark-3.0.3-bin-hadoop2.7.tgz -C ~/opt/
rm spark-3.0.3-bin-hadoop2.7.tgz

export SPARK_DIR="$HOME/opt/spark-3.0.3-bin-hadoop2.7"

echo """
export SPARK_HOME="$SPARK_DIR"
export PATH=\$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
export PYSPARK_PYTHON=/usr/bin/python3
""" >> ~/.zshrc

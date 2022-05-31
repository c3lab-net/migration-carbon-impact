#!/bin/zsh

set -e
# set -x

# Source: https://github.com/Intel-bigdata/HiBench/blob/master/docs/build-hibench.md

function download_and_extract_apache_software()
{
    suburl="$1"
    dstdir="$2"

    set -e
    pushd "$(mktemp -d)"

    echo "Downloading and verifying apache software from \"$suburl\" ..."
    prefix="${suburl%/*}"
    filename="${suburl##*/}"
    mainfile="$filename"
    checksumfile="$filename.sha512"
    url_mainfile="https://dlcdn.apache.org/$prefix/$mainfile"
    url_checksum="https://dlcdn.apache.org/$prefix/$checksumfile"
    (set -x; wget $url_mainfile)
    (set -x; wget $url_checksum)
    cat "$checksumfile" | tr '\n' ' ' | sed 's/ //g' | awk -F ':' '{print tolower($2), $1}' | sha512sum -c - | grep OK
    [ $? -eq 0 ] || { echo >&2 "Checksum failed"; exit 1 }

    # echo "Extracting to \"$dstdir\" ..."
    (set -x; tar zxf "$mainfile" -C "$dstdir")

    rm *

    popd
}

# Java 11 throws strange error in mvn build process, so change to java 8.
sudo apt-get remove --purge openjdk-11-'*'
sudo apt-get install -y openjdk-8-jdk

# Dependency #1: mvn
sudo apt-get update
sudo apt-get install -y maven

# Dependency #2: scala
#   May not be necessary because Spark 3 comes with Scala.
sudo apt-get install -y scala

java -version; javac -version; scala -version; git --version

# prepare install directory for Hadoop and Spark
INSTALL_DIR="$HOME/opt"
mkdir -p "$INSTALL_DIR"

# Dependency #3: Hadoop
sudo apt-get install -y ssh rsync
HADOOP_SUBURL="hadoop/common/hadoop-2.10.1/hadoop-2.10.1.tar.gz"
download_and_extract_apache_software "$HADOOP_SUBURL" "$INSTALL_DIR"

HADOOP_NAMENODE="yeti-09"
typeset -a HADOOP_DATANODES
HADOOP_DATANODES=(
    "yeti-02"
    "yeti-03"
)
typeset -A NODE_IPs
NODE_IPs["yeti-02"]="10.0.0.2"
NODE_IPs["yeti-03"]="10.0.0.3"
NODE_IPs["yeti-09"]="10.0.0.9"

## Setup Hadoop
function setup_hadoop_java()
{
    # Source: https://www.digitalocean.com/community/tutorials/how-to-install-hadoop-in-stand-alone-mode-on-ubuntu-20-04
    echo >&2 "Setting JAVA_HOME in Hadoop config and testing hadoop ..."
    HADOOP_NAME="${${HADOOP_SUBURL##*/}%.tar.gz}"
    export HADOOP_DIR="$INSTALL_DIR/$HADOOP_NAME"
    JAVA_HOME=$(readlink -f /usr/bin/java | sed "s:bin/java::")
    sed -i 's|^export JAVA_HOME=.*|export JAVA_HOME='"$JAVA_HOME"'|' "$HADOOP_DIR/etc/hadoop/hadoop-env.sh"
    $HADOOP_DIR/bin/hadoop > /dev/null
    [ $? -eq 0 ] || { echo >&2 "Failed to install Hadoop ..."; exit 1}
    echo >&2 "Done"
}

function test_hadoop_standalone()
{
    echo >&2 "Testing standalone Hadoop operations ..."
    pushd "$(mktemp -d)"
    mkdir input
    cp $HADOOP_DIR/etc/hadoop/*.xml input/
    hadoop_output="$($HADOOP_DIR/bin/hadoop jar $HADOOP_DIR/share/hadoop/mapreduce/hadoop-mapreduce-examples-2.10.1.jar grep input output 'dfs[a-z.]+' 2>&1)"
    [ $? -eq 0 ] || { echo >&2 "Failed to run Hadoop example ..."; exit 1}
    echo "$hadoop_output" | grep Exception > /dev/null
    [ $? -eq 1 ] || { echo >&2 "Exception occurred while running Hadoop example ..."; exit 1}
    cat output/*
    popd
    echo >&2 "Done"
}

function setup_pseudo_distributed()
{
    echo >&2 "Enabling pseudo-distributed mode on a single node ..."
    sed -i "/<configuration>/r"<(echo """    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://$HADOOP_NAMENODE:8020</value>
    </property>""") -- $HADOOP_DIR/etc/hadoop/core-site.xml
    sed -i "/<configuration>/r"<(echo """    <property>
        <name>dfs.replication</name>
        <value>1</value>
    </property>""") -- $HADOOP_DIR/etc/hadoop/hdfs-site.xml
    echo >&2 "Done"
}

function setup_hostname_mapping()
{
    typeset -A hosts_ip_mapping
    hosts_ip_mapping["hadoop-namenode"]="${NODE_IPs["$HADOOP_NAMENODE"]}"
    hosts_ip_mapping["hadoop-resourcemanager"]="${NODE_IPs["$HADOOP_NAMENODE"]}"
    datanode_id=1
    print -l $HADOOP_DATANODES
    print -l $NODE_IPs
    for datanode in "${(@)HADOOP_DATANODES}"; do
        hosts_ip_mapping["hadoop-datanode$datanode_id"]="${NODE_IPs["$datanode"]}"
        datanode_id=$((datanode_id + 1))
    done

    for host ip in "${(@kv)hosts_ip_mapping}"; do
        echo "host: $host, ip: $ip"
        sudo sh -c "echo $ip $host >> /etc/hosts"
    done
}

function enable_passwordless_ssh()
{
    echo >&2 "Testing passwordless ssh. Please enter yes at ssh prompts ..."
    for node in "$HADOOP_NAMENODE" "${HADOOP_DATANODES[@]}"; do
        ssh $node -f ':'
        [ $? -eq 0 ] || { echo >&2 "Failed to ssh to localhost."; exit 1 }
    done
    echo >&2 "Done"
}

function test_hdfs()
{
    echo >&2 "Testing HDFS with simple MapReduce job ..."
    $HADOOP_DIR/bin/hdfs namenode -format
    $HADOOP_DIR/sbin/start-dfs.sh
    $HADOOP_DIR/bin/hdfs dfs -mkdir /user
    $HADOOP_DIR/bin/hdfs dfs -mkdir /user/$USER
    $HADOOP_DIR/bin/hdfs dfs -put etc/hadoop input
    $HADOOP_DIR/bin/hadoop jar share/hadoop/mapreduce/hadoop-mapreduce-examples-2.10.1.jar grep input output 'dfs[a-z.]+'
    hdfs_output="$($HADOOP_DIR/bin/hdfs dfs -cat output/'*')"
    $HADOOP_DIR/sbin/stop-dfs.sh
    [ "$(echo "$hdfs_output" | wc -l)" -gt 1 ] || { echo "No output file in HDFS."; exit 1 }
    echo >&2 "Done"
}

function setup_yarn_single_node()
{
    echo >&2 "Enabling YARN on a Single Node ..."
    echo """<configuration>
    <property>
        <name>mapreduce.framework.name</name>
        <value>yarn</value>
    </property>
</configuration>""" > $HADOOP_DIR/etc/hadoop/mapred-site.xml
    sed -i "/<configuration>/r"<(echo """    <property>
        <name>yarn.nodemanager.aux-services</name>
        <value>mapreduce_shuffle</value>
    </property>""") -- $HADOOP_DIR/etc/hadoop/hdfs-site.xml
    $HADOOP_DIR/sbin/start-yarn.sh
    echo >&2 "Done"
    $HADOOP_DIR/sbin/stop-yarn.sh
}

function setup_hadoop()
{
    set -e
    setup_hadoop_java

    # # Source: https://hadoop.apache.org/docs/r2.10.1/hadoop-project-dist/hadoop-common/SingleCluster.html
    test_hadoop_standalone
    setup_pseudo_distributed
    setup_hostname_mapping
    enable_passwordless_ssh

    test_hdfs

    setup_yarn_single_node
}

setup_hadoop

# Dependency #4: Spark
#   From https://spark.apache.org/downloads.html
#   Selected Spark 3.0.x and Hadoop 2.7 per https://github.com/Intel-bigdata/HiBench/blob/master/docs/run-sparkbench.md
# download_and_extract_apache_software "spark/spark-3.0.3/spark-3.0.3-bin-hadoop2.7.tgz" "$HOME/opt"
download_and_extract_apache_software "spark/spark-3.0.3/spark-3.0.3-bin-without-hadoop.tgz" "$HOME/opt"

export SPARK_DIR="$HOME/opt/spark-3.0.3-bin-hadoop2.7"

echo """
export SPARK_HOME="$SPARK_DIR"
export PATH=\$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
export PYSPARK_PYTHON=/usr/bin/python3
""" >> ~/.zshrc

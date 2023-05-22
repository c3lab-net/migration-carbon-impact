FROM python:3.10-slim-bullseye

ARG REPO_DIR=/carboncast

RUN apt-get update
RUN apt-get install -y git curl
RUN apt-get install -y make cmake gcc gfortran

RUN git clone https://github.com/carbonfirst/CarbonCast.git ${REPO_DIR}

WORKDIR ${REPO_DIR}

# Install dependencies
# Source: https://github.com/carbonfirst/CarbonCast#41-installing-dependencies

## python modules
RUN pip3 install -U -r requirements.txt

WORKDIR ${REPO_DIR}/src

## wgrib2 (for weather data)
# Source: https://www.cpc.ncep.noaa.gov/products/wesley/wgrib2/compile_questions.html
RUN curl -o wgrib2.tgz https://ftp.cpc.ncep.noaa.gov/wd51we/wgrib2/wgrib2.tgz
RUN tar zxvf wgrib2.tgz && rm wgrib2.tgz
RUN cd grib2 && CC=gcc FC=gfortran make

CMD [ "bash" ]

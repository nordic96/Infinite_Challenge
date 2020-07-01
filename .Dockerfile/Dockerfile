FROM ubuntu:18.04
MAINTAINER Gihun Ko
RUN apt-get update
RUN apt-get install -y python3-pip
WORKDIR ./
RUN pip3 install -r requirements.txt
EXPOSE 80
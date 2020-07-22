# Last updated: 10 July 2020
FROM python:3.7-slim
RUN apt-get -y update && \
    apt-get install -y --fix-missing \
    curl \
    gnupg && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update -y && \
    ACCEPT_EULA=Y apt-get install -y --fix-missing \
    build-essential \
    libsm6 \
    libxext6 \
    libxrender-dev \
    msodbcsql17 \
    pkg-config \
    python3-numpy \
    unixodbc-dev
COPY requirements.txt /requirements.txt
RUN pip3 install -r /requirements.txt
ADD infinitechallenge /infinite/infinitechallenge
ADD resources /infinite/resources
ADD docker_entrypoint.sh /infinite/docker_entrypoint.sh
WORKDIR /infinite
RUN ["chmod", "+x", "/infinite/docker_entrypoint.sh"]
ENTRYPOINT ["/infinite/docker_entrypoint.sh"]

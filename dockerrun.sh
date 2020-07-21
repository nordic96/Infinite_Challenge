#!/bin/bash

HOST_DIRECTORY= # abs path of directory containing external files (credentials.json, token.pickle, config file)
CONFIG_FILENAME=default.ini  #file name of config file to use, should be in the root directory of the specified host directory
EPISODE_FILENAME= # episode filename (e.g. episode1.mp4, or episode231.avi)
DOCKER_IMAGE= #docker image

docker run \
  --rm \
  -e IC_RDS_PASSWORD= \
  -e IC_AZURE_KEY_SKULL= \
  -e IC_AZURE_KEY_FACE= \
  -e IC_GDRIVE_AUTH_TOKEN_PATH=/external/token.pickle \
  -e IC_GDRIVE_CLIENT_SECRETS_PATH=/external/credentials.json \
  --mount type=bind,source=$HOST_DIRECTORY,target=/external \
  $DOCKER_IMAGE /external/$CONFIG_FILENAME $EPISODE_FILENAME

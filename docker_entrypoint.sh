#!/bin/bash
MOUNTED_VOLUME_PATH=/external
if [ ! -d "$MOUNTED_VOLUME_PATH" ]; then
  echo "[ERROR] No external volume mounted at $MOUNTED_VOLUME_PATH"
  exit 1
fi
echo '[EXTERNAL]'
ls -l /external
echo '[EXTERNAL]'

CONFIG_FILE_PATH=$1
if [ ! -f "$CONFIG_FILE_PATH" ]; then
  echo "[WARNING] Specified configuration file '$CONFIG_FILE_PATH' does not exist. Default configuration will be used."

  CONFIG_FILE_PATH=resources/default.ini
  if [ ! -f "$CONFIG_FILE_PATH" ]; then
    echo "[ERROR] Default configuration file missing"
    exit 1
  fi
fi

EPISODE=$2

#python3 -um infinitechallenge.pipeline.phase1 $CONFIG_FILE_PATH $EPISODE
#python3 -um infinitechallenge.pipeline.phase2 $CONFIG_FILE_PATH $EPISODE
python3 -um infinitechallenge.pipeline.phase3 $CONFIG_FILE_PATH $EPISODE

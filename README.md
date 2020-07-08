![Deploy to Amazon ECS](https://github.com/nordic96/Infinite_Challenge/workflows/Deploy%20to%20Amazon%20ECS/badge.svg)
![Docker Automated Build](https://img.shields.io/docker/automated/nordic96/infinite_challenge)
![Docker Cloud Build](https://img.shields.io/docker/cloud/build/nordic96/infinite_challenge)

# Infinite Challenge [South Korea]
"Challenge is Infinite". Infinite Challenge is a South Korean television entertainment program, distributed and syndicated by MBC.

![Image of infinite challenge logo](docs/images/Infinite_Challenge_Logo.jpg)

> Infinite Challenge is recognized as the first "Real-Variety" show in Korean television history. The program is largely unscripted, filmed in almost-secrecy and followed a similar format of challenge-based reality television programs. The challenges are often absurd or impossible to achieve, so the program takes on the satirical comedy aspect of a variety show rather than a standard reality or competition program. In earlier episodes, the show's six hosts and staff would continuously proclaim that, in order to achieve its comedic purposes, the program had to be "3-D": Dirty, Dangerous, and Difficult.[14] It gives people fun to try things that seem impossible.
[Wikipedia](https://en.wikipedia.org/wiki/Infinite_Challenge)

# Project Overview
## Skulls (i.e. Skullmark)
![img_skulls](docs/images/skulls.png)

# Project Description
## Data Pipeline
![img_datapipeline](docs/images/data_pipeline_2.png)
   1. Skull Detector processes the episode video file & saves screenshots into a dir with the same name as video file (i.e. if video is named `ep120.mp4` then the directory that contains screenshots of skulls detected would be dir `ep120/`)
        * Also, skull detector script will save a csv file that contains the necessary information
            * When skull is detected (timestamp)
            * No. of skull detected in one frame (no_skull)
            * Coordinates of the skull (boxes)
   1. Main script (facial_recognition model) will iterate the images in the directory and recognise which person is detected in the scene where skull is appeared. 
        * IF multiple people is detected with the skull, we will use the coordinates of the skull and the detected member's faces that are already logged in the CSV file, to find the person that are located closest to the skull (estimated to be the person who is being burned)
    
## Phase 1: Skull Detection
## Phase 2: Facial Recognition

![opencvlogo](docs/images/opencv_logo.png)

## Phase 3: Analysis & Estimation
## Batch Processing
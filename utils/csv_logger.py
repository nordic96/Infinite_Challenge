import csv
import os
from logger.base_logger import logger

# Code for handling csv output data for project
# Developed Date: 29 June 2020
# Brian Fung

skulls_filename = "skulls.csv"
faces_filename = "faces.csv"


class CsvLogger:
    def __init__(self, csv_file_path):
        self.skull_output_path = os.path.join(csv_file_path, skulls_filename)
        self.faces_output_path = os.path.join(csv_file_path, faces_filename)
        self.skull_writer = csv.writer(open(self.skull_output_path, 'a'))
        self.faces_writer = csv.writer(open(self.faces_output_path, 'a'))

    def add_skull_entry(self, frame, timestamp, coordinate_list):
        logger.info("updating [{}]...".format(self.skull_output_path))
        self.skull_writer.writerow([frame, timestamp, coordinate_list])

    def add_faces_entry(self, frame, timestamp, coordinate_dict):
        logger.info("updating [{}]...".format(self.faces_output_path))
        self.skull_writer.writerow([frame, timestamp, coordinate_dict])


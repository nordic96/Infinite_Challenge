import csv
import datetime
import os

# Code for handling csv output data for project
# Developed Date: 29 June 2020
# Brian Fung

class CsvLogger:
    def __init__(self, output_directory):
        logger_start_time = datetime.datetime.now()
        output_directory = output_directory
        output_file_name = logger_start_time.strftime("%d_%m_%Y_%H_%M.csv")
        self.output_path = os.path.join(output_directory, output_file_name)
        output_file = open(self.output_path, 'w')
        self.writer = csv.writer(output_file)
        self.writer.writerow(["episode_number", "frame_number", "timestamp", "number_of_members", "list_of_members"])

    def add_entry(self, episode, frame, timestamp, member_count, members):
        self.writer.writerow([episode, frame, timestamp, member_count, members])

    def path(self):
        return os.path.abspath(self.output_path)

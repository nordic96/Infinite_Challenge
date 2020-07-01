import csv
import os
import shutil
from tempfile import NamedTemporaryFile
from logger.base_logger import logger

# Code for handling csv output data for project
# Developed Date: 29 June 2020
# Last Modified: 30 June 2020
# Brian Fung


class CsvLogger:
    fieldnames = ['episode', 'time', 'skull-coord', 'face-coord', 'name']
    filename = 'data.csv'

    def __init__(self, working_directory):
        self.filename = os.path.join(working_directory, CsvLogger.filename)
        if not os.path.exists(self.filename):
            logger.info('data.csv not found, creating new file [{}]'.format(self.filename))
            with open(self.filename, 'w') as f:
                csv.DictWriter(f, fieldnames=CsvLogger.fieldnames).writeheader()

    def update_entry(self, ep, time, sc, fc, name, mode='e'):
        # mode:
        # e : edit: updates sc, fc, name
        # a : edit(exists)/append(doesn't exist)
        # d : delete, ignores sc, fc, name fields
        updated = False
        with open(self.filename, 'r') as rf, NamedTemporaryFile(mode='w', delete=False) as wf:
            reader = csv.DictReader(rf, fieldnames=CsvLogger.fieldnames)
            writer = csv.DictWriter(wf, fieldnames=CsvLogger.fieldnames)
            header = True
            for row in reader:
                # skip header row
                if header:
                    writer.writeheader()
                    header = False
                    continue
                # update row (edit/delete)
                if row['episode'] == str(ep) and row['time'] == str(time):
                    updated = True
                    if mode == 'e' or mode == 'a':
                        logger.info('editing entry for frame [{} @ ep{}]'.format(time, ep))
                        writer.writerow({
                            'episode': row['episode'],
                            'time': row['time'],
                            'skull-coord': sc,
                            'face-coord': fc,
                            'name': name
                        })
                    elif mode == 'd':
                        logger.info('deleting entry for frame [{} @ ep{}]'.format(time, ep))
                # copy row
                else:
                    writer.writerow(row)

            shutil.move(wf.name, self.filename)

        # add entry
        if not updated:
            if mode == 'e':
                logger.info('no existing entry for frame [{} @ ep{}] found, not updating'.format(time, ep))
            elif mode == 'a':
                logger.info('no existing entry for frame [{} @ ep{}] found, appending...'.format(time, ep))
                self.append_entry(ep, time, sc, fc, name)


    def del_entry(self, ep, time):
        logger.info('deleting entry for frame [{} @ ep{}]'.format(time, ep))
        self.update_entry(ep, time, None, None, None, mode='d')

    def append_entry(self, ep, time, sc, fc, name):
        with open(self.filename, 'a') as f:
            writer = csv.DictWriter(f, fieldnames=CsvLogger.fieldnames)
            writer.writerow({'episode': ep, 'time': time, 'skull-coord': sc, 'face-coord': fc, 'name': name})

    def add_skull_entry(self, ep, time, sc):
        self.update_entry(ep, time, sc, None, None, mode='a')

    def get_entry(self, ep, time):
        with open(self.filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['episode'] == str(ep) and row['time'] == str(time):
                    return row

    def update_face_entry(self, ep, time, fc, name):
        entry = self.get_entry(ep, time)
        self.update_entry(ep, time, entry['skull-coord'], fc, name)

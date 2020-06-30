import csv
import shutil
from tempfile import NamedTemporaryFile
from logger.base_logger import logger

# Code for handling csv output data for project
# Developed Date: 29 June 2020
# Brian Fung


class CsvLogger:
    fieldnames = ['episode', 'time', 'skull-coord', 'face-coord', 'name']

    def __init__(self, filename):
        self.filename = filename

    def update_entry(self, ep, time, sc, fc, name, mode=1):
        # mode:
        # 1 : edit: updates sc, fc, name
        # 2 : edit(exists)/append(doesn't exist)
        # 0 : delete, ignores sc, fc, name fields
        with open(self.filename, 'r') as rf, NamedTemporaryFile(mode='w', delete=False) as wf:
            reader = csv.DictReader(rf, fieldnames=fieldnames)
            writer = csv.DictWriter(wf, fieldnames=fieldnames)
            header = True
            updated = False
            for row in reader:
                # skip header row
                if header:
                    writer.writeheader()
                    header = False
                    continue
                # update row (edit/delete)
                if row['episode'] == str(ep) and row['time'] == str(time):
                    updated = True
                    if mode is 1:
                        logger.info('editing entry for frame [{} @ ep{}]'.format(time, ep))
                        writer.writerow({
                            'episode': row['episode'],
                            'time': row['time'],
                            'skull-coord': sc,
                            'face-coord': fc,
                            'name': name
                        })
                    elif mode is 0:
                        logger.info('deleting entry for frame [{} @ ep{}]'.format(time, ep))
                # copy row
                else:
                    writer.writerow(row)
            shutil.move(wf.name, self.filename)
            # add entry
            if not updated:
                if mode == 1:
                    logger.info('no existing entry for frame [{} @ ep{}] found, not updating'.format(time, ep))
                elif mode == 2:
                    logger.info('no existing entry for frame [{} @ ep{}] found, appending...'.format(time, ep))
                    self.append_entry(ep, time, sc, fc, name)

    def del_entry(self, ep, time):
        logger.info('deleting entry for frame [{} @ ep{}]'.format(time, ep))
        self.update_entry(ep, time, None, None, None, 0)

    def append_entry(self, ep, time, sc, fc, name):
        with open(self.filename, 'a') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow({'episode': ep, 'time': time, 'skull-coord': sc, 'face-coord': fc, 'name': name})

    def add_skull_entry(self, ep, time, sc):
        self.update_entry(ep, time, sc, None, None, mode=2)

    def get_entry(self, ep, time):
        with open(self.filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['episode'] == str(ep) and row['time'] == str(time):
                    return row

    def update_face_entry(self, ep, time, fc, name):
        entry = self.get_entry(ep, time)
        self.update_entry(ep, time, entry['skull-coord'], fc, name)

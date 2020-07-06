from csv import DictReader, DictWriter, reader
from shutil import move
from tempfile import NamedTemporaryFile
from logger.base_logger import logger
from re import findall
from scipy.spatial.distance import euclidean as distance


# Code for logging image processing data for project
# Developed Date: 29 June 2020
# Last Modified: 6 Jul 2020
# Brian Fung

def centre(coordinate):
    try:
        top, left, bottom, right = coordinate
        y = (top + bottom) / 2.0
        x = (left + right) / 2.0
        return x, y
    except:
        top, left, bottom, right = coordinate[0], coordinate[1], coordinate[2], coordinate[3]
        y = (top + bottom) / 2.0
        x = (left + right) / 2.0
        return x, y


def _getcoordlistcol_util(string):
    pattern = '(\\((?:[^\\(])+\\))'
    l = findall(pattern, string)
    coords = []
    for tup in l:
        tup = tup.split(',')
        tup = tuple(map(lambda s: float(s.replace('(', '').replace(')', '')), map(str.strip, tup)))
        coords.append(tup)
    return coords


def _getnamelistcol_util(string):
    pattern = "'([^']+)'"
    res = findall(pattern, string)
    return res


def average_centre(coords):
    n = len(coords)
    if n == 0:
        return None
    sum_x = 0
    sum_y = 0
    for coord in coords:
        x, y = centre(coord)
        sum_x += x
        sum_y += y
    n = float(n)
    return sum_x / n, sum_y / n

class DataLoggerFieldName:
    EPISODE = 'episode'
    TIME = 'time'
    SC_LIST = 'skull-coord'
    FC_LIST = 'face-coord'
    NAME_LIST = 'name'

class DataLogger:
    FIELDNAMES = [DataLoggerFieldName.EPISODE, DataLoggerFieldName.TIME, DataLoggerFieldName.SC_LIST, DataLoggerFieldName.FC_LIST, DataLoggerFieldName.NAME_LIST]

    def __init__(self, filepath):
        self.filepath = filepath
        if not DataLogger.has_valid_headers(filepath):
            logger.warning(f'Invalid headers. {filepath} will be overwritten')
            f = open(filepath, 'w')
            DictWriter(f, fieldnames=DataLogger.FIELDNAMES).writeheader()

    @staticmethod
    def has_valid_headers(filepath):
        header = next(reader(open(filepath, 'r')))
        return set(header).difference(set(DataLogger.FIELDNAMES)) == set()

    def update_entry(self, ep, time, sc, fc, name):
        assert ep is not None
        assert time is not None
        # mode:
        # e : edit: updates sc, fc, name
        # a : edit(exists)/append(doesn't exist)
        updated = False
        rf = open(self.filepath, 'r')
        wf = NamedTemporaryFile(mode='w', delete=False)
        reader = DictReader(rf, fieldnames=DataLogger.FIELDNAMES)
        writer = DictWriter(wf, fieldnames=DataLogger.FIELDNAMES)
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
                logger.info('Editing entry for frame [{} @ ep{}]'.format(time, ep))
                writer.writerow({
                    'episode': row['episode'],
                    'time': row['time'],
                    'skull-coord': sc,
                    'face-coord': fc,
                    'name': name
                })
            # copy row
            else:
                writer.writerow(row)
        move(wf.name, self.filepath)
        return updated

    def append_entry(self, ep, time, sc, fc, name):
        f = open(self.filepath, 'a')
        writer = DictWriter(f, fieldnames=DataLogger.FIELDNAMES)
        logger.info('Adding new entry for [{} @ ep{}]'.format(time, ep))
        writer.writerow({'episode': ep, 'time': time, 'skull-coord': sc, 'face-coord': fc, 'name': name})

    def add_skull_entry(self, ep, time, sc):
        self.get_entry(ep, time)
        if self.get_entry(ep, time) is not None:
            logger.warning(f'Entry for [{time} @ ep{ep}] already exists. Editing entry...')
            self.update_entry(ep, time, sc, None, None)
        else:
            self.append_entry(ep, time, sc, None, None)

    def get_entry(self, ep, time):
        with open(self.filepath, 'r') as f:
            reader = DictReader(f)
            for row in reader:
                if row['episode'] == str(ep) and row['time'] == str(time):
                    return row
        return None

    def update_face_entry(self, ep, time, fc, name):
        entry = self.get_entry(ep, time)
        if entry is None:
            logger.warning(f'Entry for [{time} @ ep{ep}] does not exist. Unable to update with results.')
            return
        self.update_entry(ep, time, entry['skull-coord'], fc, name)

    def print(self):
        print(open(self.filepath).read())

    def get_column(self, header):
        r = DictReader(open(self.filepath, 'r'), fieldnames=DataLogger.FIELDNAMES)
        col = []
        is_header = True
        for row in r:
            if is_header:
                assert row[header] == header, f'{row[header]} : {header}'
                is_header = False
                continue
            col.append(row[header])
        return col

    def find_burned(self):
        episode_entries = self.get_column('episode')
        time_entries = self.get_column('time')
        sclist_entries = list(map(_getcoordlistcol_util, self.get_column('skull-coord')))
        fclist_entries = list(map(_getcoordlistcol_util, self.get_column('face-coord')))
        names_entries = list(map(_getnamelistcol_util, self.get_column('name')))

        # find closest face to skull for each entry
        burned_entries = []
        for ep, time, names, fclist, sclist in zip(episode_entries, time_entries, names_entries, fclist_entries,
                                                   sclist_entries):
            sk_avg = average_centre(sclist)
            if len(names) == 0:
                burned_entries.append(None)
                logger.info(f'entry [{time} @ ep{ep}]: no burn')
                continue
            min = None
            distance_from_skull = {}
            for member, coordinate in zip(names, fclist):
                dist = distance(centre(coordinate), sk_avg)
                distance_from_skull[member] = dist
                if min is None or dist < distance_from_skull[min]:
                    min = member
            burned_entries.append((min, distance_from_skull[min]))
            logger.info(f'entry [{time} @ ep{ep}] : {min} burned')
            burned_entries.append((min, distance_from_skull[min]))
        return burned_entries

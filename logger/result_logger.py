from csv import DictReader, DictWriter, reader
from math import sqrt
from shutil import move
from tempfile import NamedTemporaryFile
from logger.base_logger import logger
from re import findall


FIELDNAME_EP = 'episode_no'  # should match database
FIELDNAME_TIME = 'ep_time'  # should match database
FIELDNAME_SC_LIST = 'list_skull_coords'
FIELDNAME_FC_LIST = 'list_face_coords'
FIELDNAME_NAME_LIST = 'list_names'
FIELDNAME_BURNED_MEMBER = 'member'  # should match database

# Code for logging image processing data for project
# Developed Date: 29 June 2020
# Last Modified: 6 Jul 2020
# Brian Fung


def distance(pt1, pt2):
    (x1,y1), (x2,y2) = pt1, pt2
    x = (x1 + x2) / 2.0
    y = (y1 + y2) / 2.0
    return sqrt(pow(x,2) + pow(y,2))

def _has_valid_header_util(fieldnames, filepath):
    try:
        header = next(reader(open(filepath, 'r')))
        return set(header).difference(set(fieldnames)) == set()
    except StopIteration:
        return False


def _get_coord_list_col_util(string):
    pattern = '(\\((?:[^\\(])+\\))'
    l = findall(pattern, string)
    coords = []
    for tup in l:
        tup = tup.split(',')
        tup = tuple(map(lambda s: float(s.replace('(', '').replace(')', '')), map(str.strip, tup)))
        coords.append(tup)
    return coords


def _get_namelist_col_util(string):
    pattern = "'([^']+)'"
    res = findall(pattern, string)
    return res


def _average_centre_util(coords):
    n = len(coords)
    if n == 0:
        return None
    sum_x = 0
    sum_y = 0
    for coord in coords:
        x, y = _centre_util(coord)
        sum_x += x
        sum_y += y
    n = float(n)
    return sum_x / n, sum_y / n

def _centre_util(coordinate):
    top, left, bottom, right = coordinate
    y = (top + bottom) / 2.0
    x = (left + right) / 2.0
    return x, y


class ResultLogger:
    FIELDNAMES = [FIELDNAME_EP, FIELDNAME_TIME, FIELDNAME_SC_LIST, FIELDNAME_FC_LIST, FIELDNAME_NAME_LIST, FIELDNAME_BURNED_MEMBER]

    def __init__(self, filepath):
        self.filepath = filepath
        if not _has_valid_header_util(ResultLogger.FIELDNAMES, filepath):
            logger.warning(f'Invalid headers. {filepath} will be overwritten')
            f = open(filepath, 'w')
            DictWriter(f, fieldnames=ResultLogger.FIELDNAMES).writeheader()

    def _update_entry(self, ep, time, sc_list=None, fc_list=None, name_list=None, burned=None):
        assert ep is not None
        assert time is not None
        # mode:
        # e : edit: updates sc, fc, name
        # a : edit(exists)/append(doesn't exist)
        written = 0
        rf = open(self.filepath, 'r')
        wf = NamedTemporaryFile(mode='w', delete=False)
        reader = DictReader(rf, fieldnames=ResultLogger.FIELDNAMES)
        writer = DictWriter(wf, fieldnames=ResultLogger.FIELDNAMES)
        header = True
        for row in reader:
            # skip header row
            if header:
                writer.writeheader()
                header = False
                continue
            # update row (edit/delete)
            if row[FIELDNAME_EP] == str(ep) and row[FIELDNAME_TIME] == str(time):
                logger.info('Editing entry for frame [{} @ ep{}]'.format(time, ep))
                written = writer.writerow({
                    # entry id
                    FIELDNAME_EP: row[FIELDNAME_EP], FIELDNAME_TIME: row[FIELDNAME_TIME],
                    # image processing data
                    FIELDNAME_SC_LIST: sc_list, FIELDNAME_FC_LIST: fc_list, FIELDNAME_NAME_LIST: name_list,
                    # estimated result
                    FIELDNAME_BURNED_MEMBER: burned
                })
            # copy row
            else:
                writer.writerow(row)
        move(wf.name, self.filepath)
        return written

    def _append_entry(self, episode, time, sc_list=None, fc_list=None, name_list=None, burned=None):
        f = open(self.filepath, 'a')
        writer = DictWriter(f, fieldnames=ResultLogger.FIELDNAMES)
        logger.info('Adding new entry for [{} @ ep{}]'.format(time, episode))
        return writer.writerow({
            # entry id
            FIELDNAME_EP: episode, FIELDNAME_TIME: time,
            # image processing data
            FIELDNAME_SC_LIST: sc_list, FIELDNAME_FC_LIST: fc_list, FIELDNAME_NAME_LIST: name_list,
            # estimated result
            FIELDNAME_BURNED_MEMBER: burned
        })

    def add_skull_entry(self, ep, time, sc):
        self._get_entry(ep, time)
        if self._get_entry(ep, time) is not None:
            logger.warning(f'Entry for [{time} @ ep{ep}] already exists. Editing entry...')
            return self._update_entry(ep, time, sc)
        else:
            return self._append_entry(ep, time, sc)

    def _get_entry(self, ep, time):
        with open(self.filepath, 'r') as f:
            reader = DictReader(f)
            for row in reader:
                if row[FIELDNAME_EP] == str(ep) and row[FIELDNAME_TIME] == str(time):
                    return row
        return None

    def update_face_entry(self, ep, time, fc, name):
        entry = self._get_entry(ep, time)
        if entry is None:
            logger.warning(f'Entry for [{time} @ ep{ep}] does not exist. Unable to update with results.')
            return 0
        return self._update_entry(ep, time, entry[FIELDNAME_SC_LIST], fc, name)

    def _get_column(self, header):
        r = DictReader(open(self.filepath, 'r'), fieldnames=ResultLogger.FIELDNAMES)
        col = []
        is_header = True
        for row in r:
            if is_header:
                assert row[header] == header, f'{row[header]} : {header}'
                is_header = False
                continue
            col.append(row[header])
        return col

    def bulk_update_entries(self, list_of_entry_dicts):
        entries = {}
        for entry_dict in list_of_entry_dicts:
            id = (entry_dict[FIELDNAME_EP], entry_dict[FIELDNAME_TIME])
            entry_dict.pop(FIELDNAME_EP)
            entry_dict.pop(FIELDNAME_TIME)
            entries[id] = dict()
            for field in entry_dict:
                entries[id][field] = entry_dict[field]
        rf = open(self.filepath, 'r')
        wf = NamedTemporaryFile(mode='w', delete=False)
        reader = DictReader(rf, fieldnames=ResultLogger.FIELDNAMES)
        writer = DictWriter(wf, fieldnames=ResultLogger.FIELDNAMES)
        for row in reader:
            ep = row[FIELDNAME_EP]
            time = row[FIELDNAME_TIME]
            if (ep, time) in entries:
                try:
                    sc_list = entries[(ep, time)][FIELDNAME_SC_LIST]
                except KeyError:
                    sc_list = row[FIELDNAME_SC_LIST]
                try:
                    fc_list = entries[(ep, time)][FIELDNAME_FC_LIST]
                except KeyError:
                    fc_list = row[FIELDNAME_FC_LIST]
                try:
                    name_list = entries[(ep, time)][FIELDNAME_NAME_LIST]
                except KeyError:
                    name_list = row[FIELDNAME_NAME_LIST]
                try:
                    burned_member = entries[(ep, time)][FIELDNAME_BURNED_MEMBER]
                except KeyError:
                    burned_member = row[FIELDNAME_BURNED_MEMBER]
                writer.writerow({
                    FIELDNAME_EP: ep, FIELDNAME_TIME: time,
                    FIELDNAME_SC_LIST: sc_list, FIELDNAME_FC_LIST: fc_list, FIELDNAME_NAME_LIST: name_list,
                    FIELDNAME_BURNED_MEMBER: burned_member
                })
            else:
                writer.writerow(row)
        move(wf.name, self.filepath)

    def estimate_burned_member(self):
        episode_entries = self._get_column(FIELDNAME_EP)
        time_entries = self._get_column(FIELDNAME_TIME)
        sclist_entries = list(map(_get_coord_list_col_util, self._get_column(FIELDNAME_SC_LIST)))
        fclist_entries = list(map(_get_coord_list_col_util, self._get_column(FIELDNAME_FC_LIST)))
        names_entries = list(map(_get_namelist_col_util, self._get_column(FIELDNAME_NAME_LIST)))
        # find closest face to skull for each entry
        estimates = []
        for ep, time, names, fclist, sclist in zip(episode_entries, time_entries, names_entries, fclist_entries,
                                                   sclist_entries):
            sk_avg = _average_centre_util(sclist)
            if len(names) == 0:
                estimates.append({FIELDNAME_EP: ep, FIELDNAME_TIME: time, FIELDNAME_BURNED_MEMBER: 'NO_FACE_FOUND'})
                logger.warning(f'[{time} @ ep{ep}] No burned member: No faces found')
            else:
                burned = None
                distance_from_skull = {}
                for member, coordinate in zip(names, fclist):
                    cd = _centre_util(coordinate)
                    dist = distance(cd, sk_avg)
                    distance_from_skull[member] = dist
                    if burned is None or dist < distance_from_skull[burned]:
                        burned = member
                estimates.append({FIELDNAME_EP: ep, FIELDNAME_TIME: time, FIELDNAME_BURNED_MEMBER: burned})
                logger.info(f'[{time} @ ep{ep}] {burned} burned: Distances from centre of skull(s): {distance_from_skull}')
        return estimates


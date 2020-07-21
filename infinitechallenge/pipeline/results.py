import ast
from tempfile import NamedTemporaryFile

import pandas

from infinitechallenge.logging import logger


class Results:
    FIELDNAME_EP = 'episode_no'  # should match database
    FIELDNAME_TIME = 'time_appeared'  # should match database
    FIELDNAME_SC_LIST = 'list_skull_coords'
    FIELDNAME_FC_LIST = 'list_face_coords'
    FIELDNAME_NAME_LIST = 'list_names'
    FIELDNAME_BURNED_MEMBER = 'member'  # should match database
    INDEX_FIELDS = [FIELDNAME_EP, FIELDNAME_TIME]
    VALUE_FIELDS = [FIELDNAME_SC_LIST, FIELDNAME_FC_LIST, FIELDNAME_NAME_LIST, FIELDNAME_BURNED_MEMBER]
    FIELDNAMES = INDEX_FIELDS + VALUE_FIELDS

    def __init__(self, data: pandas.DataFrame):
        self.data = data

    @classmethod
    def parse_list(cls, str_to_parse):
        try:
            if type(str_to_parse) is list:
                return str_to_parse
            return ast.literal_eval(str_to_parse)
        except SyntaxError:
            return None

    @classmethod
    def blank(cls):
        temp = NamedTemporaryFile(mode='w+')
        temp.write(','.join(Results.FIELDNAMES))
        temp.seek(0)
        return Results.read(temp.name)

    @classmethod
    def read(cls, file_path):
        data = pandas.read_csv(file_path,
                               index_col=(Results.FIELDNAME_EP, Results.FIELDNAME_TIME),
                               dtype={Results.FIELDNAME_EP: 'int',
                                      Results.FIELDNAME_TIME: 'str',
                                      Results.FIELDNAME_NAME_LIST: 'object',
                                      Results.FIELDNAME_SC_LIST: 'object',
                                      Results.FIELDNAME_FC_LIST: 'object',
                                      Results.FIELDNAME_BURNED_MEMBER: 'string'},
                               keep_default_na=False,
                               encoding='utf8',
                               usecols=Results.FIELDNAMES)
        return Results(data)

    def add_skull_entry(self, ep, time, skull_list):
        idx = pandas.MultiIndex.from_tuples([(ep, time)], names=Results.INDEX_FIELDS)
        entry = pandas.DataFrame([[skull_list, None, None, None]], index=idx, columns=Results.VALUE_FIELDS)
        try:
            self.data = self.data.append(entry, verify_integrity=True)
            logger.info(f'Entry for [{time} @ ep{ep}] was created.')
        except ValueError:
            logger.info(f'Entry for [{time} @ ep{ep}] already has skull detection results, overwriting...')
            self.data.update(entry)

    def update_face_entry(self, ep, time, face_list, name_list):
        idx = pandas.MultiIndex.from_tuples([(ep, time)], names=Results.INDEX_FIELDS)
        entry = pandas.DataFrame([[None, face_list, name_list, None]], index=idx, columns=Results.VALUE_FIELDS)
        try:
            self.data.update(entry, errors='raise')
            logger.info(f'Entry for [{time} @ ep{ep}] was updated with face recognition results.')
        except ValueError:
            logger.info(f'Entry for [{time} @ ep{ep}] already has face recognition results, overwriting...')
            self.data.update(entry)

    def update_burned_member(self, ep, time, burned):
        idx = pandas.MultiIndex.from_tuples([(ep, time)], names=Results.INDEX_FIELDS)
        entry = pandas.DataFrame([[None, None, None, burned]], index=idx, columns=Results.VALUE_FIELDS)
        try:
            self.data.update(entry, errors='raise')
            logger.info(f'Entry for [{time} @ ep{ep}] was updated with burned member results.')
        except ValueError:
            logger.info(f'Entry for [{time} @ ep{ep}] already has burned member results, overwriting...')
            self.data.update(entry)

    def get_entry(self, ep, time):
        idx = pandas.MultiIndex.from_tuples([(ep, time)], names=Results.INDEX_FIELDS)
        entries = self.data.loc[idx].values.tolist()
        assert len(entries) <= 1
        sc_list, fc_list, name_list, burned = entries[0]
        sc_list = Results.parse_list(sc_list)
        fc_list = Results.parse_list(fc_list)
        name_list = Results.parse_list(name_list)
        burned = burned if burned else None
        return sc_list, fc_list, name_list, burned

    def get_entries(self):
        indexes = self.data.index.values.tolist()
        entries = {}
        for ep, time in indexes:
            sc_list, fc_list, name_list, burned_member = self.get_entry(ep, time)
            entries[(ep, time)] = {Results.FIELDNAME_SC_LIST: sc_list,
                                   Results.FIELDNAME_FC_LIST: fc_list,
                                   Results.FIELDNAME_NAME_LIST: name_list,
                                   Results.FIELDNAME_BURNED_MEMBER: burned_member}
        return entries

    def write(self, file_path):
        self.data.to_csv(file_path)
        logger.info(f"Results have been saved to '{file_path}'.")
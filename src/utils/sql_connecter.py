import pyodbc
import pandas as pd
from src.logger.base_logger import logger

# Description: Connects to SQL Server and execute bulk insert & other queries
# Developed Date: 3 Jul 2020
# Developer: Ko Gi Hun


class SqlConnector:
    def __init__(self, file_path, db_endpoint, db_name, db_uid, db_pw):
        self.file_path = file_path
        connection_string = 'DRIVER={ODBC Driver 17 for SQL Server}; ' \
                                 + f'SERVER={db_endpoint}; ' \
                                   f'DATABASE={db_name}; ' \
                                   f'UID={db_uid}; ' \
                                   f'PWD={db_pw}'

        try:
            logger.debug(connection_string)
            self.conn = pyodbc.connect(connection_string)
            self.cursor = self.conn.cursor()
            logger.info('Able to connect.')
        except pyodbc.Error as ex:
            logger.error('Failed to connect.')
            raise ex

    def execute(self, query, type):
        logger.info(query)
        try:
            self.cursor.execute(query)
            # SELECT OPERATION
            if type == 'SELECT':
                columns = [column[0] for column in self.cursor.description]
                results = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
                logger.info(results)
                return results
            # SINGLE INSERT OPERATION
            elif type == 'INSERT':
                self.conn.commit()
        except pyodbc.Error as ex:
            logger.error(ex)
            raise ex

    def bulk_insert_csv(self, table_name, cols):
        try:
            # Reading from CSV file
            df = pd.read_csv(self.file_path, encoding='utf8', usecols=cols)
            df = df.values.tolist()
            if not df:
                logger.info('No entries to insert into database.')
                return
            logger.info('Successfully read {} rows from CSV file {}'.format(len(df), self.file_path))
        except pd.io.common.EmptyDataError as ex:
            logger.error(ex)
            raise ex
        try:
            column_str = str(tuple(cols)).replace("'", "\"")
            wildcard_str = str(tuple(map(lambda x: "?", cols))).replace("'", "")
            query_template = 'INSERT INTO {} {} VALUES {}'.format(table_name, column_str, wildcard_str)
            logger.debug(f'executemany query template: \'{query_template}\'')
            # Performing Bulk Insert into RDS
            logger.debug(df)
            self.cursor.executemany(query_template, df)
            self.cursor.commit()
            logger.info('Insert success.')
        except pyodbc.Error as ex:
            logger.error(ex)
            raise ex

import pyodbc
import argparse
import configparser
import pandas as pd
from logger.base_logger import logger

# Description: Connects to SQL Server and execute bulk insert & other queries
# Developed Date: 3 Jul 2020
# Developer: Ko Gi Hun

# Initialise strings from config file
config = configparser.ConfigParser()
config.read('strings.ini')

SERVER_ENDPOINT = config['AWS RDS']['endpoint']
DB_NAME = config['AWS RDS']['db_name']
USER_NAME = config['AWS RDS']['uname']
DB_PW = config['AWS RDS']['pw']

# Connection String for SQL Server connection
CONN_STRING = 'DRIVER={ODBC Driver 17 for SQL Server}' \
              + ';SERVER={{{}}}; DATABASE={{{}}};'.format(SERVER_ENDPOINT, DB_NAME) \
              + 'UID={{{}}}; PWD={{{}}}'.format(USER_NAME, DB_PW)


# Description: SQL Connector for AWS RDS
# Developed Date: 2 Jul 2020
# Developer: Ko Gi Hun


class SqlConnector:
    def __init__(self, file_path):
        try:
            self.conn = pyodbc.connect(CONN_STRING)
        except pyodbc.Error as ex:
            logger.error(ex)
        self.cursor = self.conn.cursor()
        self.file_path = file_path

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

    def bulk_insert_csv(self, table_name, header):
        try:
            # Reading from CSV file
            df = pd.read_csv(self.file_path, encoding='utf8', header=header)
            df = df.values.tolist()
        except pd.io.common.EmptyDataError as ex:
            logger.error(ex)

        logger.info('Successfully read rows from CSV file {}'.format(self.file_path))
        no_rows = 0
        for row in df:
            logger.info(row)
            no_rows += 1
        try:
            # Performing Bulk Insert into RDS
            string = '''INSERT INTO {} VALUES (?, ?, ?)'''.format(table_name)
            logger.info(string)
            result = self.cursor.executemany(string, df)
            self.cursor.commit()
        except pyodbc.Error as ex:
            logger.error(ex)
        logger.info('Affected rows: {}'.format(no_rows))


# Main function for testing
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--input", required=True, help="input directory for csv file")
args = vars(ap.parse_args())

if __name__ == '__main__':
    sql_conn = SqlConnector(args['input'])
    # BULK INSERT example from table skull
    #sql_conn.bulk_insert_csv('skull', header=None)

    #SELECT example from table skull
    #result = sql_conn.execute('SELECT * FROM skull;', 'SELECT')
    #logger.info(result)
import pyodbc
import configparser
from logger.base_logger import logger

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


class SQLConnector:
    def __init__(self):
        self.conn = pyodbc.connect(CONN_STRING)
        self.cursor = self.conn.cursor()

    def execute(self, query):
        self.cursor.execute(query)
        for row in self.cursor:
            logger.info(row)

    def insertSkullInfo(self, csv_file_path):
        return None
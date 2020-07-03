import pyodbc
import argparse
import csv
import configparser
import pandas as pd

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
        self.conn = pyodbc.connect(CONN_STRING)
        self.cursor = self.conn.cursor()
        self.file_path = file_path

    def execute(self, query, type):
        self.cursor.execute(query)
        if type == 'SELECT':
            for row in self.cursor:
                print(row)
        elif type == 'INSERT':
            self.conn.commit()

    def insert_skull_info(self):
        with open(self.file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                print(row)
        return None

    def insert_skull_info_test(self, header):
        df= pd.read_csv(self.file_path, header=header)
        for index, row in df.iterrows():
            print(row)

        statement = "INSERT INTO skull VALUES ('{}', '{}', {});".format(row[0], row[1], row[2])
        print(statement)
        self.execute(statement, 'INSERT')
        self.cursor.commit()
        return None

    def close(self):
        self.conn.close()


ap = argparse.ArgumentParser()
ap.add_argument("-i", "--input", required=True, help="input directory for csv file")
args = vars(ap.parse_args())

if __name__ == '__main__':
    sqlconn = SqlConnector(args['input'])
    sqlconn.insert_skull_info_test(None)
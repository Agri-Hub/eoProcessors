import os
from pathlib import Path
from configparser import ConfigParser
import psycopg

def get_local_config(filename="database.ini", section="sentinel_status"):
    # TODO: has default section? Does check or not?
    parser = ConfigParser()
    config_path = str(Path(Path(__file__).parent, filename).resolve())
    parser.read(config_path)

    config = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            config[param[0]] = str(param[1])
    else:
        raise Exception("Section {0} not found in the {1} file".format(section, filename))

    return config

def get_env_config():
    # TODO make checks
    # TODO check if other db access is needed: (like "section" in local config)
    config = {}
    config["user"] = os.getenv("DB_USER")
    config["password"] = os.getenv("DB_PASSWORD")
    config["host"] = os.getenv("DB_HOST")
    config["port"] = os.getenv("DB_PORT")
    config["dbname"] = os.getenv("DB_NAME")
    if not all(config.values()):
        return None
    return config

def describe_table(config, table):

    sql = f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position;
        """

    with psycopg.connect(**config) as conn:
        with conn.cursor() as curs:
            curs.execute(sql, (table,))
            columns = [row[0] for row in curs.fetchall()]
            print("Column names:", columns)


def query_uuid(config, uuid):

    sql = f"""
        SELECT *
        FROM products
        where products.id=%s"""

    with psycopg.connect(**config) as conn:
        with conn.cursor() as curs:
            curs.execute(sql, (uuid,))
            # It should be one...
            return curs.fetchone()

def update_uuid(config, table, uuid, column, value):
        
    sql = f"""
        UPDATE {table}
        SET {column} = %s
        WHERE products.id = %s;
    """
    if column == "id":
        # Do not explain
        return False

    with psycopg.connect(**config) as conn:
        with conn.cursor() as curs:
            curs.execute(sql, (value, uuid))
            conn.commit()

            # If updated succesfully, return True
            if curs.rowcount > 0:
                return True
            return False

def query_all_items(config):
    sql = """
        SELECT *
        FROM products
    """

    with psycopg.connect(**config) as conn:
        print("Connected to the PostgreSQL server.")
        with conn.cursor() as curs:
            print("Querying")
            curs.execute(sql)
            results = curs.fetchall()
            for row in results:
                print(row)

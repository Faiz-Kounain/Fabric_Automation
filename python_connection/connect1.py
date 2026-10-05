import os
import struct
import subprocess

import pyodbc

AZ_PATH = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"

# Connection settings come from Windows user environment variables (not stored in the project)
SERVER = os.environ["FABRIC_SQL_SERVER"]
DATABASE = os.environ["FABRIC_SQL_DATABASE"]
import os
print(os.environ["FABRIC_SQL_SERVER"])

def get_sql_token():
    result = subprocess.run(
        [AZ_PATH, "account", "get-access-token",
         "--resource", "https://database.windows.net/",
         "--query", "accessToken", "-o", "tsv"],
        capture_output=True, text=True
    )
    token = result.stdout.strip()
    if not token:
        raise Exception(f"Could not get SQL token: {result.stderr}")
    return token


def get_connection():
    token = get_sql_token().encode("utf-16-le")
    token_struct = struct.pack(f"<I{len(token)}s", len(token), token)

    SQL_COPT_SS_ACCESS_TOKEN = 1256

    conn_str = (
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server={SERVER},1433;"
        f"Database={DATABASE};"
        "Encrypt=yes;TrustServerCertificate=no;"
    )
    return pyodbc.connect(conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})


conn = get_connection()
cursor = conn.cursor()

cursor.execute("SELECT DB_NAME(), SUSER_SNAME()")
db_name, user_name = cursor.fetchone()
print(f"Connected to: {db_name} as {user_name}")

cursor.execute("SELECT TOP 5 name, create_date FROM sys.tables")
rows = cursor.fetchall()
print(f"Tables found: {len(rows)}")
for row in rows:
    print(row)

conn.close()

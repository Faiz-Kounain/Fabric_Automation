import struct
import subprocess

import keyring
import pyodbc

print(keyring.get_password("FABRIC_SQL_SERVER", "server"))

AZ_PATH = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"

# Connection settings come from Windows Credential Manager (encrypted, not stored in the project)
KEYRING_SERVICE = "fabric_poc"

# print("Stored value:", keyring.get_password(KEYRING_SERVICE, "FABRIC_SQL_SERVER"))

def get_setting(name):
    value = keyring.get_password(KEYRING_SERVICE, name)
    if value is None:
        raise Exception(
            f"'{name}' not found in Windows Credential Manager. Save it with:\n"
            f"  python -c \"import keyring; keyring.set_password('{KEYRING_SERVICE}', '{name}', '<value>')\""
        )
    return value


SERVER = get_setting("FABRIC_SQL_SERVER")
DATABASE = get_setting("FABRIC_SQL_DATABASE")


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

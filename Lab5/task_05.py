import sys
import os
from dotenv import load_dotenv

load_dotenv()

class MySQLConnector:
    def __init__(self, host="localhost", port=3306, user="root", password=""):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self._conn = None
        self._cursor = None

    def connect(self):
        try:
            import mysql.connector
        except ImportError:
            raise ImportError("Библиотека не установлена. Выполните: pip install mysql-connector-python")
        self._conn = mysql.connector.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            connection_timeout=10,
        )
        self._cursor = self._conn.cursor()

    def get_version(self) -> str:
        if self._cursor is None:
            raise RuntimeError("Нет активного соединения.")
        self._cursor.execute("SELECT VERSION()")
        row = self._cursor.fetchone()
        return row[0] if row else "неизвестно"

    def close(self):
        if self._cursor:
            try:
                self._cursor.close()
            except Exception:
                pass
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

def main():
    try:
        with MySQLConnector(user="root", password=os.getenv("MYSQL_PASSWORD")) as conn:
            version = conn.get_version()
            print(f"Соединение установлено: {conn.host}:{conn.port}")
            print(f"Версия MySQL: {version}")
    except ImportError as e:
        print(f"Ошибка импорта: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Ошибка подключения: {type(e).__name__}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
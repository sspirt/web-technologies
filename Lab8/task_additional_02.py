import argparse
import csv
import logging
import os
import sys
from pathlib import Path
import mysql.connector
from mysql.connector import Error as MySQLError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": "csv_files",
}

class CSVImporter:
    def __init__(self, table: str, on_conflict: str = "ignore",
                 create_table: bool = False, encoding: str = "utf-8"):
        self.table = table
        self.on_conflict = on_conflict
        self.create_table = create_table
        self.encoding = encoding

    def run(self, csv_path: Path) -> tuple[int, int]:
        if not csv_path.exists():
            log.error("Файл не найден: %s", csv_path)
            return 0, 0
        try:
            rows, headers = self._read_csv(csv_path)
        except Exception as exc:
            log.error("Ошибка чтения CSV: %s", exc)
            return 0, 0
        if not rows:
            log.warning("CSV-файл пустой")
            return 0, 0
        log.info("Прочитано строк: %d, столбцов: %d", len(rows), len(headers))
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
        except MySQLError as exc:
            log.error("Ошибка подключения к MySQL: %s", exc)
            return 0, 0
        try:
            return self._import(conn, headers, rows)
        finally:
            conn.close()

    def _read_csv(self, path: Path) -> tuple[list[dict], list[str]]:
        with open(path, newline="", encoding=self.encoding, errors="replace") as f:
            sample = f.read(4096)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            reader = csv.DictReader(f, dialect=dialect)
            headers = list(reader.fieldnames or [])
            rows = list(reader)
        return rows, headers

    def _import(self, conn, headers: list[str], rows: list[dict]) -> tuple[int, int]:
        cur = conn.cursor()
        if self.create_table:
            self._ensure_table(cur, headers)
        else:
            self._validate_columns(cur, headers)
        cols = ", ".join(f"`{h}`" for h in headers)
        placeholders = ", ".join(["%s"] * len(headers))
        if self.on_conflict == "replace":
            sql = f"REPLACE INTO `{self.table}` ({cols}) VALUES ({placeholders})"
        elif self.on_conflict == "ignore":
            sql = f"INSERT IGNORE INTO `{self.table}` ({cols}) VALUES ({placeholders})"
        else:
            sql = f"INSERT INTO `{self.table}` ({cols}) VALUES ({placeholders})"
        inserted = failed = 0
        for i, row in enumerate(rows, 1):
            values = [row.get(h) or None for h in headers]
            try:
                cur.execute(sql, values)
                inserted += 1
            except MySQLError as exc:
                log.warning("Строка %d пропущена: %s", i, exc)
                failed += 1
        conn.commit()
        cur.close()
        log.info("Готово. Вставлено: %d, Пропущено: %d", inserted, failed)
        return inserted, failed

    def _ensure_table(self, cur, headers: list[str]) -> None:
        cols = ", ".join(f"`{h}` TEXT" for h in headers)
        cur.execute(f"CREATE TABLE IF NOT EXISTS `{self.table}` ({cols})")
        log.info("Таблица '%s' проверена/создана", self.table)

    def _validate_columns(self, cur, headers: list[str]) -> None:
        cur.execute(f"SHOW COLUMNS FROM `{self.table}`")
        db_cols = {row[0].lower() for row in cur.fetchall()}
        if not db_cols:
            raise MySQLError(f"Таблица '{self.table}' не существует. Используйте --create-table")
        missing = [h for h in headers if h.lower() not in db_cols]
        if missing:
            raise MySQLError(f"Столбцы из CSV отсутствуют в таблице: {missing}")

def main():
    parser = argparse.ArgumentParser(description="Импорт CSV в MySQL")
    parser.add_argument("csv_file", help="Путь к CSV-файлу")
    parser.add_argument("--table", required=True, help="Имя таблицы")
    parser.add_argument("--on-conflict", default="ignore",
                        choices=["ignore", "replace", "abort"],
                        help="Поведение при конфликте (по умолчанию ignore)")
    parser.add_argument("--create-table", action="store_true",
                        help="Создать таблицу автоматически если не существует")
    parser.add_argument("--encoding", default="utf-8",
                        help="Кодировка CSV (по умолчанию utf-8)")
    args = parser.parse_args()
    importer = CSVImporter(
        table=args.table,
        on_conflict=args.on_conflict,
        create_table=args.create_table,
        encoding=args.encoding,
    )
    inserted, _ = importer.run(Path(args.csv_file))
    sys.exit(0 if inserted > 0 else 1)

if __name__ == "__main__":
    main()
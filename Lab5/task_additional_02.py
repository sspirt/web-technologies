import html
import sys
from pathlib import Path


class MySQLHTMLReporter:
    HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body>
  <h1>{title}</h1>
  <p class="query">{query_escaped}</p>
  {table_html}
  <p class="meta">{meta}</p>
</body>
</html>
"""

    def __init__(self, host: str, port: int, user: str, password: str, database: str = None):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self._conn = None
        self._cursor = None

    def connect(self):
        try:
            import mysql.connector
        except ImportError:
            raise ImportError("Установите: pip install mysql-connector-python")
        params = dict(host=self.host, port=self.port, user=self.user,
                      password=self.password, connection_timeout=10)
        if self.database:
            params["database"] = self.database
        self._conn = mysql.connector.connect(**params)
        self._cursor = self._conn.cursor()

    def close(self):
        for obj in (self._cursor, self._conn):
            if obj:
                try:
                    obj.close()
                except Exception:
                    pass
        self._cursor = self._conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()

    def execute(self, query: str) -> tuple[list[str], list[tuple]]:
        if not query.strip().upper().startswith("SELECT"):
            raise ValueError("Разрешены только SELECT-запросы.")
        self._cursor.execute(query)
        columns = [desc[0] for desc in self._cursor.description]
        rows = self._cursor.fetchall()
        return columns, rows

    @staticmethod
    def _build_table(columns: list[str], rows: list[tuple]) -> str:
        if not rows:
            return '<div class="empty">Запрос вернул 0 строк.</div>'
        esc = html.escape
        th = "".join(f"<th>{esc(str(c))}</th>" for c in columns)
        body_rows = []
        for row in rows:
            cells = "".join(
                f"<td>{'NULL' if v is None else esc(str(v))}</td>" for v in row
            )
            body_rows.append(f"<tr>{cells}</tr>")
        return (
            f"<table><thead><tr>{th}</tr></thead>"
            f"<tbody>{''.join(body_rows)}</tbody></table>"
        )

    def to_html(self, query: str, title: str = "Результат запроса") -> str:
        columns, rows = self.execute(query)
        from datetime import datetime
        meta = (
            f"Строк: {len(rows)} | Столбцов: {len(columns)} | "
            f"Создано: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )
        return self.HTML_TEMPLATE.format(
            title=html.escape(title),
            query_escaped=html.escape(query),
            table_html=self._build_table(columns, rows),
            meta=meta,
        )

    def save_html(self, query: str, output_path: str,
                  title: str = "Результат запроса") -> Path:
        content = self.to_html(query, title)
        path = Path(output_path)
        path.write_text(content, encoding="utf-8")
        return path


def _get_input(prompt: str, default: str = "") -> str:
    v = input(f"{prompt} [{default}]: ").strip()
    return v if v else default

def main():
    host = _get_input("Хост", "localhost")
    port = int(_get_input("Порт", "3306") or "3306")
    user = _get_input("Пользователь", "root")
    import getpass
    try:
        password = getpass.getpass("Пароль: ")
    except Exception:
        password = input("Пароль: ")
    database = _get_input("База данных (необязательно)", "")
    output = _get_input("Путь для сохранения HTML", "result.html")
    reporter = MySQLHTMLReporter(
        host=host, port=port, user=user, password=password,
        database=database if database else None
    )
    print("\nВведите SELECT-запрос (завершите пустой строкой):")
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    query = " ".join(lines).strip()
    if not query:
        print("Запрос пуст. Выход")
        return
    try:
        with reporter as rep:
            saved = rep.save_html(query, output, title=f"SQL: {query[:60]}")
            print(f"HTML сохранён: {saved.resolve()}")
    except ImportError as e:
        print(f"[ImportError] {e}", file=sys.stderr)
    except ValueError as e:
        print(f"[Ошибка запроса] {e}", file=sys.stderr)
    except Exception as e:
        print(f"[Ошибка] {type(e).__name__}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
from html import escape

class TableBuilder:
    def __init__(self, headers: list[object] | tuple[object, ...] | None = None) -> None:
        if headers is not None and not isinstance(headers, (list, tuple)):
            raise TypeError("Headers must be a list, tuple, or None")
        self.headers = list(headers) if headers is not None else []
        self.rows: list[list[object]] = []

    def add_row(self, row: list[object] | tuple[object, ...]) -> None:
        if not isinstance(row, (list, tuple)):
            raise TypeError("Row must be a list or tuple")
        if self.headers and len(row) != len(self.headers):
            raise ValueError("Row length must match headers length")
        if not row:
            raise ValueError("Row cannot be empty")
        self.rows.append(list(row))

    def get_table(self) -> str:
        lines = ['<table border="1">']
        if self.headers:
            lines.append('  <tr>')
            lines.extend(self._cell('th', header) for header in self.headers)
            lines.append('  </tr>')
        for row in self.rows:
            lines.append('  <tr>')
            lines.extend(self._cell('td', value) for value in row)
            lines.append('  </tr>')
        lines.append('</table>')
        return "\n".join(lines)

    @staticmethod
    def _cell(tag: str, value: object) -> str:
        return f'    <{tag}>{escape(str(value), quote=True)}</{tag}>'

if __name__ == "__main__":
    table = TableBuilder(["Name", "Age"])
    table.add_row(["Alice", 20])
    table.add_row(["Bob", 22])
    print(table.get_table())
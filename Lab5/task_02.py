from pathlib import Path


class DirectoryAnalyzer:
    UNITS = [("ТБ", 1 << 40), ("ГБ", 1 << 30), ("МБ", 1 << 20), ("КБ", 1 << 10), ("Б", 1)]

    def __init__(self, path: str):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Путь не найден")
        if not self.path.is_dir():
            raise NotADirectoryError(f"Указанный путь не является каталогом")

    @staticmethod
    def format_size(size_bytes: int) -> str:
        for name, factor in DirectoryAnalyzer.UNITS:
            if size_bytes >= factor:
                value = size_bytes / factor
                return f"{value:.2f} {name} ({size_bytes} Б)"
        return "0 Б"

    def scan(self) -> dict:
        total_size = 0
        file_count = 0
        dir_count = 0
        errors = []
        for entry in self.path.rglob("*"):
            try:
                if not entry.is_symlink() and entry.is_file():
                    total_size += entry.stat().st_size
                    file_count += 1
                elif not entry.is_symlink() and entry.is_dir():
                    dir_count += 1
            except PermissionError as e:
                errors.append(str(e))
            except OSError as e:
                errors.append(str(e))
        return {
            "path": str(self.path.resolve()),
            "total_size": total_size,
            "file_count": file_count,
            "dir_count": dir_count,
            "errors": errors,
        }

    def report(self) -> str:
        result = self.scan()
        lines = [
            f"Каталог: {result['path']}",
            f"Файлов: {result['file_count']}",
            f"Подкаталогов: {result['dir_count']}",
            f"Общий размер: {self.format_size(result['total_size'])}",
        ]
        if result["errors"]:
            lines.append(f"Ошибок доступа: {len(result['errors'])}")
            for err in result["errors"][:5]:
                lines.append(err)
            if len(result["errors"]) > 5:
                lines.append(f"... и ещё {len(result['errors']) - 5}")
        return "\n".join(lines)


def main():
    while True:
        raw = input("Введите путь к каталогу (или 'выход'): ").strip()
        if raw.lower() in ("выход", "exit", "q"):
            break
        if not raw:
            print("Путь не может быть пустым")
            continue
        try:
            analyzer = DirectoryAnalyzer(raw)
            print(analyzer.report())
        except (FileNotFoundError, NotADirectoryError, PermissionError) as e:
            print(f"Ошибка: {e}")
        print()

if __name__ == "__main__":
    main()

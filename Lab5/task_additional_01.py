import hashlib
from collections import defaultdict
from pathlib import Path

class DuplicateFinder:
    CHUNK = 65536

    def __init__(self, path: str):
        self.root = Path(path)
        if not self.root.exists():
            raise FileNotFoundError(f"Путь не найден: '{path}'")
        if not self.root.is_dir():
            raise NotADirectoryError(f"Не является каталогом: '{path}'")

    def _hash_file(self, filepath: Path) -> str | None:
        h = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                while chunk := f.read(self.CHUNK):
                    h.update(chunk)
            return h.hexdigest()
        except (OSError, PermissionError):
            return None

    def find(self) -> dict[str, list[Path]]:
        by_size: dict[int, list[Path]] = defaultdict(list)
        for entry in self.root.rglob("*"):
            try:
                if not entry.is_symlink() and entry.is_file():
                    by_size[entry.stat().st_size].append(entry)
            except OSError:
                pass
        by_hash: dict[str, list[Path]] = defaultdict(list)
        for size, files in by_size.items():
            if len(files) < 2:
                continue
            for filepath in files:
                digest = self._hash_file(filepath)
                if digest is not None:
                    by_hash[digest].append(filepath)
        return {h: paths for h, paths in by_hash.items() if len(paths) > 1}

    def report(self) -> str:
        duplicates = self.find()
        if not duplicates:
            return f"Дубликатов в '{self.root.resolve()}' не найдено."
        lines = [f"Найдено групп дубликатов: {len(duplicates)}", ""]
        total_wasted = 0
        for group_idx, (digest, paths) in enumerate(sorted(duplicates.items()), start=1):
            size = paths[0].stat().st_size
            wasted = size * (len(paths) - 1)
            total_wasted += wasted
            lines.append(
                f"Группа #{group_idx} SHA-256: {digest[:16]}..."
                f"Размер: {size:,} Б Дубликатов: {len(paths) - 1}"
            )
            for p in sorted(paths):
                lines.append(f"    {p}")
            lines.append("")
        lines.append(
            f"Итого «лишних» данных: {total_wasted:,} Б "
            f"({total_wasted / (1 << 20):.2f} МБ)"
        )
        return "\n".join(lines)

def main():
    while True:
        raw = input("Введите путь к каталогу (или 'выход'): ").strip()
        if raw.lower() in ("выход", "exit", "q"):
            break
        if not raw:
            continue
        try:
            finder = DuplicateFinder(raw)
            print(finder.report())
        except (FileNotFoundError, NotADirectoryError, PermissionError) as e:
            print(f"Ошибка: {e}")
        print()

if __name__ == "__main__":
    main()
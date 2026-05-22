from dataclasses import dataclass
from pathlib import Path

@dataclass
class FileSystemObject:
    name: str
    size_bytes: int
    object_type: str

    UNIT_FACTORS = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 ** 2,
        "GB": 1024 ** 3,
        "TB": 1024 ** 4,
    }

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Name must be a non-empty string")
        if not isinstance(self.size_bytes, int) or self.size_bytes < 0:
            raise ValueError("size_bytes must be a non-negative integer")
        if self.object_type not in {"file", "directory", "other"}:
            raise ValueError("object_type must be 'file', 'directory', or 'other'")

    def get_size(self, unit: str = "B") -> float:
        if not isinstance(unit, str):
            raise TypeError("Unit must be a string")
        unit = unit.strip().upper()
        if unit not in self.UNIT_FACTORS:
            raise ValueError(f"Unsupported unit. Available: {', '.join(self.UNIT_FACTORS)}")
        return self.size_bytes / self.UNIT_FACTORS[unit]

def detect_object_type(path: Path) -> str:
    if path.is_file():
        return "file"
    if path.is_dir():
        return "directory"
    return "other"

if __name__ == "__main__":
    current_dir = Path('.')
    objects: list[FileSystemObject] = []
    for path in current_dir.iterdir():
        try:
            size = path.stat().st_size
            file_object = FileSystemObject(path.name, size, detect_object_type(path))
            objects.append(file_object)
        except OSError as exc:
            print(f"Cannot read '{path}': {exc}")
    for obj in objects:
        print(f"{obj.name} ({obj.object_type}) - {obj.get_size('MB'):.6f} MB")
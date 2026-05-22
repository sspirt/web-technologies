from pathlib import Path
from datetime import datetime

class Logger:
    VALID_DESTINATIONS = {"console", "file"}

    def __init__(self, destination: str = "console", file_path: str | None = None, encoding: str = "utf-8") -> None:
        if not isinstance(destination, str):
            raise TypeError("Destination must be a string")
        destination = destination.strip().lower()
        if destination not in self.VALID_DESTINATIONS:
            raise ValueError("Destination must be 'console' or 'file'")
        self.destination = destination
        self.encoding = encoding
        self.file_path = Path(file_path) if file_path else None
        if self.destination == "file":
            if self.file_path is None:
                raise ValueError("file_path is required when destination='file'")
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _format_message(message: object) -> str:
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        return f"[{timestamp}] {message}"

    def log(self, message: object) -> None:
        formatted = self._format_message(message)
        if self.destination == "console":
            print(formatted)
            return
        try:
            assert self.file_path is not None
            with self.file_path.open("a", encoding=self.encoding) as file:
                file.write(formatted + "\n")
        except OSError as exc:
            raise OSError(f"Failed to write to log file '{self.file_path}': {exc}") from exc

if __name__ == "__main__":
    console_logger = Logger("console")
    console_logger.log("Program started")
    file_logger = Logger("file", "app.txt")
    file_logger.log("File log entry")
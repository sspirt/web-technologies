import argparse
import logging
import signal
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

class DirectoryArchiver:
    def __init__(self, output_dir: Path, keep: int = 0):
        self.output_dir = output_dir
        self.keep = keep
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def archive_all(self, sources: list[Path]) -> list[Path]:
        created = []
        for source in sources:
            archive = self._archive_one(source)
            if archive:
                created.append(archive)
        return created

    def _archive_one(self, source: Path) -> Path | None:
        if not source.exists():
            log.error("Каталог не существует: %s", source)
            return None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{source.name}_{timestamp}.zip"
        dest = self.output_dir / archive_name
        try:
            log.info("Архивирование %s → %s", source, dest.name)
            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                if source.is_dir():
                    self._add_directory(zf, source)
                else:
                    zf.write(source, source.name)
            size_kb = dest.stat().st_size // 1024
            log.info("Создан архив %s (%d КБ)", dest.name, size_kb)
            if self.keep > 0:
                self._rotate(source.name)
            return dest
        except PermissionError as exc:
            log.error("Нет прав доступа к %s: %s", source, exc)
        except OSError as exc:
            log.error("Ошибка при архивировании %s: %s", source, exc)
        except zipfile.BadZipFile as exc:
            log.error("Ошибка создания ZIP: %s", exc)
        return None

    @staticmethod
    def _add_directory(zf: zipfile.ZipFile, directory: Path) -> None:
        for file in directory.rglob("*"):
            if file.is_file():
                try:
                    arcname = file.relative_to(directory.parent)
                    zf.write(file, arcname)
                except OSError as exc:
                    log.warning("Пропуск файла %s: %s", file, exc)

    def _rotate(self, prefix: str) -> None:
        archives = sorted(
            self.output_dir.glob(f"{prefix}_*.zip"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        to_delete = archives[self.keep:]
        for old in to_delete:
            try:
                old.unlink()
                log.info("Удалён старый архив %s", old.name)
            except OSError as exc:
                log.warning("Не удалось удалить %s: %s", old, exc)

class ArchiveScheduler:
    def __init__(self, archiver: DirectoryArchiver, sources: list[Path], interval: int):
        self.archiver = archiver
        self.sources = sources
        self.interval = interval
        self._running = False

    def run_once(self) -> None:
        log.info("Разовое архивирование %d каталогов", len(self.sources))
        created = self.archiver.archive_all(self.sources)
        log.info("Создано архивов: %d", len(created))

    def run_forever(self) -> None:
        self._running = True
        signal.signal(signal.SIGINT, self._handle_stop)
        signal.signal(signal.SIGTERM, self._handle_stop)
        log.info("Планировщик запущен. Интервал: %d сек. Каталогов: %d",
                 self.interval, len(self.sources))
        while self._running:
            self.archiver.archive_all(self.sources)
            log.info("Следующий запуск через %d сек. Нажмите Ctrl+C для остановки",
                     self.interval)
            self._sleep_interruptible(self.interval)
        log.info("Планировщик остановлен")

    def _sleep_interruptible(self, seconds: int) -> None:
        for _ in range(seconds):
            if not self._running:
                break
            time.sleep(1)

    def _handle_stop(self, signum, frame) -> None:
        log.info("Получен сигнал остановки")
        self._running = False

def main():
    parser = argparse.ArgumentParser(description="Автоматическое архивирование по расписанию")
    parser.add_argument("sources", nargs="+", help="Каталоги для архивирования")
    parser.add_argument("-o", "--output", default="./backups",
                        help="Каталог для архивов (по умолчанию ./backups)")
    parser.add_argument("--interval", type=int, default=3600,
                        help="Интервал между архивациями в секундах (по умолчанию 3600)")
    parser.add_argument("--keep", type=int, default=0,
                        help="Хранить N последних архивов каждого каталога (0 = все)")
    parser.add_argument("--once", action="store_true",
                        help="Выполнить однократно и завершить")
    args = parser.parse_args()
    sources = []
    for s in args.sources:
        p = Path(s)
        if not p.exists():
            log.warning("Путь не существует: %s", p)
        sources.append(p)
    if not sources:
        log.error("Не указано ни одного существующего каталога.")
        sys.exit(1)
    archiver = DirectoryArchiver(output_dir=Path(args.output), keep=args.keep)
    scheduler = ArchiveScheduler(archiver, sources, interval=args.interval)
    if args.once:
        scheduler.run_once()
    else:
        scheduler.run_forever()

if __name__ == "__main__":
    main()
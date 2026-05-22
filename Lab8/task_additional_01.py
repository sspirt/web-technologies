import argparse
import logging
import signal
import requests
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

TIMEOUT = 10
HEADERS = {"User-Agent": "SiteMonitor/1.0"}

@dataclass
class CheckResult:
    url: str
    status_code: Optional[int] = None
    response_ms: Optional[float] = None
    available: bool = False
    error: str = ""
    checked_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

class SiteChecker:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def check(self, url: str) -> CheckResult:
        result = CheckResult(url=url)
        try:
            start = time.monotonic()
            resp = self.session.get(url, timeout=TIMEOUT, allow_redirects=True)
            elapsed_ms = (time.monotonic() - start) * 1000
            result.status_code = resp.status_code
            result.response_ms = round(elapsed_ms, 1)
            result.available = resp.status_code < 400
        except requests.exceptions.Timeout:
            result.error = "Таймаут"
        except requests.exceptions.ConnectionError:
            result.error = "Ошибка соединения"
        except requests.exceptions.TooManyRedirects:
            result.error = "Слишком много редиректов"
        except requests.exceptions.RequestException as exc:
            result.error = str(exc)
        return result

class SiteMonitor:
    def __init__(self, urls: list[str], interval: int):
        self.urls = urls
        self.interval = interval
        self.checker = SiteChecker()
        self._running = False

    def run_once(self) -> None:
        results = [self.checker.check(url) for url in self.urls]
        self._report(results)

    def run_forever(self) -> None:
        self._running = True
        signal.signal(signal.SIGINT, self._stop)
        signal.signal(signal.SIGTERM, self._stop)
        log.info("Мониторинг запущен. Сайтов: %d, интервал %d сек",
                 len(self.urls), self.interval)
        while self._running:
            self.run_once()
            self._sleep(self.interval)
        log.info("Мониторинг остановлен")

    @staticmethod
    def _report(results: list[CheckResult]) -> None:
        print(f"\n{'URL':<45} {'Статус':>6} {'Время':>8}  Результат")
        for r in results:
            status = str(r.status_code) if r.status_code else "—"
            ms = f"{r.response_ms:.0f} мс" if r.response_ms else "—"
            info = r.error or "OK"
            print(f"{r.url:<45} {status:>6} {ms:>8}  {info}")
        print()

    def _sleep(self, seconds: int) -> None:
        for _ in range(seconds):
            if not self._running:
                break
            time.sleep(1)

    def _stop(self, *_) -> None:
        self._running = False

def main():
    parser = argparse.ArgumentParser(description="Мониторинг доступности сайтов")
    parser.add_argument("urls", nargs="*", help="URL для проверки")
    parser.add_argument("--file", help="Файл со списком URL (по одному на строку)")
    parser.add_argument("--interval", type=int, default=60,
                        help="Интервал проверки в секундах (по умолчанию 60)")
    parser.add_argument("--once", action="store_true",
                        help="Проверить однократно и завершить")
    args = parser.parse_args()
    urls = list(args.urls)
    if args.file:
        try:
            lines = open(args.file).read().splitlines()
            urls += [l.strip() for l in lines if l.strip() and not l.startswith("#")]
        except OSError as exc:
            log.error("Не удалось прочитать файл сайтов %s", exc)
            sys.exit(1)
    if not urls:
        log.error("Укажите хотя бы один URL")
        sys.exit(1)
    monitor = SiteMonitor(urls, args.interval)
    if args.once:
        monitor.run_once()
    else:
        monitor.run_forever()

if __name__ == "__main__":
    main()
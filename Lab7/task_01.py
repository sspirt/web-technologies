import re
import sys
import time
import logging
import argparse
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".tiff"}
TIMEOUT = 15
MAX_RETRIES = 3


class ImageDownloader:
    def __init__(self, output_dir: str = "images", delay: float = 0.5):
        self.output_dir = Path(output_dir)
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def download_from_url(self, url: str) -> int:
        log.info("Начало обработки страницы: %s", url)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        page_content = self._fetch_page(url)
        if page_content is None:
            log.error("Не удалось загрузить страницу")
            return 0
        image_urls = self._extract_image_urls(page_content, url)
        log.info("Найдено изображений: %d", len(image_urls))
        saved = 0
        for img_url in image_urls:
            if self._download_image(img_url):
                saved += 1
            time.sleep(self.delay)

        log.info("Сохранено: %d / %d", saved, len(image_urls))
        return saved

    def _fetch_page(self, url: str) -> str | None:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.session.get(url, timeout=TIMEOUT)
                response.raise_for_status()
                return response.text
            except requests.exceptions.HTTPError as exc:
                log.warning("HTTP-ошибка (попытка %d/%d): %s", attempt, MAX_RETRIES, exc)
            except requests.exceptions.ConnectionError:
                log.warning("Ошибка соединения (попытка %d/%d)", attempt, MAX_RETRIES)
            except requests.exceptions.Timeout:
                log.warning("Таймаут (попытка %d/%d)", attempt, MAX_RETRIES)
            except requests.exceptions.RequestException as exc:
                log.error("Неизвестная ошибка запроса: %s", exc)
                return None
            time.sleep(2 ** attempt)
        return None

    def _extract_image_urls(self, html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        urls: set[str] = set()
        for tag in soup.find_all("img"):
            for attr in ("src", "data-src", "data-lazy-src", "data-original"):
                src = tag.get(attr, "").strip()
                if src:
                    urls.add(urljoin(base_url, src))
        for tag in soup.find_all("source"):
            srcset = tag.get("srcset", "")
            for part in srcset.split(","):
                src = part.strip().split()[0]
                if src:
                    urls.add(urljoin(base_url, src))
        return [url for url in urls if self._is_image_url(url)]

    @staticmethod
    def _is_image_url(url: str) -> bool:
        path = urlparse(url).path.lower()
        ext = Path(path).suffix
        return ext in IMAGE_EXTENSIONS

    @staticmethod
    def _sanitize_filename(url: str) -> str:
        path = urlparse(url).path
        name = Path(path).name
        name = re.sub(r'[<>:"/\\|?*]', "_", name)
        return name or "image"

    @staticmethod
    def _unique_path(filepath: Path) -> Path:
        if not filepath.exists():
            return filepath
        stem, suffix = filepath.stem, filepath.suffix
        counter = 1
        while True:
            candidate = filepath.with_name(f"{stem}_{counter}{suffix}")
            if not candidate.exists():
                return candidate
            counter += 1

    def _download_image(self, url: str) -> bool:
        filename = self._sanitize_filename(url)
        filepath = self._unique_path(self.output_dir / filename)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.session.get(url, timeout=TIMEOUT, stream=True)
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "")
                if "image" not in content_type and not self._is_image_url(url):
                    log.debug("Пропуск (не изображение): %s", url)
                    return False
                with open(filepath, "wb") as fh:
                    for chunk in response.iter_content(chunk_size=8192):
                        fh.write(chunk)
                log.info("Сохранено: %s", filepath.name)
                return True
            except requests.exceptions.HTTPError as exc:
                log.warning("[%d/%d] HTTP-ошибка %s: %s", attempt, MAX_RETRIES, exc.response.status_code, url)
            except requests.exceptions.ConnectionError:
                log.warning("[%d/%d] Ошибка соединения: %s", attempt, MAX_RETRIES, url)
            except requests.exceptions.Timeout:
                log.warning("[%d/%d] Таймаут: %s", attempt, MAX_RETRIES, url)
            except OSError as exc:
                log.error("Ошибка записи файла %s: %s", filepath, exc)
                return False
            time.sleep(2 ** attempt)
        log.error("Не удалось загрузить: %s", url)
        return False

def main():
    parser = argparse.ArgumentParser(description="Загрузчик изображений с веб страницы")
    parser.add_argument("url", help="URL страницы для анализа")
    parser.add_argument("-o", "--output", default="images",
                        help="Каталог для сохранения (по умолчанию: ./images)")
    parser.add_argument("-d", "--delay", type=float, default=0.5,
                        help="Задержка между запросами в секундах (по умолчанию: 0.5)")
    args = parser.parse_args()
    downloader = ImageDownloader(output_dir=args.output, delay=args.delay)
    count = downloader.download_from_url(args.url)
    sys.exit(0 if count > 0 else 1)

if __name__ == "__main__":
    main()
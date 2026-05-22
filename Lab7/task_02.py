import hashlib
import logging
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import argparse

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
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
TIMEOUT = 20
MAX_RETRIES = 3
DELAY = 0.8


class WallpaperCaveScraper:
    BASE_URL = "https://wallpapercave.com"

    def __init__(self, root_url: str, output_dir: str = "wallpapers", skip_existing: bool = True):
        self.root_url = root_url
        self.output_dir = Path(output_dir)
        self.skip_existing = skip_existing
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._seen_urls: set[str] = set()

    def run(self):
        log.info("Запуск: %s", self.root_url)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        categories = self._get_categories(self.root_url)
        if not categories:
            log.warning("Категории не найдены. Скачиваем изображения прямо со стартовой страницы")
            self._download_images_from_page(self.root_url, self.output_dir)
            return
        log.info("Найдено категорий: %d", len(categories))
        for name, url in categories.items():
            cat_dir = self.output_dir / self._safe_dirname(name)
            cat_dir.mkdir(parents=True, exist_ok=True)
            log.info("Категория: %s → %s", name, url)
            self._download_images_from_page(url, cat_dir)

    def _get_categories(self, url: str) -> dict[str, str]:
        html = self._fetch(url)
        if html is None:
            return {}
        soup = BeautifulSoup(html, "html.parser")
        categories: dict[str, str] = {}
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            full = urljoin(self.BASE_URL, href)
            if re.search(r"/w/[\w-]+-wallpapers$", href) or re.search(r"/categories/[\w-]+$", href):
                text = a.get_text(strip=True) or Path(href).name.replace("-", " ").title()
                if text and full not in categories.values():
                    categories[text] = full
        return categories

    def _download_images_from_page(self, url: str, directory: Path):
        visited_pages: set[str] = set()
        queue = [url]
        while queue:
            page_url = queue.pop(0)
            if page_url in visited_pages:
                continue
            visited_pages.add(page_url)
            html = self._fetch(page_url)
            if html is None:
                continue
            soup = BeautifulSoup(html, "html.parser")
            image_urls = self._extract_image_urls(soup, page_url)
            for img_url in image_urls:
                self._download_single(img_url, directory)
                time.sleep(DELAY)
            next_page = self._find_next_page(soup, page_url)
            if next_page and next_page not in visited_pages:
                queue.append(next_page)

    def _extract_image_urls(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        urls: set[str] = set()
        for tag in soup.find_all("img"):
            for attr in ("src", "data-src", "data-original", "data-lazy"):
                src = (tag.get(attr) or "").strip()
                if src:
                    full = urljoin(base_url, src)
                    if self._is_image_url(full):
                        urls.add(full)
        return list(urls)

    @staticmethod
    def _find_next_page(soup: BeautifulSoup, current_url: str) -> str | None:
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True).lower()
            rel = a.get("rel", [])
            if text in ("next", "→", "»", "следующая") or "next" in rel:
                return urljoin(current_url, a["href"].strip())
        return None

    def _download_single(self, url: str, directory: Path) -> bool:
        if url in self._seen_urls:
            return False
        self._seen_urls.add(url)
        filename = self._sanitize_filename(url)
        filepath = directory / filename
        if self.skip_existing and filepath.exists():
            log.debug("Пропуск (файл уже существует): %s", filename)
            return False
        filepath = self._unique_path(filepath)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, timeout=TIMEOUT, stream=True)
                resp.raise_for_status()
                ct = resp.headers.get("Content-Type", "")
                if "image" not in ct and not self._is_image_url(url):
                    return False
                with open(filepath, "wb") as fh:
                    for chunk in resp.iter_content(8192):
                        fh.write(chunk)
                log.info("Сохранено: %s", filepath)
                return True
            except requests.exceptions.HTTPError as exc:
                log.warning("[%d/%d] HTTP %s: %s", attempt, MAX_RETRIES, exc.response.status_code, url)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                log.warning("[%d/%d] Ошибка сети: %s", attempt, MAX_RETRIES, url)
            except OSError as exc:
                log.error("Ошибка записи: %s", exc)
                return False
            time.sleep(2 ** attempt)
        log.error("Не удалось загрузить: %s", url)
        return False

    def _fetch(self, url: str) -> str | None:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, timeout=TIMEOUT)
                resp.raise_for_status()
                return resp.text
            except requests.exceptions.HTTPError as exc:
                log.warning("[%d/%d] HTTP %s: %s", attempt, MAX_RETRIES, exc.response.status_code, url)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                log.warning("[%d/%d] Ошибка сети: %s", attempt, MAX_RETRIES, url)
            except requests.exceptions.RequestException as exc:
                log.error("Неизвестная ошибка: %s", exc)
                return None
            time.sleep(2 ** attempt)
        return None

    @staticmethod
    def _is_image_url(url: str) -> bool:
        return Path(urlparse(url).path).suffix.lower() in IMAGE_EXTENSIONS

    @staticmethod
    def _sanitize_filename(url: str) -> str:
        name = Path(urlparse(url).path).name
        name = re.sub(r'[<>:"/\\|?*]', "_", name)
        return name or hashlib.md5(url.encode()).hexdigest()[:12]

    @staticmethod
    def _safe_dirname(name: str) -> str:
        return re.sub(r'[<>:"/\\|?*\s]+', "_", name).strip("_") or "misc"

    @staticmethod
    def _unique_path(p: Path) -> Path:
        if not p.exists():
            return p
        stem, suffix, i = p.stem, p.suffix, 1
        while (candidate := p.with_name(f"{stem}_{i}{suffix}")).exists():
            i += 1
        return candidate

def main():
    parser = argparse.ArgumentParser(description="Рекурсивный загрузчик обоев с wallpapercave.com")
    parser.add_argument("url", nargs="?",
                        default="https://wallpapercave.com/categories/anime",
                        help="URL категориальной страницы")
    parser.add_argument("-o", "--output", default="wallpapers",
                        help="Корневой каталог для сохранения")
    parser.add_argument("--no-skip", action="store_true",
                        help="Перекачивать файлы, даже если они уже есть на диске")
    args = parser.parse_args()
    scraper = WallpaperCaveScraper(
        root_url=args.url,
        output_dir=args.output,
        skip_existing=not args.no_skip,
    )
    scraper.run()

if __name__ == "__main__":
    main()
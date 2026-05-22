import argparse
import logging
import sys
from pathlib import Path
from typing import Optional
from PIL import Image, UnidentifiedImageError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".gif"}

class ThumbConfig:
    def __init__(self, size: tuple[int, int] = (256, 256), output_format: str = "JPEG",
                 quality: int = 85, keep_aspect: bool = True, suffix: str = "_thumb"):
        self.size = size
        self.output_format = output_format.upper()
        self.quality = max(1, min(95, quality))
        self.keep_aspect = keep_aspect
        self.suffix = suffix

    @property
    def extension(self) -> str:
        return {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}.get(self.output_format, ".jpg")

class Thumbnailer:
    def __init__(self, config: ThumbConfig):
        self.config = config

    def process_directory(self, source_dir: Path, output_dir: Optional[Path] = None,
                          recursive: bool = False) -> tuple[int, int]:
        if not source_dir.exists():
            log.error("Каталог не существует: %s", source_dir)
            return 0, 0
        out = output_dir or source_dir
        out.mkdir(parents=True, exist_ok=True)
        pattern = "**/*" if recursive else "*"
        files = [file for file in source_dir.glob(pattern)
                 if file.is_file() and file.suffix.lower() in SUPPORTED]
        if not files:
            log.warning("Изображения не найдены в %s", source_dir)
            return 0, 0
        log.info("Найдено изображений: %d", len(files))
        ok = failed = 0
        for path in files:
            dest = self._build_dest_path(path, source_dir, out)
            if self._process_image(path, dest):
                ok += 1
            else:
                failed += 1
        log.info("Создано: %d, Ошибок: %d", ok, failed)
        return ok, failed

    def process_file(self, source: Path, output_dir: Optional[Path] = None) -> bool:
        out = output_dir or source.parent
        out.mkdir(parents=True, exist_ok=True)
        dest = out / (source.stem + self.config.suffix + self.config.extension)
        return self._process_image(source, dest)

    def _process_image(self, source: Path, dest: Path) -> bool:
        try:
            with Image.open(source) as img:
                img = self._convert_mode(img)
                thumb = self._resize(img)
                self._save(thumb, dest)
            log.info("%s → %s (%dx%d)",
                     source.name, dest.name, thumb.width, thumb.height)
            return True

        except UnidentifiedImageError:
            log.warning("Не удалось распознать изображение: %s", source)
        except OSError as exc:
            log.error("Ошибка чтения/записи %s: %s", source, exc)
        except Exception as exc:
            log.error("Неожиданная ошибка при обработке %s: %s", source, exc)
        return False

    def _convert_mode(self, img: Image.Image) -> Image.Image:
        if self.config.output_format == "JPEG" and img.mode not in ("RGB", "L"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                bg.paste(img, mask=img.split()[3])
            else:
                bg.paste(img.convert("RGB"))
            return bg
        return img

    def _resize(self, img: Image.Image) -> Image.Image:
        if self.config.keep_aspect:
            img.thumbnail(self.config.size, Image.LANCZOS)
            return img
        return img.resize(self.config.size, Image.LANCZOS)

    def _save(self, img: Image.Image, dest: Path) -> None:
        kwargs: dict = {}
        if self.config.output_format == "JPEG":
            kwargs["quality"] = self.config.quality
            kwargs["optimize"] = True
        elif self.config.output_format == "WEBP":
            kwargs["quality"] = self.config.quality
        elif self.config.output_format == "PNG":
            kwargs["optimize"] = True
        img.save(dest, format=self.config.output_format, **kwargs)

    def _build_dest_path(self, file: Path, source_dir: Path, output_dir: Path) -> Path:
        rel = file.relative_to(source_dir)
        dest_parent = output_dir / rel.parent
        dest_parent.mkdir(parents=True, exist_ok=True)
        return dest_parent / (file.stem + self.config.suffix + self.config.extension)

def parse_size(s: str) -> tuple[int, int]:
    try:
        w, h = s.lower().split("x")
        return int(w), int(h)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Неверный формат размера '{s}'. Ожидается WxH, например 256x256"
        )

def main():
    parser = argparse.ArgumentParser(description="Генератор превью изображений")
    parser.add_argument("source", help="Каталог с исходными изображениями")
    parser.add_argument("-o", "--output",
                        help="Каталог для превью (по умолчанию рядом с оригиналами)")
    parser.add_argument("--size", type=parse_size, default=(256, 256),
                        metavar="WxH", help="Размер превью (по умолчанию 256x256)")
    parser.add_argument("--format", default="JPEG", choices=["JPEG", "PNG", "WEBP"],
                        help="Формат выходных файлов (по умолчанию JPEG)")
    parser.add_argument("--quality", type=int, default=85,
                        help="Качество JPEG/WEBP 1–95 (по умолчанию 85)")
    parser.add_argument("--no-aspect", action="store_true",
                        help="Не сохранять соотношение сторон (растянуть до точного размера)")
    parser.add_argument("--suffix", default="_thumb",
                        help="Суффикс имени файла (по умолчанию _thumb)")
    parser.add_argument("-r", "--recursive", action="store_true",
                        help="Обрабатывать подкаталоги рекурсивно")
    args = parser.parse_args()
    config = ThumbConfig(
        size=args.size,
        output_format=args.format,
        quality=args.quality,
        keep_aspect=not args.no_aspect,
        suffix=args.suffix,
    )
    thumbnailer = Thumbnailer(config)
    source = Path(args.source)
    output = Path(args.output) if args.output else None
    ok, failed = thumbnailer.process_directory(source, output, recursive=args.recursive)
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
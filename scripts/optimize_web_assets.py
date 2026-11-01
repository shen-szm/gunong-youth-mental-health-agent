"""Generate lightweight WebP variants for performance-critical web assets."""
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "frontend" / "public" / "images"

ASSETS = (
    (PUBLIC / "island" / "heart-island-base.png", (960, 540), 84, True),
    (PUBLIC / "island" / "student-back.png", (96, 221), 86, True),
    (PUBLIC / "guguan" / "guguan-idle.png", (384, 384), 84, True),
    (PUBLIC / "guguan" / "guguan-eating.png", (384, 384), 84, True),
    (PUBLIC / "guguan" / "guguan-happy.png", (384, 384), 84, True),
    (PUBLIC / "guguan" / "guguan-sleeping.png", (384, 384), 84, True),
)


def main() -> None:
    for source, size, quality, pixel_art in ASSETS:
        target = source.with_suffix(".webp")
        with Image.open(source) as image:
            image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            image.thumbnail(size, Image.Resampling.NEAREST if pixel_art else Image.Resampling.LANCZOS)
            image.save(target, "WEBP", quality=quality, method=6)
        before = source.stat().st_size
        after = target.stat().st_size
        print(f"{target.relative_to(ROOT)}: {before} -> {after} bytes")


if __name__ == "__main__":
    main()

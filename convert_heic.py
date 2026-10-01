"""Batch convert iPhone HEIC photos to PNG, JPG, WebP, or AVIF."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path


def find_images(inputs: list[Path], output_dir: Path, extension: str, recursive: bool = False) -> list[tuple[Path, Path]]:
    jobs: list[tuple[Path, Path]] = []
    seen_sources: set[Path] = set()
    seen_targets: dict[str, Path] = {}

    for item in inputs:
        if not item.exists():
            raise ValueError(f"Input does not exist: {item}")
        if item.is_file():
            if item.suffix.lower() != ".heic":
                raise ValueError(f"Expected a .heic file: {item}")
            candidates = [(item, Path(item.name))]
        elif item.is_dir():
            candidates = [
                (source, source.relative_to(item))
                for source in sorted(item.rglob("*") if recursive else item.iterdir())
                if source.is_file() and source.suffix.lower() == ".heic"
            ]
        else:
            raise ValueError(f"Input is not a file or directory: {item}")

        for source, relative in candidates:
            resolved_source = source.resolve()
            if resolved_source in seen_sources:
                continue
            seen_sources.add(resolved_source)
            target = output_dir / relative.with_suffix(extension)
            target_key = str(target.resolve()).casefold()
            previous = seen_targets.get(target_key)
            if previous is not None:
                raise ValueError(
                    f"Two inputs would write {target}: {previous} and {source}. "
                    "Use separate output folders."
                )
            seen_targets[target_key] = source
            jobs.append((source, target))

    return jobs


def convert(source: Path, target: Path, image_format: str, max_dimension: int | None, max_width: int | None, max_height: int | None) -> None:
    from PIL import Image, ImageOps

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with Image.open(source) as original:
            # The HEIF plugin applies container rotation; this also handles any
            # remaining EXIF orientation and removes that orientation tag.
            image = ImageOps.exif_transpose(original)
            save_options: dict[str, object] = {}
            if icc_profile := image.info.get("icc_profile"):
                save_options["icc_profile"] = icc_profile
            if exif := image.getexif():
                save_options["exif"] = exif.tobytes()

            if any(value is not None for value in (max_dimension, max_width, max_height)):
                width_limit = min(value for value in (image.width, max_dimension, max_width) if value is not None)
                height_limit = min(value for value in (image.height, max_dimension, max_height) if value is not None)
                image.thumbnail((width_limit, height_limit), Image.Resampling.LANCZOS)

            if image_format == "jpg":
                if image.mode == "RGBA":
                    background = Image.new("RGB", image.size, "white")
                    background.paste(image, mask=image.getchannel("A"))
                    image = background
                elif image.mode != "RGB":
                    image = image.convert("RGB")
                save_options.update(quality=95, subsampling=0, optimize=True)
                output_format = "JPEG"
            else:
                if image.mode not in ("RGB", "RGBA"):
                    image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
                output_format = image_format.upper()
                if image_format == "webp":
                    save_options.update(lossless=True, exact=True)
                elif image_format == "avif":
                    save_options.update(quality=95, subsampling="4:2:0")

            with tempfile.NamedTemporaryFile(
                dir=target.parent, prefix=f".{target.stem}-", suffix=target.suffix, delete=False
            ) as handle:
                temporary = Path(handle.name)
            image.save(temporary, format=output_format, **save_options)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="HEIC files and/or folders")
    parser.add_argument("--all", dest="recursive", action="store_true", help="Include HEIC files in subfolders")
    parser.add_argument("--f", dest="format", choices=("png", "jpg", "webp", "avif"), default="png", help="Output format (default: png)")
    parser.add_argument("--o", dest="output_dir", type=Path, default=Path("output"), metavar="PATH", help="Output folder (default: ./output)")
    parser.add_argument("--s", dest="max_dimension", type=int, metavar="PIXELS", help="Maximum length of the longest edge in pixels; keeps aspect ratio")
    parser.add_argument("--max", dest="max_dimension", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--w", dest="max_width", type=int, metavar="PIXELS", help="Maximum width in pixels; keeps aspect ratio")
    parser.add_argument("--h", dest="max_height", type=int, metavar="PIXELS", help="Maximum height in pixels; keeps aspect ratio")
    parser.add_argument("-s", dest="max_dimension", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--x", dest="overwrite", action="store_true", help="Replace existing output files")
    # Accept commands written for earlier versions without cluttering --help.
    parser.add_argument("--format", dest="format", choices=("png", "jpg", "webp", "avif"), help=argparse.SUPPRESS)
    parser.add_argument("--output-dir", dest="output_dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--max-dimension", dest="max_dimension", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--overwrite", dest="overwrite", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    for option, value in (("--s", args.max_dimension), ("--w", args.max_width), ("--h", args.max_height)):
        if value is not None and value < 1:
            parser.error(f"{option} must be a positive number of pixels")

    try:
        from pillow_heif import register_heif_opener
    except ImportError:
        print("Missing dependency. Install with: python -m pip install -r requirements.txt", file=sys.stderr)
        return 2
    register_heif_opener(thumbnails=False)

    if args.format in ("webp", "avif"):
        from PIL import features

        if not features.check(args.format):
            print(f"This Pillow installation cannot encode {args.format.upper()} images. Install a Pillow wheel with {args.format.upper()} support.", file=sys.stderr)
            return 2

    try:
        jobs = find_images(args.inputs, args.output_dir, f".{args.format}", args.recursive)
    except ValueError as exc:
        parser.error(str(exc))
    if not jobs:
        parser.error("No .heic files found in the supplied inputs")

    converted = skipped = failed = 0
    for source, target in jobs:
        if target.exists() and not args.overwrite:
            print(f"SKIP {target} (already exists)")
            skipped += 1
            continue
        try:
            convert(source, target, args.format, args.max_dimension, args.max_width, args.max_height)
        except Exception as exc:
            print(f"FAIL {source}: {exc}", file=sys.stderr)
            failed += 1
        else:
            print(f"OK   {source} -> {target}")
            converted += 1

    print(f"Converted: {converted}, skipped: {skipped}, failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

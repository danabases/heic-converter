# HEIC photo converter

Convert `.heic` photos to PNG, JPG, WebP, or AVIF. You can give the tool one file, several files, or a folder. It searches folders recursively and leaves the originals untouched.

## Install

Install Python 3.10 or newer. From this project's folder, run the commands for your shell. The `.venv` folder holds this tool's Python packages locally.

macOS (Bash or zsh):

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
py -m venv .venv
.\.venv\scripts\python.exe -m pip install -r requirements.txt
```

## Convert a file

These examples read `photo.heic` from the `images` folder and write `photo.png` to an `output` folder beside the project folder. Run the command from the project folder.

macOS:

```bash
./.venv/bin/python convert_heic.py "./images/photo.heic" --o "../output/" --f png
```

Windows:

```powershell
.\.venv\scripts\python.exe convert_heic.py ".\images\photo.heic" --o "..\output\" --f png
```

The value after `--o` is the output folder path. For example, on Windows you can use `--o "c:\output"` for an absolute path. The tool creates the folder if needed.

## Convert a folder

To convert every `.heic` file under `images`, including its subfolders:

macOS:

```bash
./.venv/bin/python convert_heic.py "./images" --o "./output" --f jpg
```

Windows:

```powershell
.\.venv\scripts\python.exe convert_heic.py ".\images" --o ".\output" --f jpg
```

The output keeps the input's subfolder structure. Each output file keeps the source name with a new extension.

## Switches

| Switch | Meaning |
| --- | --- |
| `--o PATH` | Output folder. Default: `./output`. |
| `--f FORMAT` | `png`, `jpg`, `webp`, or `avif`. Default: `png`. |
| `--x` | Replace output files that already exist. Without it, existing files are skipped. |
| `--s PIXELS` | Limit the longest edge to this many pixels. |
| `--w PIXELS` | Limit the width to this many pixels. |
| `--h PIXELS` | Limit the height to this many pixels. |

The resize switches keep the photo's proportions and never enlarge it. You can use `--w` or `--h` alone, or both together to fit within a width × height box. If you also use `--s`, the tightest limits apply. For example:

```powershell
.\.venv\scripts\python.exe convert_heic.py ".\images\photo.heic" --o ".\output" --f png --w 1200 --h 800
```

Add `--x` to regenerate an output file after changing its size.

PNG and WebP exports are lossless after HEIC decoding. JPG and AVIF exports use fixed high-quality settings. AVIF uses 4:2:0 chroma for Windows viewer compatibility. The tool exports the main photo, applies its saved orientation, and copies available EXIF metadata and color profile data.

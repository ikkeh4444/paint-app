# Paint App

A simple paint app that runs in the browser. Plain HTML/CSS/JavaScript with an
HTML5 canvas — no dependencies and no build step.

## Run it

Open `index.html` directly in a browser, or serve the folder:

```bash
python3 -m http.server 8000
```

Then visit http://localhost:8000

## Features

- Freehand drawing with mouse or touch
- Color picker plus a preset palette
- Adjustable brush size
- Eraser, undo (also `Ctrl/Cmd + Z`), clear canvas
- Save the drawing as a PNG

## Desktop version

`desktop/paint.py` is a desktop version built on Python's standard library
(Tkinter) — no pip installs needed, but Tkinter must be present
(on Debian/Ubuntu: `sudo apt install python3-tk`).

```bash
python3 desktop/paint.py
```

- Open existing PNG images (`Ctrl+O`) and edit them
- Save / Save As PNG (`Ctrl+S`)
- Mouse painting, color picker + palette, brush size, eraser, undo (`Ctrl+Z`), clear
- PNG reading/writing is implemented in pure stdlib in `desktop/pngio.py`
  (supports 8/16-bit gray, RGB, palette, gray+alpha and RGBA PNGs, flattened
  onto white; non-interlaced only)

# SnapForge (Educational Clean-Room Screenshot Tool)

SnapForge is an **independent, from-scratch** screenshot + annotation tool inspired by the general *category* of capture tools.

## Important legal note

- This project is **not copied** from Flameshot code.
- No source files from Flameshot are included here.
- Similar functionality is implemented from public product behavior and original design/code.
- This is **not legal advice**. If you plan commercial/public distribution, consult a lawyer for license and IP review.

## Current MVP features

- Full-screen capture via Qt
- Region selection overlay
- Basic annotation tools:
  - Pen
  - Rectangle
- Copy to clipboard
- Save to PNG

## Planned parity roadmap

- Arrow, text, line, marker tools
- Blur/pixelate tools
- Undo/redo
- Global hotkeys
- Configurable shortcuts and theme
- Multi-screen handling improvements
- Optional upload integrations

## Run

```bash
python3 -m pip install -r requirements.txt
python3 -m snapforge
```

(Or editable install)

```bash
python3 -m pip install -e .
snapforge
```

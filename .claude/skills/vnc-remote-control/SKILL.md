---
name: vnc-remote-control
description: Use when you need to observe and control a machine over VNC/RFB - take a screenshot, read the screen (including OCR), click a pixel or a labeled UI element, type text, or press keys - using the vnc-remote-control CLI. Triggers on driving or automating a guest GUI through VNC (a VM console, a boot screen, a login prompt, a dialog).
---

# Driving a machine over VNC with vnc-remote-control

`vnc-remote-control` is a small CLI that drives a VNC/RFB server: screenshot,
click, type, press keys, and OCR the screen. This skill explains how to use it
to reliably control a guest, including how to click the right pixel every time.

## Prerequisites

- The `vnc-remote-control` command on PATH (`pip install vnc-remote-control` or
  `uv tool install vnc-remote-control`).
- `tesseract` installed (required for `ocr` and `click-text`):
  `apt-get install tesseract-ocr`, `brew install tesseract`, or
  `choco install tesseract`.
- The VNC server's host and port. Every command takes `--port`; `--host`
  defaults to `127.0.0.1`. Examples below use `--port 5901`.

## The one rule that makes clicking reliable

RFB pointer coordinates are absolute framebuffer pixels, and a screenshot is
taken at the native framebuffer resolution. So a coordinate you read off the
screenshot is the exact coordinate to click. There is no scale factor.

The usual cause of "I clicked the wrong place" is reading coordinates off a
scaled image. Do not let your image viewer downscale the screenshot, and do not
guess at coordinates from a resized view.

## The control loop

1. Capture and look. Run `screenshot out.png`. It prints `resolution: WxH` on
   stdout. View `out.png` at native size.
2. Decide where to act. Read the (x, y) directly off the screenshot, or use OCR
   to locate UI text (see below).
3. Verify a coordinate before committing (optional but cheap). Run
   `screenshot out.png --mark X,Y` and confirm the crosshair sits on the target.
   `--grid 50` overlays a coordinate grid if you want a ruler.
4. Act: `click X Y`, or click by label with `click-text`. Before you `type`,
   click into the target text field: a window you just opened or launched
   usually does NOT have keyboard focus yet, so typing goes nowhere. Click the
   field first, then `type` / `key`.
5. Confirm. Take a fresh screenshot and check the result before the next step.
   Always re-screenshot; never assume an action landed.

## Commands

```bash
# see the screen (prints "resolution: WxH")
vnc-remote-control --port 5901 screenshot /tmp/s.png

# verify a candidate click point with a crosshair
vnc-remote-control --port 5901 screenshot /tmp/s.png --mark 640,480

# read the screen: each line is "<cx> <cy> <w>x<h> conf=<n> <text>"
# cx,cy is the center, i.e. the point to click
vnc-remote-control --port 5901 ocr
vnc-remote-control --port 5901 ocr --grep "Sign in"

# click: by pixel, or (more reliable) by on-screen label
vnc-remote-control --port 5901 click 640 480
vnc-remote-control --port 5901 click-text "Next"

# type text (literal keysyms; the server maps the layout) and press keys
vnc-remote-control --port 5901 type "chkdsk c: /f" --enter
vnc-remote-control --port 5901 type "user@host"
vnc-remote-control --port 5901 key enter
vnc-remote-control --port 5901 key esc
```

## Clicking: prefer labels over pixels

When the target has visible text, `click-text "Label"` (or `ocr --grep` then
`click <cx> <cy>`) is more reliable than reading a pixel, because it clicks the
center of the recognized word and does not depend on your coordinate estimate.
Fall back to pixel clicks for icons and controls with no text, and use
`--mark X,Y` to confirm the pixel first.

## Typing and keyboard layout

`type` sends literal keysyms: each character's keysym is its code point, exactly
like a standard VNC client. It does no client-side translation. The guest
keyboard layout is a server setting: openvmm is layout-aware (its
`--vnc-keyboard-layout` flag, which on Proxmox the ovm shim sets from the VM's
`keyboard:` key) and maps keysyms into the guest layout. When the server layout
matches the guest, every character types correctly, including symbols.

A text field must have keyboard focus before you `type` (see the focus tip
below).

## Focus before typing

This is the most common typing failure. After you open or launch a window
(taskbar search, the Run box, an application), it often does NOT have keyboard
focus, so `type` goes nowhere. Concrete lesson: a freshly-opened editor showed
nothing typed until it was clicked to focus. Always click into the actual text
field first, then `type`. If text seems to vanish, re-screenshot, click the
field, and type again.

## Practical tips

- Focus before typing: click the target field, then `type` (see above).
- One observable step at a time: act, then screenshot to confirm.
- Boot screens and dialogs: screenshot first to see the current state (spinner,
  login, BSOD, dialog) before deciding what to send.
- If OCR misreads small text, take the screenshot and read the coordinates
  yourself off the native image.

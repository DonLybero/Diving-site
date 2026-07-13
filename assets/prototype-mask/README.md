# Dive-Mask Hologram — 3D Prototype Video

A looping video of a **wireframe (prototype) scuba dive mask** rendered as a
teal hologram, projected upward from a projector stand. Deliberately *not* a
full-colour 3D model — just the glowing wireframe blueprint.

- **`dive-mask-hologram.webm`** — the video. 1080×1350 (4:5), 30 fps, 6 s,
  seamless 360° loop. VP8/WebM.
- **`scene.html`** — the self-contained scene. Pure canvas 2D; procedurally
  builds the mask geometry (lofted skirt, twin domed lenses, nose pocket,
  split head strap) and the projector stand (pedestal, emitter, light cone,
  floor grid, scanlines, flicker, blueprint HUD). Exposes
  `window.renderFrame(i)` for a deterministic, loop-safe frame at index `i`.
- **`capture.js`** — headless-Chromium (Playwright) frame grabber.

## Regenerate
```bash
node capture.js                     # writes frames/f0000.jpg … f0179.jpg
FF=/opt/pw-browsers/ffmpeg-1011/ffmpeg-linux
cat $(ls frames/*.jpg | sort) | "$FF" -y -f image2pipe -c:v mjpeg -framerate 30 \
    -i pipe:0 -c:v libvpx -b:v 5M -crf 8 -auto-alt-ref 0 -pix_fmt yuv420p \
    dive-mask-hologram.webm
```
`node capture.js 40` renders a single frame to `test.png` for quick previews.

> WebM (VP8) is used because the only ffmpeg available in this environment is
> Playwright's stripped build (VP8/WebM + MJPEG decode only — no H.264/MP4).
> To produce an MP4, run the same JPEG frames through a full ffmpeg:
> `ffmpeg -framerate 30 -i frames/f%04d.jpg -c:v libx264 -pix_fmt yuv420p dive-mask-hologram.mp4`

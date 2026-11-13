# HydroBuddy Animation Plan

> **Decision (2026-11-13):** the character is a smooth cartoon water drop drawn
> live by the app as vector art (a code-drawn variant of Way 4). There are no
> sprite files: poses and timing live in `hydrobuddy/ui/character_anim.py` and
> the drawing in `hydrobuddy/ui/character.py`. The sprite-sheet contract in
> section 2 is not used. The rest of this document is kept as background on
> the options that were considered.

## 1. First, a reality check on the tools

| Tool | What it can do here | What it can't |
|---|---|---|
| **Claude Opus 5.5** | Write image/video prompts, write the whole conversion pipeline (ffmpeg, Python), **generate art as code** (pixel grids, SVG, procedural frames), and review exported frames for consistency (it can see images) | It does not output raster images or video directly |
| **Gemini** (image models + Veo video) | Generate the character design, pose sheets, and short video clips | Keep a character perfectly consistent across clips; produce transparent backgrounds; produce clean pixel art |

So the realistic split is that **Gemini makes pixels, Opus makes the plan, prompts, pipeline and code.**

### About GIF

- GIF has 256 colours and **1-bit transparency** (each pixel is either fully visible or invisible).
- That is fine for crisp **pixel art**.
- It looks jagged for smooth, anti-aliased art floating on your desktop.
- **Recommended runtime format: PNG sprite sheet + JSON.** It has perfect alpha, is tiny, and is trivial to play in Qt with a `QTimer`. Keep GIF/WebP only as previews to share.
- If you want a single file, use **animated WebP** (full alpha; Qt's `QMovie` plays it).

---

## 2. The animation contract (define this before making any art)

All four approaches below must produce assets that fit this contract, so the app never changes.

```json
{
  "frame_size": [128, 128],
  "scale": 2,
  "anchor": "bottom-center",
  "states": {
    "appear":    { "file": "appear.png",    "frames": 8,  "fps": 12, "loop": false, "next": "idle" },
    "idle":      { "file": "idle.png",      "frames": 8,  "fps": 8,  "loop": true },
    "celebrate": { "file": "celebrate.png", "frames": 12, "fps": 12, "loop": false, "next": "leave" },
    "sad":       { "file": "sad.png",       "frames": 10, "fps": 10, "loop": false, "next": "leave" },
    "leave":     { "file": "leave.png",     "frames": 8,  "fps": 12, "loop": false, "next": null }
  }
}
```

The rules for the assets:

- Each file is a horizontal strip of equal frames with a transparent background.
- The character stays in the same spot. Feet sit on the same baseline in every frame of every state.
- `idle` must loop seamlessly, so its last frame flows into its first.
- Every state starts and ends close to the idle pose, so transitions don't "pop".
- Upscale with **nearest-neighbour** only (no blur) if it's pixel art.

The minimum to ship is `idle` + `celebrate`. Add the others later.

---

## 3. Top 4 ways to make the character

### Way 1: AI concept + hand-finished pixel sprite sheets (Gemini, then Aseprite)

**Best quality and consistency for pixel art. The most manual work.**

1. **Design.** Opus writes prompts, Gemini generates 10–20 character concepts. Pick one.
2. **Turnaround/pose sheet.** Ask Gemini for the same character in key poses (neutral, drinking, cheering, sad, waving) on a flat white background.
   Prompt shape: *"Pixel art character sheet, 64×64 sprite style, cute water-drop mascot named Hydro, 5 poses in a row: neutral, drinking from a glass, cheering, sad, waving goodbye. Same character, same proportions, limited 16-colour palette, plain white background, no shadows."*
3. **Clean up in [Aseprite](https://www.aseprite.org/)** (about $20, or compile it free).
   - Downscale to a 64×64 grid and fix the palette to about 16 colours.
   - Redraw the key frames by hand using the AI images as reference.
   - Add in-between frames. For an idle bob, 4–8 frames are enough.
4. **Export** with *File, Export Sprite Sheet*: horizontal strip plus JSON data, one per state.
5. **Review.** Show Opus the strips and ask it to check baseline drift, palette consistency and loop seams.

| Pros | Cons |
|---|---|
| Crisp, consistent, tiny files, fully on-brand | Needs some drawing time (a beginner needs about 1–3 days) |
| Easy to add new states later | You must learn basic Aseprite |

---

### Way 2: Gemini video (Veo), then frames, then background removal, then a sprite sheet or GIF

**This is your idea. The most "alive" motion. The hardest to keep consistent.**

1. **Make one master still** of the character (Gemini image), full body, centred, on **solid pure green `#00FF00`**.
2. **Image-to-video with Veo**, one short clip (2–4 s) per state, **always starting from the same master still** so the character stays the same.
   Prompt shape: *"The character from the image takes a sip from its glass and smiles, static camera, locked-off shot, no zoom, no camera movement, character stays centred, solid flat green background, no shadows, no other objects."*
   - Generate 3–5 takes per state and keep the best.
   - For `idle`, ask for subtle breathing/bobbing. Make it loop by cross-fading or ping-ponging (described below).
3. **Extract and key out the background** with ffmpeg:
   ```bash
   ffmpeg -i drink.mp4 -vf "fps=12,chromakey=0x00FF00:0.12:0.05,scale=256:-1:flags=lanczos" frames/drink_%03d.png
   ```
   If the green spills onto the character, use `rembg` (a Python AI background remover) on each frame instead.
4. **Clean up frames** with a Python script Opus writes:
   - Crop all frames to the same bounding box and align them on the feet baseline. This removes the jitter.
   - Optionally *pixelate*: downscale to 64 px nearest-neighbour and quantise to 16–32 colours. This hides AI wobble and matches a pixel-art look.
   - Drop frames to a hand-picked 8–12.
5. **Seamless idle loop**: either ping-pong (frames 1→N→1) or trim to a point where the last frame ≈ the first.
6. **Pack**:
   ```bash
   magick montage frames/drink_*.png -tile x1 -geometry +0+0 -background none drink.png
   ffmpeg -framerate 12 -i frames/drink_%03d.png -loop 0 -lossless 1 drink.webp
   ffmpeg -framerate 12 -i frames/drink_%03d.png -vf "split[a][b];[a]palettegen=reserve_transparent=1[p];[b][p]paletteuse" drink.gif
   ```

| Pros | Cons |
|---|---|
| Rich, natural motion; little drawing skill needed | The character's face, colours and proportions drift between clips |
| Fast to try ideas | Background keying leaves fringes; AI videos jitter and morph |
| | Costs money per generation; many retries are needed |
| | Big raw files; a lot of cleanup to make frames usable |

**Make it work by** always using image-to-video from one master still, using a green background, using a static camera, pixelating at the end, and using short clips.

---

### Way 3: Opus generates the character as code (procedural pixel art)

**No external AI art, no drawing. Fully reproducible. The most consistent. The least expressive.**

1. Opus designs the character as a **pixel grid in code**, for example a 32×32 palette-indexed array per body part (body, eyes, mouth, arm, glass).
2. Animations are **code transforms** on those parts:
   - `idle`: a 1–2 px vertical bob plus a blink every N frames.
   - `celebrate`: squash and stretch, a jump, the arm with the glass raised, and sparkle pixels.
   - `sad`: droop by 2 px, eyes change to a sad sprite, a single tear pixel falls.
   - `appear`/`leave`: slide up from the taskbar, or a pop with a squash.
3. A Python script (Pillow) renders every state to PNG strips matching the contract, and writes previews as GIFs.
4. You iterate by telling Opus "bigger eyes", "make it blue", or "slower bob", and re-run the script.

| Pros | Cons |
|---|---|
| Perfect consistency, zero cost, regenerates in seconds | Simple, "geometric" look; limited personality |
| Version-controlled; easy to tweak and add states | Complex motion (actually drinking) is hard to do convincingly |
| Unblocks the app immediately | |

**Great as the placeholder you ship with in Phase 6, or as the final art if you like a minimal style.**

---

### Way 4: Rigged 2D cut-out character (parts animated live in the app)

**Smooth, tiny, infinitely tweakable. A different (non-pixel) look.**

1. Get the character as **separate layered parts** (body, head, eyes, mouth shapes, arms, glass):
   - Generate them with Gemini (*"…isolated parts on white background: body, left arm, right arm, 3 mouth shapes, 2 eye states"*), then trace or vectorise them in Inkscape or Figma.
   - Or have Opus write it directly as **SVG**. A simple mascot like a water drop is very doable in SVG.
2. Animate in either of these ways:
   - **In the app**: Qt `QPropertyAnimation` / `QGraphicsItem` transforms for bobbing, rotating an arm, swapping the mouth, and blinking. Opus writes this code.
   - **In a tool**: [Rive](https://rive.app) or Lottie (After Effects plus Bodymovin, or the free LottieFiles editor), exported then rendered to frames.
3. Optionally bake to PNG strips that match the contract, so the app code stays identical to the other ways.

| Pros | Cons |
|---|---|
| Very smooth motion at any size; tiny files | Not pixel art; needs a clean vector style |
| Easy to add expressions (swap a mouth) | Rigging takes some setup |
| Live animation can react (e.g. progress fills a body of water!) | Rive/Lottie playback in Qt needs baking or a web view |

---

## 4. Comparison

| | Way 1 Pixel (Aseprite) | Way 2 Veo video | Way 3 Opus code | Way 4 Rigged 2D |
|---|---|---|---|---|
| Visual quality | ★★★★ | ★★★★ (if cleaned) | ★★ | ★★★★ |
| Consistency | ★★★★★ | ★★ | ★★★★★ | ★★★★★ |
| Your effort | High | Medium–High (cleanup) | Very low | Medium |
| Money | ~$20 one-off | Pay per generation | $0 | $0–low |
| Time to first usable asset | 2–4 days | 1–3 days | Hours | 1–2 days |
| Easy to add new states | Yes | Hard (consistency) | Yes | Yes |
| Risk | Low | **High** | Very low | Medium |

## 5. Recommendation

1. **Now, in Phase 6:** use **Way 3**. Opus generates a code-drawn water-drop character in hours. This unblocks the app and proves the animation contract.
2. **In parallel:** run a **1-day spike of Way 2** with just the `celebrate` state. Judge it honestly:
   if after pixelation it looks consistent with a master still, continue for the other states; if it drifts, stop.
3. **Final art:** whichever of Way 1 or Way 2 survives the spike. Use Way 4 only if you prefer a smooth vector style over pixel art.

Because everything goes through the same contract, each swap is just replacing files in `assets/character/`.

## 6. Spike checklist for Way 2 (your video idea)

- [ ] Master still on `#00FF00` is chosen.
- [ ] Three Veo takes of `celebrate` are made from that still.
- [ ] ffmpeg extraction plus chroma key is done; check edges at 200% zoom.
- [ ] Align, crop and pixelate with the script; compare side-by-side with the master still.
- [ ] Ask Opus to review the frames for drift, jitter and fringes.
- [ ] Decide: continue or switch to Way 1/3.

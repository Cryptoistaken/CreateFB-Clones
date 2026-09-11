"""Number badge overlay for clone launcher icons.

Design B (circle-safe): a bright royal-blue scalloped seal with a centered
white number, placed top-left *inside* the icon border. Geometry is expressed
as fractions of the icon size so one code path serves every density:

  - badge box  : 30% of icon size, inset 11% from the top-left edges
  - seal       : 8-lobe rosette filling the badge box
  - number     : bold, white, centered, auto-fit so "10" fits the seal
  - fixed box  : identical size/position for numbers 1-10

The 11% inset keeps the whole seal inside the launcher circle mask
(inscribed circle), so the number stays visible even where the launcher
circle-crops legacy icons. The source icon file is never modified in place -
a badged copy is returned/written.

Usage:
    badge_icons.py icon.png 5 out.png          # badge one icon
    badge_icons.py --dir work --number 3       # badge all res icons in a decode dir
    badge_icons.py --preview icon.png out.png  # contact sheet 1-10
"""

import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BLUE = (29, 78, 216, 255)      # bright royal blue (approved reference)
WHITE = (255, 255, 255, 255)
BOX_FRAC = 0.30                # badge box edge as fraction of icon size
INSET_FRAC = 0.11              # top-left inset as fraction of icon size
LOBES = 8                      # scallops of the seal
SAMPLES = 256
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "DejaVuSans-Bold.ttf",
)


def validate_number(number):
    """Accept ints 1-10, reject everything else loudly."""
    if type(number) is not int or not 1 <= number <= 10:
        raise ValueError(f"badge number must be an int from 1 to 10, got {number!r}")
    return number


def badge_box(size):
    """(left, top, edge) of the fixed badge box for a square icon of `size`."""
    edge = round(size * BOX_FRAC)
    inset = round(size * INSET_FRAC)
    return inset, inset, edge


def seal_polygon(cx, cy, radius, samples=SAMPLES, lobes=LOBES):
    """Scalloped-seal outline approximating the approved reference shape."""
    pts = []
    for k in range(samples):
        t = 2 * math.pi * k / samples
        r = radius * (0.82 + 0.18 * math.cos(lobes * t))
        pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return pts


def load_font(edge):
    """Bold font sized so even '10' fits the seal; errors if none found."""
    for path in FONT_CANDIDATES:
        try:
            ImageFont.truetype(path, 10)
            return path
        except OSError:
            continue
    raise OSError("no bold TTF font found (tried: %s)" % ", ".join(FONT_CANDIDATES))


def fit_font(draw, text, radius, font_path):
    """Largest bold size whose width fits the seal interior."""
    size = max(8, int(radius * 0.75))
    while size > 8:
        font = ImageFont.truetype(font_path, size)
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= radius * 1.02:
            return font
        size -= 2
    return ImageFont.truetype(font_path, 8)


def add_number_badge(icon, number):
    """Return a copy of square RGBA `icon` with the number badge composited."""
    number = validate_number(number)
    if icon.width != icon.height:
        raise ValueError(f"launcher icon must be square, got {icon.size}")
    base = icon.convert("RGBA")
    size = base.width
    left, top, edge = badge_box(size)
    cx, cy, radius = left + edge / 2.0, top + edge / 2.0, edge / 2.0

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.polygon(seal_polygon(cx, cy, radius), fill=BLUE)
    out = Image.alpha_composite(base, overlay)

    draw = ImageDraw.Draw(out)
    font = fit_font(draw, str(number), radius, load_font(edge))
    draw.text((cx, cy - radius * 0.03), str(number), font=font,
              fill=WHITE, anchor="mm")
    return out


def badge_content_description(app_name, number):
    """Accessible name announcing which numbered clone an icon belongs to."""
    return f"{app_name}, number {validate_number(number)}"


def badge_icon_file(icon_path, number, out_path=None):
    """Badge one icon file; defaults to overwriting in place."""
    with Image.open(icon_path) as img:
        badged = add_number_badge(img, number)
    badged.save(out_path or icon_path)
    return str(out_path or icon_path)


def badge_decode_dir(decode_dir, number):
    """Badge every launcher icon in an apktool decode dir (all densities)."""
    number = validate_number(number)
    hits = sorted(Path(decode_dir).glob("res/*/ic_launcher.png"))
    if not hits:
        raise FileNotFoundError(f"no launcher icons under {decode_dir}/res/")
    for path in hits:
        badge_icon_file(path, number)
    return [str(p) for p in hits]


def render_preview(icon_path, out_path):
    """Contact sheet of the base icon badged 1-10 (for review artifacts)."""
    with Image.open(icon_path) as img:
        base = img.convert("RGBA")
    cell = 300
    sheet = Image.new("RGBA", (5 * cell, 2 * cell + 60), (255, 255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(load_font(cell), 26)
    except OSError:
        font = ImageFont.load_default()
    for n in range(1, 11):
        badged = add_number_badge(base.resize((cell, cell)), n)
        col, row = (n - 1) % 5, (n - 1) // 5
        sheet.alpha_composite(badged, (col * cell, row * (cell + 30)))
        draw.text((col * cell + cell / 2, row * (cell + 30) + cell + 8),
                  f"number {n}", font=font, fill=(32, 33, 36, 255), anchor="ma")
    sheet.convert("RGB").save(out_path)
    return str(out_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Badge launcher icons 1-10.")
    parser.add_argument("icon", nargs="?", help="input icon PNG")
    parser.add_argument("number", nargs="?", help="badge number 1-10")
    parser.add_argument("output", nargs="?", help="output PNG")
    parser.add_argument("--dir", help="apktool decode dir: badge all res icons")
    parser.add_argument("--preview", help="write 1-10 contact sheet to this path")
    args = parser.parse_args(argv)

    if args.preview:
        if not args.icon:
            parser.error("--preview needs an input icon")
        print(render_preview(args.icon, args.preview))
    elif args.dir:
        if args.number is None:
            parser.error("--dir needs a number")
        for p in badge_decode_dir(args.dir, int(args.number)):
            print(p)
    else:
        if not (args.icon and args.number and args.output):
            parser.error("need icon number output (or --dir / --preview)")
        print(badge_icon_file(args.icon, int(args.number), args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())

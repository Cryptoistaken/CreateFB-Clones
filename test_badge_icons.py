"""Tests for badge_icons.py (run: python3 -m unittest discover -s . -p 'test_*.py')."""

import math
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from badge_icons import (
    BLUE,
    WHITE,
    add_number_badge,
    badge_box,
    badge_content_description,
    main,
)

SIZE = 512


def make_icon():
    """Deterministic dark stand-in for the launcher icon."""
    return Image.new("RGBA", (SIZE, SIZE), (4, 6, 17, 255))


def changed_pixels(before, after):
    """Coordinates where badging altered the image."""
    w, h = before.size
    px0, px1 = before.load(), after.load()
    return [(x, y) for y in range(h) for x in range(w) if px0[x, y] != px1[x, y]]


def changed_bbox(before, after):
    pts = changed_pixels(before, after)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def luminance(rgb):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


class BadgeTest(unittest.TestCase):
    def test_numbers_1_to_9_render(self):
        for n in range(1, 10):
            with self.subTest(n=n):
                out = add_number_badge(make_icon(), n)
                self.assertEqual(out.size, (SIZE, SIZE))
                self.assertTrue(changed_pixels(make_icon(), out))

    def test_number_10_renders(self):
        out = add_number_badge(make_icon(), 10)
        self.assertTrue(changed_pixels(make_icon(), out))

    def test_one_consistent_box_for_all_numbers(self):
        """Same badge size/position for 1-10 (10 must not resize or move it)."""
        boxes = {n: changed_bbox(make_icon(), add_number_badge(make_icon(), n))
                 for n in range(1, 11)}
        first = boxes[1]
        for n, box in boxes.items():
            with self.subTest(n=n):
                for a, b in zip(first, box):
                    self.assertAlmostEqual(a, b, delta=2)

    def test_invalid_values_rejected(self):
        for bad in (0, 11, -1, 100, "3", 3.5, None, True):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    add_number_badge(make_icon(), bad)

    def test_top_left_position(self):
        """Badge lives in the top-left quadrant with an inset from the edges."""
        left, top, edge = badge_box(SIZE)
        self.assertGreaterEqual(left, 1)
        self.assertGreaterEqual(top, 1)
        box = changed_bbox(make_icon(), add_number_badge(make_icon(), 5))
        self.assertLess(box[0], SIZE // 2)
        self.assertLess(box[1], SIZE // 2)
        self.assertAlmostEqual(box[0], left, delta=2)
        self.assertAlmostEqual(box[1], top, delta=2)

    def test_badge_inside_icon_boundary(self):
        """No badged pixel may leave the icon (rounded-square) boundary."""
        for n in (1, 10):
            with self.subTest(n=n):
                pts = changed_pixels(make_icon(), add_number_badge(make_icon(), n))
                for x, y in pts:
                    self.assertGreaterEqual(x, 0)
                    self.assertGreaterEqual(y, 0)
                    self.assertLess(x, SIZE)
                    self.assertLess(y, SIZE)

    def test_badge_survives_circle_mask(self):
        """Design B: every badged pixel sits inside the inscribed circle."""
        for n in (1, 10):
            with self.subTest(n=n):
                pts = changed_pixels(make_icon(), add_number_badge(make_icon(), n))
                cx = cy = SIZE / 2.0
                for x, y in pts:
                    dist = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
                    self.assertLessEqual(dist, SIZE / 2.0 + 1)

    def test_original_icon_preserved(self):
        """Pixels outside the badge box are byte-identical to the source."""
        src = make_icon()
        out = add_number_badge(src, 7)
        left, top, edge = badge_box(SIZE)
        px0, px1 = src.load(), out.load()
        for y in range(0, SIZE, 7):
            for x in range(0, SIZE, 7):
                inside = left - 1 <= x <= left + edge + 1 and top - 1 <= y <= top + edge + 1
                if not inside:
                    self.assertEqual(px0[x, y], px1[x, y], f"pixel {(x, y)} modified")

    def test_badge_uses_royal_blue(self):
        """The seal background matches the approved royal-blue."""
        out = add_number_badge(make_icon(), 4)
        px = out.load()
        blue = sum(1 for y in range(0, SIZE, 4) for x in range(0, SIZE, 4)
                   if px[x, y][:3] == BLUE[:3])
        self.assertGreater(blue, 100)

    def test_number_contrast(self):
        """White number on royal blue must meet WCAG AA (ratio >= 4.5)."""
        l1 = luminance(WHITE)
        l2 = luminance(BLUE)
        ratio = (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)
        self.assertGreaterEqual(ratio, 4.5)

    def test_number_ink_present_for_all(self):
        """Near-white number pixels exist inside every badge 1-10."""
        for n in range(1, 11):
            with self.subTest(n=n):
                out = add_number_badge(make_icon(), n)
                left, top, edge = badge_box(SIZE)
                px = out.load()
                ink = sum(1 for y in range(top, top + edge, 2)
                          for x in range(left, left + edge, 2)
                          if all(v > 230 for v in px[x, y][:3]))
                self.assertGreater(ink, 20, f"no number ink for {n}")

    def test_accessibility_label(self):
        self.assertEqual(badge_content_description("DGDcreateFB 1", 1),
                         "DGDcreateFB 1, number 1")
        self.assertEqual(badge_content_description("DGDcreateFB 10", 10),
                         "DGDcreateFB 10, number 10")
        with self.assertRaises(ValueError):
            badge_content_description("DGDcreateFB", 0)

    def test_non_square_icon_rejected(self):
        with self.assertRaises(ValueError):
            add_number_badge(Image.new("RGBA", (256, 128)), 3)

    def test_cli_dir_badges_all_densities(self):
        with tempfile.TemporaryDirectory() as tmp:
            for density in ("drawable-mdpi-v4", "drawable-xxhdpi-v4"):
                d = Path(tmp) / "res" / density
                d.mkdir(parents=True)
                make_icon().save(d / "ic_launcher.png")
            with self.assertRaises(SystemExit):
                main(["--dir", tmp])  # missing --number
            self.assertEqual(main(["--dir", tmp, "--number", "4"]), 0)
            for density in ("drawable-mdpi-v4", "drawable-xxhdpi-v4"):
                with Image.open(Path(tmp) / "res" / density / "ic_launcher.png") as img:
                    self.assertTrue(changed_pixels(make_icon(), img.convert("RGBA")))

    def test_cli_dir_missing_icons_fails_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                main(["--dir", tmp, "--number", "2"])

    def test_cli_preview_sheet(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = str(Path(tmp) / "icon.png")
            out = str(Path(tmp) / "preview.png")
            make_icon().save(src)
            self.assertEqual(main(["--preview", src, out]), 0)
            with Image.open(out) as img:
                self.assertEqual(img.size, (1500, 660))


if __name__ == "__main__":
    unittest.main()

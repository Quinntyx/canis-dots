"""Linear-callout regressions. Run with the same build123d interpreter as the helper:
uv run --no-project --with build123d python3 path/to/test_part_drawing.py
"""
import importlib.util
import math
from pathlib import Path
from types import SimpleNamespace
from build123d import Align, Box, Pos
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
HELPER = next(path for path in [ROOT / 'bin/part-drawing.py',
                               ROOT / 'bin/executable_part-drawing.py'] if path.exists())
spec = importlib.util.spec_from_file_location('part_drawing', HELPER)
drawing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drawing)


class LinearDimensions(unittest.TestCase):
    def dimension(self, p1, p2, scale=1.0):
        # Analytic front-view coordinates isolate callout layout from OCCT HLR.
        view = drawing.View.__new__(drawing.View)
        view.name = 'front'
        view.spans = ((-100, 100, -100, 100), (-100, 100, -100, 100))
        sheet = drawing.SvgSheet(SimpleNamespace(scale=scale), scale)
        drawing.draw_dim_linear(sheet, view, (115, 92), scale, p1, p2, 'test', 12)
        root = ET.fromstring('<svg>' + ''.join(sheet.body) + '</svg>')
        line = next(item for item in root.findall('line') if item.get('class') == 'dim')
        a = tuple(float(line.get(key)) for key in ['x1', 'y1'])
        b = tuple(float(line.get(key)) for key in ['x2', 'y2'])
        return a, b, view, root

    def test_full_horizontal_span(self):
        a, b, _, _ = self.dimension((-30, 0, 5), (30, 0, 5))
        self.assertAlmostEqual(math.dist(a, b), 60)

    def test_full_vertical_span(self):
        a, b, _, _ = self.dimension((30, 0, 0), (30, 0, 40))
        self.assertAlmostEqual(math.dist(a, b), 40)

    def test_thin_part_dimension_keeps_direction(self):
        a, b, _, _ = self.dimension((30, 0, 0), (30, 0, 5))
        self.assertAlmostEqual(math.dist(a, b), 5)
        self.assertLess(b[1], a[1])

    def test_scaled_span(self):
        a, b, _, _ = self.dimension((-30, 0, 5), (30, 0, 5), scale=0.5)
        self.assertAlmostEqual(math.dist(a, b), 30)

    def test_centered_dimension_has_a_defined_perpendicular_lane(self):
        a, b, _, _ = self.dimension((-30, 0, 0), (30, 0, 0))
        self.assertAlmostEqual(math.dist(a, b), 60)
        self.assertAlmostEqual(abs(a[1] - 92), 12)

    def test_oblique_lane_preserves_projected_endpoints(self):
        p1, p2 = (10, 0, 10), (40, 0, 50)
        a, b, view, _ = self.dimension(p1, p2)
        first = drawing._page(view, (115, 92), 1, p1)
        last = drawing._page(view, (115, 92), 1, p2)
        vx, vy = last[0] - first[0], last[1] - first[1]
        self.assertAlmostEqual(math.dist(a, b), 50, places=2)
        self.assertAlmostEqual((a[0] - first[0]) * vx + (a[1] - first[1]) * vy, 0, places=2)
        self.assertAlmostEqual((b[0] - last[0]) * vx + (b[1] - last[1]) * vy, 0, places=2)


class OrthographicViews(unittest.TestCase):
    def setUp(self):
        self.plate = Box(60, 40, 5, align=(Align.CENTER, Align.CENTER, Align.MIN))

    def test_axis_aligned_front_and_left_spans(self):
        for name, expected in [('front', (60, 5)), ('left', (40, 5))]:
            view = drawing.View(name, self.plate)
            actual = tuple(hi - lo for lo, hi in view.sample_extent)
            for value, target in zip(actual, expected):
                self.assertAlmostEqual(value, target, places=5, msg=name)

    def test_translation_preserves_projection_scale(self):
        shifted = Pos(125, -77, 32) * self.plate
        for name in ['front', 'top', 'left']:
            original = drawing.View(name, self.plate)
            moved = drawing.View(name, shifted)
            for before, after in zip(original.sample_extent, moved.sample_extent):
                self.assertAlmostEqual(before[1] - before[0], after[1] - after[0],
                                       places=5, msg=name)


if __name__ == '__main__':
    unittest.main()

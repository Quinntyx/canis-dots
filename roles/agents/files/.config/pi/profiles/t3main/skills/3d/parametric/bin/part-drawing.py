#!/usr/bin/env python3
"""Compose a first-angle multiview technical drawing sheet from a verified part.

Reads a STEP file of the verified solid, projects explicit engineering views —
front, top placed below it, and the left-hand view placed to its right, by
first-angle convention, plus an isometric view — through build123d hidden-line
removal, and writes one A4-landscape SVG sheet in millimeter units with
dimension callouts, a center mark, and a title block. Dimension labels come
from the caller; each should denote one Stage 2 parameter so the sheet traces
requirements. Convert to PNG with rsvg-convert when a raster is needed.

Usage:
  python3 part-drawing.py --part out/part.step --out out/part-sheet.svg \
      --name Part [--material PLA] [--note text] \
      [--dims out/part-dims.json] [--views front,top,left,iso] [--scale 0.5]

Dims JSON: a list of annotations in model millimeters.
  linear:   {"view": "front", "p1": [x,y,z], "p2": [x,y,z], "label": "30"}
  diameter: {"view": "top", "center": [x,y,z], "radius": 2.15,
             "label": "Ø4.30", "angle": 45}
Diameter callouts belong on the view where the circular face is planar to the
sheet. Every callout needs the view to be one of those drawn.
Requires build123d importable as for the build scripts (use the interpreter
that cad-preflight probed, or the uv alternate route).
"""

import argparse
import datetime
import json
import math
import sys

from build123d import import_step

A4_W, A4_H = 420.0, 297.0
BORDER = 5.0
TEXT_H = 2.6

# Screen-right and screen-up expressed as world directions per view.
VIEW_PAIRS = {
    "front": ((1, 0, 0), (0, 0, 1)),
    "top": ((1, 0, 0), (0, 1, 0)),
    "left": ((0, 1, 0), (0, 0, 1)),
    "iso": ((0.94, -0.34, 0.0), (-0.12, 0.33, 0.94)),
}
# Eye positions only steer the hidden-line removal; orthographic throughout.
VIEW_EYES = {
    "front": (0, -1000, 0),
    "top": (0, 0, 1000),
    "left": (-1000, 0, 0),
    "iso": (800, -700, 480),
}
CELLS = {"front": (115, 92), "top": (115, 196), "left": (240, 92), "iso": (345, 88)}
CELL_SIZE = {"front": (110, 84), "top": (110, 84), "left": (110, 84), "iso": (114, 112)}
SCALE_STEPS = (1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.25, 0.2, 0.15, 0.1, 0.05)


def corners_of(part):
    bb = part.bounding_box()
    return [
        (bb.min.X + bb.size.X * a, bb.min.Y + bb.size.Y * b, bb.min.Z + bb.size.Z * c)
        for a, b, c in [
            (0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1),
            (1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1),
        ]
    ]


class View:
    """One projected view with sampled edges and a calibrated mapping."""

    def __init__(self, name, part):
        self.name = name
        right, up = VIEW_PAIRS[name]
        center = part.bounding_box().center()
        self.center = (center.X, center.Y, center.Z)
        eye = tuple(self.center[i] + VIEW_EYES[name][i] for i in range(3))
        vis, hid = part.project_to_viewport(
            eye,
            viewport_up=up,
            look_at=self.center,
        )
        self.visible = [self._sample(e) for e in vis]
        self.hidden = [self._sample(e) for e in hid]
        pts = [p for pl in self.visible + self.hidden for p in pl]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self.sample_extent = ((min(xs), max(xs)), (min(ys), max(ys)))
        self.spans = None
        if name != "iso":
            self._calibrate(part, right, up)

    @staticmethod
    def _sample(edge, n=33):
        return [
            (edge.position_at(i / (n - 1)).X, edge.position_at(i / (n - 1)).Y)
            for i in range(n)
        ]

    @staticmethod
    def _dot(a, b):
        return sum(a[i] * b[i] for i in range(3))

    def _calibrate(self, part, right, up):
        """Pair each analytic model extent with the matching HLR sample extent.

        The HLR output plane's axis order depends on OCCT internals; pairing
        ranges by aspect ratio removes the guesswork so callouts land on the
        drawn geometry. Mirrors are validated by the skill's visual check.
        """
        vals = [vpair_value((right, up), p) for p in corners_of(part)]
        rx = (min(v[0] for v in vals), max(v[0] for v in vals))
        ry = (min(v[1] for v in vals), max(v[1] for v in vals))
        (sx0, sx1), (sy0, sy1) = self.sample_extent
        if math.log((sx1 - sx0) / max(sy1 - sy0, 1e-9) / ((rx[1] - rx[0]) / max(ry[1] - ry[0], 1e-9))) ** 2 < 0.12:
            self.spans = (
                (rx[0], rx[1], sx0, sx1),
                (ry[0], ry[1], sy0, sy1),
            )
        else:
            self.spans = (
                (ry[0], ry[1], sx0, sx1),
                (rx[0], rx[1], sy0, sy1),
            )

    def project(self, point):
        """Model point -> sample-frame coordinates through the calibrated spans."""
        if self.spans is None:
            raise ValueError("isometric views do not carry dimension callouts")
        right, up = VIEW_PAIRS[self.name]
        r = self._dot(right, point)
        u = self._dot(up, point)
        (fx0, fx1, sx0, sx1), (fy0, fy1, sy0, sy1) = self.spans[0], self.spans[1]
        return (
            sx0 + _lerp(r, fx0, fx1, sx0, sx1),
            sy0 + _lerp(u, fy0, fy1, sy0, sy1),
        )

def _lerp(v, f0, f1, s0, s1):
    return (v - f0) * (s1 - s0) / max(f1 - f0, 1e-9)


def vpair_value(pair, point):
    right, up = pair
    return (View._dot(right, point), View._dot(up, point))


def draw_view(svg, view, cell, scale):
    cx, cy = cell
    for pl in view.visible:
        svg.polyline([(cx + scale * x, cy - scale * y) for x, y in pl], "vis")
    for pl in view.hidden:
        svg.polyline([(cx + scale * x, cy - scale * y) for x, y in pl], "hid")


def _page(view, cell, scale, point):
    cx, cy = cell
    x, y = view.project(point)
    return cx + scale * x, cy - scale * y


def draw_dim_linear(svg, view, cell, scale, p1, p2, label, offset):
    x1, y1 = _page(view, cell, scale, p1)
    x2, y2 = _page(view, cell, scale, p2)
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 3.0:
        raise ValueError(f"dimension {label!r} is too small to draw")
    ux, uy = dx / length, dy / length
    a, b = (x1, y1), (x2, y2)
    mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    # Translate both projected endpoints perpendicular to their dimension line.
    # A centered dimension uses the positive normal as its deterministic lane.
    nx, ny = -uy, ux
    side = 1.0 if nx * (mx - cell[0]) + ny * (my - cell[1]) >= 0 else -1.0
    ox, oy = nx * side, ny * side
    pa = (a[0] + ox * offset, a[1] + oy * offset)
    pb = (b[0] + ox * offset, b[1] + oy * offset)
    for point, o in ((a, pa), (b, pb)):
        svg.line(point[0] + ox * 1.2, point[1] + oy * 1.2, o[0] + ox * 2.0, o[1] + oy * 2.0, "ext")
    svg.line(pa[0], pa[1], pb[0], pb[1], "dim")
    _arrow(svg, pa, ux, uy, 1.0)
    _arrow(svg, pb, ux, uy, -1.0)
    # Label lane: perpendicular to the dimension line, on the same side the
    # dim line was offset toward, so text never crosses the stroke.
    spx, spy = -uy, ux
    lane = spx * ox + spy * oy
    s = 1.0 if lane >= 0 else -1.0
    lx_lane, ly_lane = spx * s, spy * s
    if abs(lx_lane) >= abs(ly_lane):
        svg.text(
            (pa[0] + pb[0]) / 2.0 + lx_lane * 1.2,
            (pa[1] + pb[1]) / 2.0 + 1.0,
            label,
            anchor="end" if lx_lane < 0 else "start",
        )
    else:
        svg.text(
            (pa[0] + pb[0]) / 2.0,
            (pa[1] + pb[1]) / 2.0 + (2.8 if ly_lane > 0 else -1.2),
            label,
        )


def _arrow(svg, tip, ux, uy, direction):
    px, py = -uy, ux
    for s in (1.0, -1.0):
        svg.line(
            tip[0],
            tip[1],
            tip[0] + ux * 2.4 * direction + px * 0.8 * s,
            tip[1] + uy * 2.4 * direction + py * 0.8 * s,
            "dim",
        )


def draw_dim_diameter(svg, view, cell, scale, center, radius, label, angle_deg):
    x0, y0 = _page(view, cell, scale, center)
    r = scale * radius
    cross = max(r * 1.8, 4.5)
    svg.line(x0 - cross, y0, x0 + cross, y0, "center")
    svg.line(x0, y0 - cross, x0, y0 + cross, "center")
    a = math.radians(angle_deg)
    ex, ey = math.cos(a), -math.sin(a)
    tip = (x0 + ex * r, y0 + ey * r)
    end = (x0 + ex * (r + 14.0), y0 + ey * (r + 14.0))
    svg.line(end[0], end[1], tip[0], tip[1], "dim")
    ll = math.hypot(end[0] - tip[0], end[1] - tip[1])
    _arrow(svg, tip, (end[0] - tip[0]) / ll, (end[1] - tip[1]) / ll, -1.0)
    svg.text(end[0] + ex * 2.0, end[1] + ey * 2.0 + 1.0, label)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--part", required=True, help="STEP file of the verified solid")
    parser.add_argument("--out", required=True, help="output SVG sheet path")
    parser.add_argument("--dims", help="JSON list of dimension annotations")
    parser.add_argument("--name", default="Part")
    parser.add_argument("--material", default="—")
    parser.add_argument("--note", default="")
    parser.add_argument("--views", default="front,top,left,iso")
    parser.add_argument("--scale", type=float, help="explicit sheet scale")
    args = parser.parse_args(argv)

    part = import_step(args.part)
    wanted = [v.strip() for v in args.views.split(",") if v.strip()]
    unknown = [v for v in wanted if v not in CELLS]
    if unknown:
        raise SystemExit(f"unknown view(s): {', '.join(unknown)}")
    if not wanted:
        raise SystemExit("no requested view is defined")
    views = {v: View(v, part) for v in wanted}

    scale = args.scale
    if scale is None:
        fits = {}
        for v, view in views.items():
            (sx0, sx1), (sy0, sy1) = view.sample_extent
            w, h = CELL_SIZE[v]
            fits[v] = min(w / max(sx1 - sx0, 1e-9), h / max(sy1 - sy0, 1e-9))
        fit = min(fits.values())
        scale = next((s for s in SCALE_STEPS if s <= fit), fit)

    dims = []
    if args.dims:
        with open(args.dims) as dfile:
            dims = json.load(dfile)
    for d in dims:
        if d["view"] not in views:
            raise SystemExit(f"dimension references a view not drawn: {d['view']!r}")

    sheet = SvgSheet(args, scale)
    for v in wanted:
        draw_view(sheet, views[v], CELLS[v], scale)
    for d in dims:
        is_diameter = d.get("kind") == "diameter" or (
            "center" in d and "radius" in d
        )
        if is_diameter:
            draw_dim_diameter(sheet, views[d["view"]], CELLS[d["view"]], scale,
                              d["center"], d["radius"], d["label"], d.get("angle", 45.0))
        else:
            draw_dim_linear(sheet, views[d["view"]], CELLS[d["view"]], scale, d["p1"],
                            d["p2"], d["label"], d.get("offset", 12.0))
    with open(args.out, "w") as out:
        out.write(sheet.render())

    print(json.dumps({
        "out": args.out,
        "scale": {"value": scale, "label": sheet.scale_label},
        "views": wanted,
    }))
    return 0


class SvgSheet:
    """A4-landscape sheet writer; coordinates are millimeters."""

    def __init__(self, args, scale):
        self.args = args
        self.scale = scale
        self.scale_label = args.scale and f"1:{round(1 / args.scale)}" or "1:1"
        if args.scale is None:
            self.scale_label = _pretty_label(scale)
        self.body = []

    def polyline(self, pts, cls):
        d = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
        self.body.append(f'<polyline points="{d}" class="{cls}" />')

    def line(self, x1, y1, x2, y2, cls=""):
        self.body.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}"'
            + (f' class="{cls}"' if cls else "")
            + " />"
        )

    def text(self, x, y, content, size=TEXT_H, weight="normal", anchor="middle"):
        content = (
            str(content).replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        self.body.append(
            f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}" '
            f'font-weight="{weight}" font-family="system-ui, sans-serif">'
            f"{content}</text>"
        )

    def render(self):
        w, h = A4_W, A4_H
        tw, th = 132.0, 26.0
        tx, ty = w - BORDER - tw, h - BORDER - th
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" '
            f'viewBox="0 0 {w} {h}">',
            "<style>",
            ".vis{fill:none;stroke:#000;stroke-width:0.35}",
            ".hid{fill:none;stroke:#000;stroke-width:0.25;stroke-dasharray:2.4 1.1}",
            ".dim{fill:none;stroke:#000;stroke-width:0.2}",
            ".ext{fill:none;stroke:#000;stroke-width:0.16}",
            ".center{fill:none;stroke:#000;stroke-width:0.16;stroke-dasharray:5 1 1 1}",
            "text{fill:#000;stroke:none}",
            ".tb{fill:none;stroke:#000;stroke-width:0.4}",
            "</style>",
            f'<rect x="{BORDER}" y="{BORDER}" width="{w - 2 * BORDER}" '
            f'height="{h - 2 * BORDER}" fill="white" stroke="black" stroke-width="0.5" />',
        ]
        parts += self.body
        parts += self._title_block(tx, ty, tw, th)
        parts.append("</svg>")
        return "\n".join(parts)

    def _title_block(self, tx, ty, tw, th):
        def tb(x1, y1, x2, y2):
            self_parts = [
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="tb" />'
            ]
            return self_parts

        parts = [
            f'<rect x="{tx:.1f}" y="{ty:.1f}" width="{tw:.1f}" height="{th:.1f}" class="tb" />',
            f'<line x1="{tx:.1f}" y1="{ty + 12:.1f}" x2="{tx + tw:.1f}" y2="{ty + 12:.1f}" class="tb" />',
            f'<text x="{tx + 4:.1f}" y="{ty + 8.4:.1f}" font-size="4.2" '
            f'font-family="system-ui, sans-serif">{self.args.name}</text>',
            f'<text x="{tx + tw - 4:.1f}" y="{ty + 8.4:.1f}" font-size="2.6" '
            f'text-anchor="end" font-family="system-ui, sans-serif">'
            f"{datetime.date.today().isoformat()}</text>",
            f'<text x="{tx + 4:.1f}" y="{ty + 18.6:.1f}" font-size="2.6" '
            f'font-family="system-ui, sans-serif">Scale {self.scale_label}  ·  mm  ·  '
            "First angle (ISO-E)  ·  build123d STEP</text>",
        ]
        if self.args.material and self.args.material != "—":
            parts.append(
                f'<text x="{tx + 4:.1f}" y="{ty + 23.6:.1f}" font-size="2.6" '
                f'font-family="system-ui, sans-serif">Material: {self.args.material}</text>'
            )
        if self.args.note:
            parts.append(
                f'<text x="{tx + 72:.1f}" y="{ty + 23.6:.1f}" font-size="2.6" '
                f'font-family="system-ui, sans-serif">{self.args.note}</text>'
            )
        return parts


def _pretty_label(scale):
    if abs(scale - 1.0) < 1e-9:
        return "1:1"
    for k in range(1, 21):
        if abs(scale - 1.0 / k) < 1e-9:
            return f"1:{k}"
    return f"1:{round(1 / scale)}"


if __name__ == "__main__":
    sys.exit(main())

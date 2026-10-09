# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""Evaluate the branch-bg terminal background mapping, current and proposed.

Run from anywhere inside the repository:

    uv run --no-project docs/branch-bg-colour-eval.py
    uv run --no-project docs/branch-bg-colour-eval.py --show      # ANSI swatches
    uv run --no-project docs/branch-bg-colour-eval.py --c3-data c3_data.json

The current mapping is loaded from the hook itself, so this script measures the
shipped code rather than a copy. Both mappings go through the same metrics.

Sources for the constants and reference values used below:

- Oklab matrices and test table: https://bottosson.github.io/posts/oklab/
- One JND is 0.02 in Oklab (deltaEOK) and 2 in CIE Lab (deltaE2000); deltaEOK
  under-estimates colourfulness differences: https://www.w3.org/TR/css-color-4/
  sections 14.2.1 and 20.4
- CIEDE2000 test pairs: Sharma, Wu and Dalal,
  https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/
- WCAG 2 relative luminance and contrast ratio:
  https://www.w3.org/WAI/WCAG22/Understanding/contrast-enhanced
- APCA 0.0.98G-4g constants: https://github.com/Myndex/apca-w3
- Farthest-point palette selection: Glasbey et al. 2007,
  https://strathprints.strath.ac.uk/30312/
- C3 colour naming model (optional input): https://github.com/uwdata/c3,
  Heer and Stone 2012, https://idl.uw.edu/papers/color-naming-models
"""

import argparse
import ast
import hashlib
import importlib.util
import itertools
import json
import math
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

HOOK_PATH = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "denubis-hook-branch-bg"
    / "hooks"
    / "branch-bg.py"
)

# One just-noticeable difference, as documented by CSS Color 4 section 14.2.1.
JND_OK = 0.02
JND_00 = 2.0
# Multiples of one JND reported throughout. 1x is the documented threshold. 5x
# matches the deltaE2000 = 10 level below which categorical-palette optimisers
# penalise a pair (arXiv 2407.14742, describing Palettailor). 2.5x is this
# script's own midpoint and has no source.
LEVELS = (1.0, 2.5, 5.0)

# Ghostty 1.3.1 default palette entry 8, from `ghostty +show-config --default`.
ANSI_BRIGHT_BLACK = "#666666"

# ---------------------------------------------------------------------------
# BEGIN PROPOSED MAPPING. Python 3.9-compatible, standard library only, so the
# block can be lifted into the hook beside a baked palette table.
# `check_proposed_block_parses_on_39` parses it with the 3.9 grammar.
# ---------------------------------------------------------------------------
PROPOSED_MAIN_NAMES = ("main", "master")


def proposed_colour(repo_id, branch, palette):
    """Repo picks a colour family; main is its base, a branch one of its steps.

    `palette` is a sequence of families. Each family is a sequence of hex
    strings: the base colour first, then its branch steps.
    """
    repo_hash = int(hashlib.sha256(repo_id.encode()).hexdigest()[:8], 16)
    family = palette[repo_hash % len(palette)]
    if branch in PROPOSED_MAIN_NAMES:
        return family[0]
    steps = family[1:]
    branch_hash = int(hashlib.sha256(branch.encode()).hexdigest()[:8], 16)
    return steps[branch_hash % len(steps)]


# ---------------------------------------------------------------------------
# END PROPOSED MAPPING
# ---------------------------------------------------------------------------


def check_proposed_block_parses_on_39():
    """Parse the proposed block with the Python 3.9 grammar.

    `feature_version` is best effort: it rejects newer syntax, not newer library
    calls. The block calls only `hashlib.sha256`, `int`, and `len`.
    """
    source = Path(__file__).read_text(encoding="utf-8")
    start = source.index("# BEGIN PROPOSED MAPPING")
    end = source.index("# END PROPOSED MAPPING")
    ast.parse(source[start:end], feature_version=(3, 9))


# ----------------------------- colour maths --------------------------------


def decode_channel(encoded):
    """Gamma-encoded sRGB channel to linear light (IEC 61966-2-1)."""
    if encoded <= 0.04045:
        return encoded / 12.92
    return ((encoded + 0.055) / 1.055) ** 2.4


def encode_channel(linear):
    """Linear light to an 8-bit sRGB channel."""
    linear = min(1.0, max(0.0, linear))
    if linear <= 0.0031308:
        encoded = 12.92 * linear
    else:
        encoded = 1.055 * linear ** (1 / 2.4) - 0.055
    return round(encoded * 255)


LINEAR = tuple(decode_channel(i / 255) for i in range(256))


def hex_to_bytes(colour):
    value = colour.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def linear_rgb(colour):
    return tuple(LINEAR[c] for c in hex_to_bytes(colour))


def linear_rgb_to_oklab(rgb):
    red, green, blue = rgb
    long = 0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue
    medium = 0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue
    short = 0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue
    l_, m_, s_ = math.cbrt(long), math.cbrt(medium), math.cbrt(short)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklch_to_linear_rgb(lightness, chroma, hue_deg):
    """Oklch to linear sRGB, coefficients from Ottosson's reference code."""
    a = chroma * math.cos(math.radians(hue_deg))
    b = chroma * math.sin(math.radians(hue_deg))
    l_ = lightness + 0.3963377774 * a + 0.2158037573 * b
    m_ = lightness - 0.1055613458 * a - 0.0638541728 * b
    s_ = lightness - 0.0894841775 * a - 1.2914855480 * b
    long, medium, short = l_**3, m_**3, s_**3
    return (
        4.0767416621 * long - 3.3077115913 * medium + 0.2309699292 * short,
        -1.2684380046 * long + 2.6097574011 * medium - 0.3413193965 * short,
        -0.0041960863 * long - 0.7034186147 * medium + 1.7076147010 * short,
    )


def max_chroma(lightness, hue_deg):
    """Largest Oklch chroma that stays inside sRGB at this lightness and hue."""
    low, high = 0.0, 0.4
    for _ in range(30):
        mid = (low + high) / 2
        rgb = oklch_to_linear_rgb(lightness, mid, hue_deg)
        if min(rgb) >= 0.0 and max(rgb) <= 1.0:
            low = mid
        else:
            high = mid
    return low


def oklch_hex(lightness, hue_deg, chroma_cap):
    """The most colourful in-gamut colour at a lightness and hue, up to a cap."""
    chroma = min(max_chroma(lightness, hue_deg), chroma_cap)
    rgb = oklch_to_linear_rgb(lightness, chroma, hue_deg)
    return "#" + "".join(f"{encode_channel(c):02x}" for c in rgb)


def xyz_to_oklab(xyz):
    """XYZ (D65) to Oklab through the M1 and M2 matrices of the Oklab post."""
    x, y, z = xyz
    long = 0.8189330101 * x + 0.3618667424 * y - 0.1288597137 * z
    medium = 0.0329845436 * x + 0.9293118715 * y + 0.0361456387 * z
    short = 0.0482003018 * x + 0.2643662691 * y + 0.6338517070 * z
    l_, m_, s_ = math.cbrt(long), math.cbrt(medium), math.cbrt(short)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def linear_rgb_to_xyz(rgb):
    red, green, blue = rgb
    return (
        0.4124564 * red + 0.3575761 * green + 0.1804375 * blue,
        0.2126729 * red + 0.7151522 * green + 0.0721750 * blue,
        0.0193339 * red + 0.1191920 * green + 0.9503041 * blue,
    )


def xyz_to_lab(xyz):
    """XYZ to CIE L*a*b* with the D65 white of sRGB."""

    def f(t):
        if t > (6 / 29) ** 3:
            return math.cbrt(t)
        return t / (3 * (6 / 29) ** 2) + 4 / 29

    fx, fy, fz = f(xyz[0] / 0.95047), f(xyz[1] / 1.0), f(xyz[2] / 1.08883)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e_2000(lab1, lab2):
    """CIEDE2000 colour difference, after Sharma, Wu and Dalal (2005)."""
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2
    c_bar = (math.hypot(a1, b1) + math.hypot(a2, b2)) / 2
    g = 0.5 * (1 - math.sqrt(c_bar**7 / (c_bar**7 + 25**7)))
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if c1p else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if c2p else 0.0
    d_l, d_c = l2 - l1, c2p - c1p
    if c1p * c2p == 0:
        d_h_angle = 0.0
        h_bar = h1p + h2p
    else:
        d_h_angle = h2p - h1p
        if d_h_angle > 180:
            d_h_angle -= 360
        elif d_h_angle < -180:
            d_h_angle += 360
        if abs(h1p - h2p) <= 180:
            h_bar = (h1p + h2p) / 2
        elif h1p + h2p < 360:
            h_bar = (h1p + h2p + 360) / 2
        else:
            h_bar = (h1p + h2p - 360) / 2
    d_h = 2 * math.sqrt(c1p * c2p) * math.sin(math.radians(d_h_angle / 2))
    l_bar, c_bar_p = (l1 + l2) / 2, (c1p + c2p) / 2
    t = (
        1
        - 0.17 * math.cos(math.radians(h_bar - 30))
        + 0.24 * math.cos(math.radians(2 * h_bar))
        + 0.32 * math.cos(math.radians(3 * h_bar + 6))
        - 0.20 * math.cos(math.radians(4 * h_bar - 63))
    )
    d_theta = 30 * math.exp(-(((h_bar - 275) / 25) ** 2))
    r_c = 2 * math.sqrt(c_bar_p**7 / (c_bar_p**7 + 25**7))
    s_l = 1 + 0.015 * (l_bar - 50) ** 2 / math.sqrt(20 + (l_bar - 50) ** 2)
    s_c = 1 + 0.045 * c_bar_p
    s_h = 1 + 0.015 * c_bar_p * t
    r_t = -math.sin(math.radians(2 * d_theta)) * r_c
    return math.sqrt(
        (d_l / s_l) ** 2
        + (d_c / s_c) ** 2
        + (d_h / s_h) ** 2
        + r_t * (d_c / s_c) * (d_h / s_h)
    )


def wcag_luminance(colour):
    red, green, blue = linear_rgb(colour)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def wcag_contrast(colour_a, colour_b):
    la, lb = wcag_luminance(colour_a), wcag_luminance(colour_b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def apca_lc(text, background):
    """APCA 0.0.98G-4g lightness contrast; negative for light text on dark."""

    def screen_y(colour):
        red, green, blue = ((c / 255) ** 2.4 for c in hex_to_bytes(colour))
        y = 0.2126729 * red + 0.7151522 * green + 0.0721750 * blue
        return y if y > 0.022 else y + (0.022 - y) ** 1.414

    text_y, bg_y = screen_y(text), screen_y(background)
    if abs(bg_y - text_y) < 0.0005:
        return 0.0
    if bg_y > text_y:
        sapc = (bg_y**0.56 - text_y**0.57) * 1.14
        return 0.0 if sapc < 0.1 else (sapc - 0.027) * 100
    sapc = (bg_y**0.65 - text_y**0.62) * 1.14
    return 0.0 if sapc > -0.1 else (sapc + 0.027) * 100


class Colour:
    """A hex colour with its Oklab and CIE Lab coordinates."""

    __slots__ = ("hex", "lab", "oklab")

    def __init__(self, colour):
        self.hex = colour
        rgb = linear_rgb(colour)
        self.oklab = linear_rgb_to_oklab(rgb)
        self.lab = xyz_to_lab(linear_rgb_to_xyz(rgb))

    @property
    def chroma(self):
        return math.hypot(self.oklab[1], self.oklab[2])

    @property
    def hue(self):
        return math.degrees(math.atan2(self.oklab[2], self.oklab[1])) % 360


def d_ok(a, b):
    return math.dist(a.oklab, b.oklab)


def d_00(a, b):
    return delta_e_2000(a.lab, b.lab)


def jnd(a, b):
    """Difference in JND units, counted only when both metrics agree.

    deltaEOK has no chroma compression and stretches near-black lightness;
    deltaE2000 was fitted to small differences. Taking the smaller of the two
    credits a pair with k JND only if each metric independently gives k.
    """
    return min(d_ok(a, b) / JND_OK, d_00(a, b) / JND_00)


METRICS = (
    ("both metrics", jnd, 1.0),
    ("deltaEOK", d_ok, JND_OK),
    ("deltaE2000", d_00, JND_00),
)


def self_check():
    """Fail loudly if any colour formula disagrees with its published values."""

    def near(actual, expected, tolerance, label):
        if abs(actual - expected) > tolerance:
            raise SystemExit(f"self-check failed: {label}: {actual} != {expected}")

    oklab_table = (
        ((0.950, 1.000, 1.089), (1.000, 0.000, 0.000)),
        ((1.000, 0.000, 0.000), (0.450, 1.236, -0.019)),
        ((0.000, 1.000, 0.000), (0.922, -0.671, 0.263)),
        ((0.000, 0.000, 1.000), (0.153, -1.415, -0.449)),
    )
    for xyz, expected in oklab_table:
        for got, want in zip(xyz_to_oklab(xyz), expected, strict=True):
            near(got, want, 0.0006, f"Oklab of XYZ {xyz}")
    for colour in ("#ffffff", "#ff0000", "#00ff00", "#0000ff", "#301d0c", "#808080"):
        rgb = linear_rgb(colour)
        via_xyz = xyz_to_oklab(linear_rgb_to_xyz(rgb))
        for got, want in zip(linear_rgb_to_oklab(rgb), via_xyz, strict=True):
            near(got, want, 0.0005, f"Oklab sRGB path against XYZ path for {colour}")
        sample = Colour(colour)
        back = oklch_to_linear_rgb(sample.oklab[0], sample.chroma, sample.hue)
        for got, want in zip(back, rgb, strict=True):
            near(got, want, 1e-6, f"Oklab round trip for {colour}")

    sharma = (
        ((50.0, 2.6772, -79.7751), (50.0, 0.0, -82.7485), 2.0425),
        ((50.0, 3.1571, -77.2803), (50.0, 0.0, -82.7485), 2.8615),
        ((50.0, 2.8361, -74.0200), (50.0, 0.0, -82.7485), 3.4412),
        ((50.0, 0.0, 0.0), (50.0, -1.0, 2.0), 2.3669),
        ((50.0, 2.49, -0.001), (50.0, -2.49, 0.0009), 7.1792),
        ((50.0, 2.5, 0.0), (73.0, 25.0, -18.0), 27.1492),
        ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
        ((2.0776, 0.0795, -1.1350), (0.9033, -0.0636, -0.5514), 0.9082),
    )
    for lab1, lab2, expected in sharma:
        near(delta_e_2000(lab1, lab2), expected, 0.00006, f"CIEDE2000 {lab1}")
        near(delta_e_2000(lab2, lab1), expected, 0.00006, f"CIEDE2000 swap {lab1}")

    # The Oklab table and the CIEDE2000 pairs above were fetched from their
    # sources on 2026-10-09. Everything below was recalled, not re-fetched: the
    # widely published CIE Lab values of the sRGB primaries under D65, the WCAG
    # 4.54:1 of #767676 on white, and the APCA outputs. Agreement to this
    # precision is a consistency check, not a sourced verification.
    for colour, expected in (
        ("#ffffff", (100.0, 0.0, 0.0)),
        ("#ff0000", (53.2408, 80.0925, 67.2032)),
        ("#0000ff", (32.2970, 79.1875, -107.8602)),
    ):
        for got, want in zip(Colour(colour).lab, expected, strict=True):
            near(got, want, 0.02, f"CIE Lab of {colour}")

    near(wcag_contrast("#000000", "#ffffff"), 21.0, 1e-9, "WCAG black on white")
    near(wcag_contrast("#767676", "#ffffff"), 4.54, 0.005, "WCAG #767676 on white")

    for text, background, expected in (
        ("#888888", "#ffffff", 63.056469930209424),
        ("#ffffff", "#888888", -68.54146436644962),
        ("#000000", "#aaaaaa", 58.146262578561334),
        ("#aaaaaa", "#000000", -56.24113336839742),
        ("#112233", "#ddeeff", 91.66830811481631),
        ("#ddeeff", "#112233", -93.06770049484275),
    ):
        near(apca_lc(text, background), expected, 1e-6, f"APCA {text} on {background}")

    check_proposed_block_parses_on_39()


# --------------------------- palette generation ----------------------------


class Limits:
    """Which colours a palette may use."""

    def __init__(
        self,
        foreground,
        ratio,
        min_lightness,
        max_chroma_value,
        *,
        text_flip=False,
        max_lightness=1.0,
    ):
        self.foreground = foreground
        self.ratio = ratio
        self.min_lightness = min_lightness
        self.max_chroma = max_chroma_value
        self.text_flip = text_flip
        self.max_lightness = max_lightness
        self.max_luminance = (wcag_luminance(foreground) + 0.05) / ratio - 0.05
        # With text flipping, a colour is also fine when BLACK text reads on it.
        self.min_luminance_for_black = 0.05 * ratio - 0.05

    def dark_enough(self, red, green, blue):
        """Cheap luminance test on 8-bit channels, before building a Colour."""
        luminance = (
            0.2126 * LINEAR[red] + 0.7152 * LINEAR[green] + 0.0722 * LINEAR[blue]
        )
        if luminance <= self.max_luminance:
            return True
        return self.text_flip and luminance >= self.min_luminance_for_black

    def legible(self, colour):
        if wcag_contrast(self.foreground, colour.hex) >= self.ratio:
            return True
        return self.text_flip and wcag_contrast("#000000", colour.hex) >= self.ratio

    def allows(self, colour):
        return (
            self.legible(colour)
            and self.min_lightness <= colour.oklab[0] <= self.max_lightness
            and colour.chroma <= self.max_chroma
        )


def farthest_point(candidates, gap, distance=jnd):
    """Glasbey-style selection: keep adding the colour farthest from the set.

    Starts from the most colourful candidate and stops when no candidate is
    `gap` from everything chosen (JND by default). The count is a lower bound
    on how many mutually separated colours the candidate set holds.
    """
    seed = max(range(len(candidates)), key=lambda i: candidates[i].chroma)
    chosen = [candidates[seed]]
    nearest = [distance(c, chosen[0]) for c in candidates]
    while True:
        index = max(range(len(candidates)), key=nearest.__getitem__)
        if nearest[index] < gap:
            return chosen
        chosen.append(candidates[index])
        for i, candidate in enumerate(candidates):
            nearest[i] = min(nearest[i], distance(candidate, candidates[index]))


def allowed_grid(limits, grid_step=5):
    """Every colour on an sRGB grid that the limits allow."""
    candidates = []
    for red, green, blue in itertools.product(range(0, 256, grid_step), repeat=3):
        if limits.dark_enough(red, green, blue):
            colour = Colour(f"#{red:02x}{green:02x}{blue:02x}")
            if limits.allows(colour):
                candidates.append(colour)
    return candidates


def repo_bases(limits, gap):
    return farthest_point(allowed_grid(limits), gap)


class Spacing:
    """The JND gaps a palette keeps, by both metrics."""

    def __init__(self, repo_gap, step, cross_gap, step_count):
        self.repo_gap = repo_gap
        self.step = step
        self.cross_gap = cross_gap
        self.step_count = step_count


def branch_steps(base, taken, limits, spacing):
    """Colours a small step from `base`, clear of every other repo's colours.

    Each step sits between `spacing.step` and 1.3 times that many JND from the
    base, so a branch is visibly not main yet stays nearer its own repo's main
    than any colour of another repo, which is at least `spacing.cross_gap` away.
    """
    red0, green0, blue0 = hex_to_bytes(base.hex)
    shell = []
    for dr, dg, db in itertools.product(range(-30, 31, 3), repeat=3):
        red, green, blue = red0 + dr, green0 + dg, blue0 + db
        if min(red, green, blue) < 0 or max(red, green, blue) > 255:
            continue
        if not limits.dark_enough(red, green, blue):
            continue
        colour = Colour(f"#{red:02x}{green:02x}{blue:02x}")
        if not spacing.step <= jnd(base, colour) <= 1.3 * spacing.step:
            continue
        if limits.allows(colour) and all(
            jnd(colour, other) >= spacing.cross_gap for other in taken
        ):
            shell.append(colour)
    if len(shell) < spacing.step_count:
        raise SystemExit(f"only {len(shell)} branch steps available round {base.hex}")
    chosen = [max(shell, key=lambda c: c.oklab[0])]
    while len(chosen) < spacing.step_count:
        chosen.append(max(shell, key=lambda c: min(jnd(c, other) for other in chosen)))
    return chosen


def build_palette(limits, spacing):
    """Families of (base, branch steps...) for the proposed mapping."""
    bases = repo_bases(limits, spacing.repo_gap)
    families = []
    for base in bases:
        taken = [b for b in bases if b is not base]
        taken.extend(c for family in families for c in family[1:])
        families.append([base, *branch_steps(base, taken, limits, spacing)])
    return families


def ring_hues(count, lightness, chroma_cap):
    """Hues at equal deltaEOK arc length round the gamut ring at one lightness."""
    steps = 1440
    hues = [i * 360 / steps for i in range(steps)]
    points = []
    for hue in hues:
        chroma = min(max_chroma(lightness, hue), chroma_cap)
        points.append(
            (chroma * math.cos(math.radians(hue)), chroma * math.sin(math.radians(hue)))
        )
    arc = [0.0]
    for i in range(steps):
        arc.append(arc[-1] + math.dist(points[i], points[(i + 1) % steps]))
    slots = []
    for i in range(count):
        target = i * arc[-1] / count
        slots.append(hues[max(j for j in range(steps) if arc[j] <= target)])
    return slots


def build_ring_palette(hue_count, main_lightness, step_lightnesses, chroma_cap):
    """The formula-only alternative: hue is the repo, lightness is the branch."""
    return [
        [
            Colour(oklch_hex(lightness, hue, chroma_cap))
            for lightness in (main_lightness, *step_lightnesses)
        ]
        for hue in ring_hues(hue_count, main_lightness, chroma_cap)
    ]


def palette_gaps(families):
    """Smallest JND gaps inside a palette, each over every relevant pair."""
    bases = [family[0] for family in families]
    tagged = [(i, c) for i, family in enumerate(families) for c in family]
    return {
        "mains": min(jnd(a, b) for a, b in itertools.combinations(bases, 2)),
        "cross": min(
            jnd(a, b) for (i, a), (j, b) in itertools.combinations(tagged, 2) if i != j
        ),
        "step": min(jnd(family[0], c) for family in families for c in family[1:]),
        "siblings": min(
            jnd(a, b)
            for family in families
            for a, b in itertools.combinations(family[1:], 2)
        ),
    }


# ------------------------------ mappings -----------------------------------


def load_hook():
    spec = importlib.util.spec_from_file_location("branch_bg_hook", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def representative_ids(function, samples=20000):
    """One synthetic repo id per distinct main colour a mapping produces.

    Sampling ids, not hues, keeps this independent of how a mapping hashes. With
    20000 ids the chance of missing one of 360 equally likely buckets is below
    1e-21.
    """
    found = {}
    for i in range(samples):
        found.setdefault(function(f"repo-{i:05d}"), f"repo-{i:05d}")
    return list(found.values())


class Mapping:
    """One (repo, branch) to hex mapping plus the inputs that enumerate it."""

    def __init__(self, name, function, branch_names):
        self.name = name
        self.function = function
        self.branch_names = branch_names
        self._cache = {}
        self.repo_ids = representative_ids(lambda r: function(r, "main"))
        self.mains = sorted(
            (self.colour(r, "main") for r in self.repo_ids), key=lambda c: c.hue
        )

    def colour(self, repo_id, branch):
        key = (repo_id, branch)
        if key not in self._cache:
            self._cache[key] = Colour(self.function(repo_id, branch))
        return self._cache[key]

    def branches(self, repo_id):
        return [self.colour(repo_id, name) for name in self.branch_names]

    def outputs(self):
        colours = list(self.mains)
        for repo_id in self.repo_ids:
            colours.extend(self.branches(repo_id))
        return colours


# ------------------------------- metrics -----------------------------------


class SearchBudgetSpent(Exception):
    """The exact search ran out of steps before proving its answer."""


def largest_separated_subset(colours, distance, threshold, budget=200_000):
    """Size of the largest set with every pair >= threshold, and whether proven.

    A greedy walk from every starting colour gives a lower bound. A depth-first
    search then looks for anything larger. If it finishes within `budget` steps
    the size is exact; otherwise the size is a lower bound and is reported so.
    """
    colours = list({c.hex: c for c in colours}.values())
    n = len(colours)
    table = [[distance(a, b) for b in colours] for a in colours]
    best = 0
    for start in range(n):
        kept = [start]
        for offset in range(1, n):
            i = (start + offset) % n
            if all(table[i][j] >= threshold for j in kept):
                kept.append(i)
        best = max(best, len(kept))

    apart = [
        {j for j in range(n) if j != i and table[i][j] >= threshold} for i in range(n)
    ]
    steps = 0

    def extend(size, candidates):
        nonlocal best, steps
        steps += 1
        if steps > budget:
            raise SearchBudgetSpent
        best = max(best, size)
        ordered = sorted(candidates)
        for position, node in enumerate(ordered):
            if size + len(ordered) - position <= best:
                return
            extend(size + 1, set(ordered[position + 1 :]) & apart[node])

    try:
        extend(0, set(range(n)))
    except SearchBudgetSpent:
        return best, False
    return best, True


def fmt_subset(result):
    size, proven = result
    return str(size) if proven else f"at least {size}"


def expected_distinct(mains, k, threshold, rng, trials=4000):
    """Mean number of mutually distinguishable mains among k random repos."""
    table = [[jnd(a, b) for b in mains] for a in mains]
    total = 0
    for _ in range(trials):
        kept = []
        for index in (rng.randrange(len(mains)) for _ in range(k)):
            if all(table[index][other] >= threshold for other in kept):
                kept.append(index)
        total += len(kept)
    return total / trials


def branch_stats(mapping, rng):
    """How far branches sit from main, and from each other, inside one repo."""
    sample = mapping.repo_ids[:: max(1, len(mapping.repo_ids) // 36)]
    from_main, lightness_part, colour_part = [], [], []
    close = Counter()
    pairs = 0
    for repo_id in sample:
        main = mapping.colour(repo_id, "main")
        branches = mapping.branches(repo_id)
        for branch in branches:
            from_main.append(jnd(main, branch))
            d_l = abs(main.oklab[0] - branch.oklab[0])
            lightness_part.append(d_l / JND_OK)
            colour_part.append(
                math.sqrt(max(0.0, d_ok(main, branch) ** 2 - d_l**2)) / JND_OK
            )
        for _ in range(400):
            a, b = rng.sample(branches, 2)
            distance = jnd(a, b)
            pairs += 1
            for level in (1.0, 1.5):
                if distance < level:
                    close[level] += 1
    return {
        "below 1": sum(1 for v in from_main if v < 1.0) / len(from_main),
        "median": statistics.median(from_main),
        "lightness": statistics.median(lightness_part),
        "colour": statistics.median(colour_part),
        "pair below 1": close[1.0] / pairs,
        "pair below 1.5": close[1.5] / pairs,
    }


def wrong_repo_rate(mapping, rng, others=5, trials=6000):
    """Share of branch sessions whose colour is nearer another repo's main.

    A session opens on a random branch of repo A while `others` further random
    repos exist. It counts as wrong when some other repo's main colour is at
    least as close to the session colour as A's own main colour is.
    """
    wrong = 0
    for _ in range(trials):
        own = rng.choice(mapping.repo_ids)
        session = mapping.colour(own, rng.choice(mapping.branch_names))
        own_distance = jnd(session, mapping.colour(own, "main"))
        rivals = (rng.choice(mapping.repo_ids) for _ in range(others))
        if any(
            jnd(session, mapping.colour(rival, "main")) <= own_distance
            for rival in rivals
            if rival != own
        ):
            wrong += 1
    return wrong / trials


class NamingModel:
    """Heer and Stone's C3 model: response counts per 5-unit CIE Lab bin."""

    def __init__(self, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.terms = data["terms"]
        width = len(self.terms)
        flat = data["color"]
        self.bins = {
            (flat[i], flat[i + 1], flat[i + 2]): i // 3 for i in range(0, len(flat), 3)
        }
        self.counts = {}
        self._by_hex = {}
        table = data["T"]
        for i in range(0, len(table), 2):
            colour_index, term_index = divmod(table[i], width)
            self.counts.setdefault(colour_index, {})[term_index] = table[i + 1]
        # The index layout is inferred, so confirm it against unmistakable names.
        for colour, expected in (
            ("#ff0000", "red"),
            ("#00ff00", "green"),
            ("#0000ff", "blue"),
            ("#000000", "black"),
            ("#ffffff", "white"),
        ):
            got = self.modal_name(Colour(colour))
            if got != expected:
                raise SystemExit(f"C3 index check failed: {colour} named {got!r}")

    def distribution(self, colour):
        """Response counts for the colour's bin, or the nearest bin with data."""
        if colour.hex not in self._by_hex:
            key = tuple(round(v / 5) * 5 for v in colour.lab)
            index = self.bins.get(key)
            if index is None or index not in self.counts:
                index = self.bins[
                    min(
                        (b for b, i in self.bins.items() if i in self.counts),
                        key=lambda b: math.dist(b, colour.lab),
                    )
                ]
            self._by_hex[colour.hex] = self.counts[index]
        return self._by_hex[colour.hex]

    def modal_name(self, colour):
        counts = self.distribution(colour)
        return self.terms[max(counts, key=counts.get)]

    def name_distance(self, a, b):
        """1 - cosine between naming distributions (Heer and Stone, eq. 7)."""
        ca, cb = self.distribution(a), self.distribution(b)
        dot = sum(v * cb.get(k, 0) for k, v in ca.items())
        norm = math.sqrt(
            sum(v * v for v in ca.values()) * sum(v * v for v in cb.values())
        )
        return 1 - dot / norm


# ------------------------------ reporting ----------------------------------


def fmt_range(values, digits=2):
    low, high = min(values), max(values)
    if abs(high - low) < 10**-digits / 2:
        return f"{low:.{digits}f}"
    return f"{low:.{digits}f} to {high:.{digits}f}"


def table(header, rows):
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        print("| " + " | ".join(str(cell) for cell in row) + " |")
    print()


def swatch(colour):
    red, green, blue = hex_to_bytes(colour)
    dim = "\033[38;5;8mdim\033[39m"
    return f"\033[48;2;{red};{green};{blue}m {colour} text {dim} \033[0m"


def per_mapping(mappings, measure):
    return tuple(measure(m) for m in mappings)


def report_output_range(mappings, outputs, foreground):
    print("## Output range\n")

    def channels(colours):
        values = [v for c in colours for v in hex_to_bytes(c.hex)]
        return f"{min(values)} to {max(values)}"

    def lightness(colours):
        return fmt_range([c.oklab[0] for c in colours])

    rows = [
        ("possible main colours", *per_mapping(mappings, lambda m: len(m.mains))),
        (
            "distinct colours in sample",
            *per_mapping(mappings, lambda m: len({c.hex for c in outputs[m.name]})),
        ),
        (
            "sRGB channel values, mains",
            *per_mapping(mappings, lambda m: channels(m.mains)),
        ),
        (
            "sRGB channel values, all outputs",
            *per_mapping(mappings, lambda m: channels(outputs[m.name])),
        ),
        ("Oklab L, mains", *per_mapping(mappings, lambda m: lightness(m.mains))),
        (
            "Oklab L, all outputs",
            *per_mapping(mappings, lambda m: lightness(outputs[m.name])),
        ),
        (
            "Oklab chroma, mains",
            *per_mapping(mappings, lambda m: fmt_range([c.chroma for c in m.mains])),
        ),
    ]
    for text in (foreground, "#ffffff", ANSI_BRIGHT_BLACK):
        rows.append(
            (
                f"WCAG contrast, {text} text",
                *per_mapping(
                    mappings,
                    lambda m, text=text: fmt_range(
                        [wcag_contrast(text, c.hex) for c in outputs[m.name]], 1
                    ),
                ),
            )
        )
        rows.append(
            (
                f"APCA |Lc|, {text} text",
                *per_mapping(
                    mappings,
                    lambda m, text=text: fmt_range(
                        [abs(apca_lc(text, c.hex)) for c in outputs[m.name]], 0
                    ),
                ),
            )
        )
    table(("measure", "current", "proposed"), rows)


def report_palette_checks(families, limits):
    """Check every colour the proposed mapping can emit, and say what held."""
    floor = min(
        wcag_contrast(limits.foreground, c.hex) for family in families for c in family
    )
    if floor < limits.ratio:
        raise SystemExit(f"proposed palette breaks the contrast floor: {floor:.2f}")
    gaps = palette_gaps(families)
    print(
        f"Every proposed colour was checked: worst contrast {floor:.2f}:1 against "
        f"{limits.foreground}; closest two mains {gaps['mains']:.1f} JND; closest "
        f"colours of different repos {gaps['cross']:.1f} JND; nearest branch to its "
        f"main {gaps['step']:.1f} JND; closest two branches of one repo "
        f"{gaps['siblings']:.1f} JND.\n"
    )


def report_repo_colours(mappings):
    print("## Repo colours (main branch only)\n")
    rows = []
    for metric_name, distance, unit in METRICS:
        closest = [
            min(distance(a, b) for a, b in itertools.combinations(m.mains, 2)) / unit
            for m in mappings
        ]
        rows.append(
            (f"closest two mains, JND by {metric_name}", *(f"{v:.2f}" for v in closest))
        )
        for level in LEVELS:
            sizes = [
                largest_separated_subset(m.mains, distance, level * unit)
                for m in mappings
            ]
            rows.append(
                (
                    f"largest set, every pair >= {level:g} JND by {metric_name}",
                    *(fmt_subset(size) for size in sizes),
                )
            )
    table(("measure", "current", "proposed"), rows)


def report_expected_distinct(mappings, rng):
    print("## Expected distinguishable colours among k random repos (both metrics)\n")
    rows = [
        (
            k,
            *(
                f"{expected_distinct(m.mains, k, level, rng):.1f}"
                for level in (2.5, 5.0)
                for m in mappings
            ),
        )
        for k in (3, 5, 8, 12)
    ]
    header = (
        "repos",
        *(f"{m.name}, {lv:g} JND" for lv in (2.5, 5.0) for m in mappings),
    )
    table(header, rows)


def report_branches(mappings, rng):
    print("## Branches within one repo (JND by both metrics unless stated)\n")
    stats = {m.name: branch_stats(m, rng) for m in mappings}

    def share(key):
        return per_mapping(mappings, lambda m: f"{stats[m.name][key]:.0%}")

    def value(key):
        return per_mapping(mappings, lambda m: f"{stats[m.name][key]:.1f}")

    rows = [
        ("branch under 1 JND from main", *share("below 1")),
        ("median branch to main", *value("median")),
        ("median lightness part of that offset, deltaEOK JND", *value("lightness")),
        ("median hue and chroma part, deltaEOK JND", *value("colour")),
        ("two branches under 1 JND apart", *share("pair below 1")),
        ("two branches under 1.5 JND apart", *share("pair below 1.5")),
        (
            "session nearer another repo's main than its own (5 other repos)",
            *per_mapping(mappings, lambda m: f"{wrong_repo_rate(m, rng):.0%}"),
        ),
    ]
    table(("measure", "current", "proposed"), rows)


def report_names(mappings, path, limits):
    model = NamingModel(path)
    print("## Colour names (C3 model of the XKCD survey)\n")
    # Any background that meets the contrast floor, with no other limit.
    floor_only = allowed_grid(Limits(limits.foreground, limits.ratio, 0.0, 9.0))
    names = Counter(model.modal_name(c) for c in floor_only)
    counts = [
        len(farthest_point(floor_only, gap, model.name_distance)) for gap in (0.75, 0.5)
    ]
    print(
        f"Across all {len(floor_only)} grid colours that meet the floor there are "
        f"{len(names)} distinct modal names. Farthest-point selection by name "
        f"distance finds {counts[0]} colours at >= 0.75 and {counts[1]} at >= 0.5.\n"
    )
    rows = []
    for m in mappings:
        names = Counter(model.modal_name(c) for c in m.mains)
        shares = ", ".join(
            f"{n} {c / len(m.mains):.0%}" for n, c in names.most_common()
        )
        subset = largest_separated_subset(m.mains, model.name_distance, 0.5)
        rows.append((m.name, len(names), shares, fmt_subset(subset)))
    table(
        (
            "mapping",
            "distinct modal names",
            "share of mains per name",
            "largest set, name distance >= 0.5",
        ),
        rows,
    )


def trade_off_row(label, families):
    gaps = palette_gaps(families)
    repos, steps = len(families), len(families[0]) - 1
    all_differ = math.prod((repos - i) / repos for i in range(5))
    return (
        label,
        repos,
        steps,
        f"{gaps['mains']:.1f}",
        f"{gaps['cross']:.1f}",
        f"{gaps['step']:.1f}",
        f"{gaps['siblings']:.1f}",
        f"{1 - all_differ:.0%}",
        f"{1 / steps:.0%}",
    )


def report_trade_off(families, limits):
    print("## Trade-off: repo colours against branch steps (JND, both metrics)\n")
    rows = [trade_off_row("proposed default", families)]
    cap = limits.max_chroma
    for label, other_spacing, other_cap in (
        ("four branch steps", Spacing(5.0, 1.5, 2.0, 4), cap),
        ("wider repo gap", Spacing(6.0, 1.5, 2.0, 6), cap),
        ("narrower repo gap", Spacing(4.0, 1.5, 2.0, 6), cap),
        ("larger branch step", Spacing(6.0, 2.0, 2.5, 6), cap),
        ("no chroma cap", Spacing(5.0, 1.5, 2.0, 6), 9.0),
        ("chroma cap 0.10", Spacing(5.0, 1.5, 2.0, 6), 0.10),
    ):
        other = Limits(limits.foreground, limits.ratio, limits.min_lightness, other_cap)
        rows.append(trade_off_row(label, build_palette(other, other_spacing)))
    for hue_count in (8, 12):
        ring = build_ring_palette(hue_count, 0.31, (0.35, 0.27, 0.23, 0.19), cap)
        rows.append(
            trade_off_row(f"hue ring, {hue_count} hues, 4 lightness steps", ring)
        )
    table(
        (
            "palette",
            "repo colours",
            "branch steps",
            "closest two mains",
            "closest colours of different repos",
            "nearest branch to its main",
            "closest two branches of one repo",
            "5 repos: some pair identical",
            "2 branches identical",
        ),
        rows,
    )


def report_floor(limits, spacing):
    print("## Contrast floor against palette size\n")
    rows = []
    for foreground, ratio in (
        ("#d0d0d0", 9.0),
        ("#d0d0d0", 7.0),
        ("#d0d0d0", 4.5),
        ("#ffffff", 7.0),
    ):
        other = Limits(foreground, ratio, limits.min_lightness, limits.max_chroma)
        bases = repo_bases(other, spacing.repo_gap)
        lightest = max(bases, key=lambda c: wcag_luminance(c.hex))
        rows.append(
            (
                f"{ratio:g}:1 against {foreground}",
                f"{other.max_luminance:.3f}",
                f"{math.cbrt(other.max_luminance):.2f}",
                len(bases),
                len(repo_bases(other, 4.0)),
                f"{wcag_contrast(ANSI_BRIGHT_BLACK, lightest.hex):.1f}",
            )
        )
    table(
        (
            "floor",
            "max relative luminance",
            "Oklab L of the lightest grey",
            f"repo colours >= {spacing.repo_gap:g} JND",
            "repo colours >= 4 JND",
            f"{ANSI_BRIGHT_BLACK} dim text on the lightest",
        ),
        rows,
    )


def report_swatches(hook, mappings, show):
    print("## Swatches\n")
    new = mappings[1]
    repo_id, _ = hook.get_git_info()
    if repo_id is None:
        repo_id = "outside-a-repository"
    rows = [
        ("this repository", branch, *(m.function(repo_id, branch) for m in mappings))
        for branch in ("main", "feature/synthetic-alpha", "fix/synthetic-beta")
    ]
    own = new.function(repo_id, "main")
    others = [r for r in new.repo_ids if new.function(r, "main") != own][:5]
    rows.extend(
        (f"synthetic {r}", "main", *(m.function(r, "main") for m in mappings))
        for r in others
    )
    table(("repo", "branch", "current", "proposed"), rows)
    if show:
        for row in rows:
            print(f"{row[0]:>22} {row[1]:<24} {swatch(row[2])}  {swatch(row[3])}")
        print()


def report_palette(families, show):
    print("## Full proposed palette (main first, then its branch steps)\n")
    steps = len(families[0]) - 1

    def coordinates(main):
        return f"{main.oklab[0]:.2f}, {main.chroma:.2f}, {main.hue:.0f}"

    table(
        ("main", *(f"step {i + 1}" for i in range(steps)), "Oklab L, C, hue of main"),
        [(*(c.hex for c in family), coordinates(family[0])) for family in families],
    )
    if show:
        for family in families:
            print(" ".join(swatch(c.hex) for c in family))
        print()


def report_real_repos(mappings, path):
    """Real repositories from a file of git common dirs, as counts only."""
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    real = [line.strip() for line in text.splitlines() if line.strip()]
    print(f"## {len(real)} real repositories (main branch, JND by both metrics)\n")
    rows = []
    for m in mappings:
        colours = [Colour(m.function(r, "main")) for r in real]
        rows.append(
            (
                m.name,
                len({c.hex for c in colours}),
                *(
                    fmt_subset(largest_separated_subset(colours, jnd, level))
                    for level in (2.5, 5.0)
                ),
            )
        )
    table(
        ("mapping", "distinct hex", "largest set >= 2.5 JND", "largest set >= 5 JND"),
        rows,
    )


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--foreground", default="#d0d0d0")
    parser.add_argument("--ratio", type=float, default=7.0, help="WCAG contrast floor")
    parser.add_argument("--repo-gap", type=float, default=5.0, help="JND between repos")
    parser.add_argument("--branch-step", type=float, default=1.5, help="JND to main")
    parser.add_argument(
        "--cross-gap", type=float, default=2.0, help="JND to other repos"
    )
    parser.add_argument("--branch-steps", type=int, default=6)
    parser.add_argument("--min-lightness", type=float, default=0.15)
    parser.add_argument("--max-lightness", type=float, default=1.0)
    parser.add_argument("--max-chroma", type=float, default=0.16)
    parser.add_argument("--branch-samples", type=int, default=120)
    parser.add_argument("--c3-data", help="path to c3_data.json from uwdata/c3")
    parser.add_argument("--repo-ids-file", help="real git common dirs, one per line")
    parser.add_argument("--show", action="store_true", help="print ANSI swatches")
    parser.add_argument("--skip-tables", action="store_true", help="skip slow sweeps")
    parser.add_argument(
        "--text-flip",
        action="store_true",
        help="a colour is legible if black OR white text meets the ratio on it",
    )
    parser.add_argument(
        "--emit-blocks",
        metavar="PATH",
        help="write a flat farthest-point palette (no branch steps) as JSON and exit",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    self_check()
    print("Self-check passed: Oklab, CIE Lab, CIEDE2000, WCAG, APCA, 3.9 grammar.\n")

    hook = load_hook()
    # Seeded so every run prints the same simulation figures; not security.
    rng = random.Random(20261009)  # noqa: S311
    limits = Limits(
        args.foreground,
        args.ratio,
        args.min_lightness,
        args.max_chroma,
        text_flip=args.text_flip,
        max_lightness=args.max_lightness,
    )
    if args.emit_blocks:
        bases = repo_bases(limits, args.repo_gap)
        blocks = [
            {
                "hex": c.hex,
                "text": "#000000"
                if wcag_contrast("#000000", c.hex) >= wcag_contrast("#ffffff", c.hex)
                else "#ffffff",
            }
            for c in bases
        ]
        Path(args.emit_blocks).write_text(json.dumps(blocks, indent=1) + "\n")
        print(f"{len(blocks)} block colours written to {args.emit_blocks}")
        return
    spacing = Spacing(
        args.repo_gap, args.branch_step, args.cross_gap, args.branch_steps
    )
    families = build_palette(limits, spacing)
    palette = tuple(tuple(c.hex for c in family) for family in families)

    branch_names = [f"feature/sample-{i:03d}" for i in range(args.branch_samples)]
    mappings = (
        Mapping("current", hook.git_info_to_colour, branch_names),
        Mapping("proposed", lambda r, b: proposed_colour(r, b, palette), branch_names),
    )
    outputs = {m.name: m.outputs() for m in mappings}
    if {c.hex for c in outputs["proposed"]} != {
        c for family in palette for c in family
    }:
        raise SystemExit("sampling did not reach every proposed colour")

    report_output_range(mappings, outputs, args.foreground)
    report_palette_checks(families, limits)
    report_repo_colours(mappings)
    report_expected_distinct(mappings, rng)
    report_branches(mappings, rng)
    if args.c3_data:
        report_names(mappings, args.c3_data, limits)
    if not args.skip_tables:
        report_trade_off(families, limits)
        report_floor(limits, spacing)
    report_swatches(hook, mappings, args.show)
    report_palette(families, args.show)
    if args.repo_ids_file:
        report_real_repos(mappings, args.repo_ids_file)


if __name__ == "__main__":
    main()

"""Colour science for the branch-bg block palette: Oklab, CIEDE2000, WCAG, APCA.

Imported by ``palette.py`` beside it. Standard library only. The reference
values for every formula are checked by ``tests/test_branch_bg_palette.py``.

Sources for the constants:

- sRGB transfer function and primaries: IEC 61966-2-1.
- Oklab, including its linear-sRGB form: https://bottosson.github.io/posts/oklab/
- One JND is 0.02 in Oklab (deltaEOK) and 2 in CIE Lab (deltaE2000); deltaEOK
  under-estimates colourfulness differences: https://www.w3.org/TR/css-color-4/
  sections 14.2.1 and 20.4
- CIEDE2000: Sharma, Wu and Dalal (2005),
  https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/
- WCAG 2 relative luminance and contrast ratio:
  https://www.w3.org/WAI/WCAG22/Understanding/contrast-enhanced
- APCA 0.0.98G-4g constants: https://github.com/Myndex/apca-w3
"""

import math

type Triple = tuple[float, float, float]

# One just-noticeable difference, as documented by CSS Color 4 section 14.2.1.
JND_OK = 0.02
JND_00 = 2.0


def decode_channel(encoded: float) -> float:
    """Gamma-encoded sRGB channel to linear light (IEC 61966-2-1)."""
    if encoded <= 0.04045:
        return encoded / 12.92
    return ((encoded + 0.055) / 1.055) ** 2.4


# Linear light for every 8-bit channel value.
LINEAR = tuple(decode_channel(i / 255) for i in range(256))


def hex_to_bytes(colour: str) -> tuple[int, int, int]:
    """``#rrggbb`` to its three 8-bit channels."""
    value = colour.lstrip("#")
    red, green, blue = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return red, green, blue


def linear_rgb(colour: str) -> Triple:
    red, green, blue = hex_to_bytes(colour)
    return LINEAR[red], LINEAR[green], LINEAR[blue]


def xyz_to_oklab(xyz: Triple) -> Triple:
    """XYZ (D65) to Oklab through the M1 and M2 matrices of the Oklab post.

    This is Oklab's definition, the form Ottosson's reference table is given
    in; ``linear_rgb_to_oklab`` is its sRGB form, which the palette uses.
    """
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


def linear_rgb_to_oklab(rgb: Triple) -> Triple:
    """Linear sRGB to Oklab, coefficients from Ottosson's reference code."""
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


def linear_rgb_to_xyz(rgb: Triple) -> Triple:
    """Linear sRGB to CIE XYZ under D65."""
    red, green, blue = rgb
    return (
        0.4124564 * red + 0.3575761 * green + 0.1804375 * blue,
        0.2126729 * red + 0.7151522 * green + 0.0721750 * blue,
        0.0193339 * red + 0.1191920 * green + 0.9503041 * blue,
    )


def xyz_to_lab(xyz: Triple) -> Triple:
    """XYZ to CIE L*a*b* with the D65 white of sRGB."""

    def f(t: float) -> float:
        if t > (6 / 29) ** 3:
            return math.cbrt(t)
        return t / (3 * (6 / 29) ** 2) + 4 / 29

    fx, fy, fz = f(xyz[0] / 0.95047), f(xyz[1] / 1.0), f(xyz[2] / 1.08883)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e_2000(lab1: Triple, lab2: Triple) -> float:
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


def wcag_luminance(colour: str) -> float:
    red, green, blue = linear_rgb(colour)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def wcag_contrast(colour_a: str, colour_b: str) -> float:
    """WCAG 2 contrast ratio, from 1 to 21, in either order."""
    la, lb = wcag_luminance(colour_a), wcag_luminance(colour_b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def apca_lc(text: str, background: str) -> float:
    """APCA 0.0.98G-4g lightness contrast; negative for light text on dark."""

    def screen_y(colour: str) -> float:
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

    def __init__(self, colour: str) -> None:
        self.hex = colour
        rgb = linear_rgb(colour)
        self.oklab = linear_rgb_to_oklab(rgb)
        self.lab = xyz_to_lab(linear_rgb_to_xyz(rgb))

    @property
    def chroma(self) -> float:
        return math.hypot(self.oklab[1], self.oklab[2])

    @property
    def hue(self) -> float:
        return math.degrees(math.atan2(self.oklab[2], self.oklab[1])) % 360


def d_ok(a: Colour, b: Colour) -> float:
    """deltaEOK: Euclidean distance in Oklab."""
    return math.dist(a.oklab, b.oklab)


def d_00(a: Colour, b: Colour) -> float:
    """deltaE2000 between the CIE Lab coordinates."""
    return delta_e_2000(a.lab, b.lab)


def jnd(a: Colour, b: Colour) -> float:
    """Difference in JND units, counted only when both metrics agree.

    deltaEOK has no chroma compression and stretches near-black lightness;
    deltaE2000 was fitted to small differences. Taking the smaller of the two
    credits a pair with k JND only if each metric independently gives k.
    """
    return min(d_ok(a, b) / JND_OK, d_00(a, b) / JND_00)

# /// script
# requires-python = ">=3.14"
# dependencies = []
# [tool.ty.environment]
# root = ["."]  # resolve the sibling colour_science module, as uv run does
# ///
"""Generate the branch-bg block colour table and report its metrics.

The hook's ``BLOCKS`` table comes from this command, run from the repository
root:

    uv run --script plugins/denubis-hook-branch-bg/scripts/palette.py
        --text-flip --ratio 4.5 --repo-gap 5 --max-chroma 0.16
        --min-lightness 0.30 --emit-blocks blocks.json

Every run prints the palette's metrics as Markdown. ``--emit-blocks PATH`` also
writes the table as JSON, and ``--show`` adds ANSI swatches.

Candidates are an sRGB grid filtered by a WCAG contrast floor and by Oklab
lightness and chroma bounds. Farthest-point selection (Glasbey et al. 2007,
https://strathprints.strath.ac.uk/30312/) then keeps adding the candidate
farthest from those already chosen until none is ``--repo-gap`` JND clear of
them all, counting a JND only where deltaEOK and deltaE2000 agree. Each block's
label is black or white, whichever contrasts more with it. The colour science
lives beside this script in ``colour_science.py``.
"""

import argparse
import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from colour_science import (
    JND_00,
    JND_OK,
    LINEAR,
    Colour,
    apca_lc,
    d_00,
    d_ok,
    hex_to_bytes,
    jnd,
    wcag_contrast,
    wcag_luminance,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

BLACK = "#000000"
WHITE = "#ffffff"

type Block = tuple[str, str]  # (block colour, label text colour)


class Limits:
    """Which colours a palette may use."""

    def __init__(
        self,
        foreground: str,
        ratio: float,
        min_lightness: float,
        max_chroma_value: float,
        *,
        text_flip: bool = False,
        max_lightness: float = 1.0,
    ) -> None:
        self.foreground = foreground
        self.ratio = ratio
        self.min_lightness = min_lightness
        self.max_chroma = max_chroma_value
        self.text_flip = text_flip
        self.max_lightness = max_lightness
        self.max_luminance = (wcag_luminance(foreground) + 0.05) / ratio - 0.05
        # With text flipping, a colour is also fine when BLACK text reads on it.
        self.min_luminance_for_black = 0.05 * ratio - 0.05

    def dark_enough(self, red: int, green: int, blue: int) -> bool:
        """Cheap luminance test on 8-bit channels, before building a Colour."""
        luminance = (
            0.2126 * LINEAR[red] + 0.7152 * LINEAR[green] + 0.0722 * LINEAR[blue]
        )
        if luminance <= self.max_luminance:
            return True
        return self.text_flip and luminance >= self.min_luminance_for_black

    def legible(self, colour: Colour) -> bool:
        if wcag_contrast(self.foreground, colour.hex) >= self.ratio:
            return True
        return self.text_flip and wcag_contrast(BLACK, colour.hex) >= self.ratio

    def allows(self, colour: Colour) -> bool:
        return (
            self.legible(colour)
            and self.min_lightness <= colour.oklab[0] <= self.max_lightness
            and colour.chroma <= self.max_chroma
        )


def allowed_grid(limits: Limits, grid_step: int = 5) -> list[Colour]:
    """Every colour on an sRGB grid that the limits allow."""
    candidates = []
    for red, green, blue in itertools.product(range(0, 256, grid_step), repeat=3):
        if limits.dark_enough(red, green, blue):
            colour = Colour(f"#{red:02x}{green:02x}{blue:02x}")
            if limits.allows(colour):
                candidates.append(colour)
    return candidates


def farthest_point(candidates: Sequence[Colour], gap: float) -> list[Colour]:
    """Glasbey-style selection: keep adding the colour farthest from the set.

    Starts from the most colourful candidate and stops when no candidate is
    `gap` JND from everything chosen. The count is a lower bound on how many
    mutually separated colours the candidate set holds.
    """
    seed = max(range(len(candidates)), key=lambda i: candidates[i].chroma)
    chosen = [candidates[seed]]
    nearest = [jnd(c, chosen[0]) for c in candidates]
    while True:
        index = max(range(len(candidates)), key=nearest.__getitem__)
        if nearest[index] < gap:
            return chosen
        chosen.append(candidates[index])
        for i, candidate in enumerate(candidates):
            nearest[i] = min(nearest[i], jnd(candidate, candidates[index]))


def label_colour(block: str) -> str:
    """Black or white label text, whichever contrasts more with the block."""
    if wcag_contrast(BLACK, block) >= wcag_contrast(WHITE, block):
        return BLACK
    return WHITE


def generate_blocks(limits: Limits, gap: float) -> list[Block]:
    """The block table in farthest-point order, so the first N are best separated."""
    candidates = allowed_grid(limits)
    if not candidates:
        raise SystemExit("no sRGB grid colour meets these limits")
    return [(c.hex, label_colour(c.hex)) for c in farthest_point(candidates, gap)]


@dataclass(frozen=True)
class PaletteMetrics:
    """What a block table delivers, by the models in colour_science.

    Distances are in JND; ``closest_both`` counts a JND only where deltaEOK and
    deltaE2000 agree. With fewer than two blocks the distances are infinite.
    """

    blocks: int
    worst_label_contrast: float
    closest_both: float
    closest_ok: float
    closest_2000: float


def palette_metrics(blocks: Sequence[Block]) -> PaletteMetrics:
    colours = [Colour(block) for block, _ in blocks]
    pairs = list(itertools.combinations(colours, 2))
    return PaletteMetrics(
        blocks=len(blocks),
        worst_label_contrast=min(
            wcag_contrast(label, block) for block, label in blocks
        ),
        closest_both=min((jnd(a, b) for a, b in pairs), default=math.inf),
        closest_ok=min((d_ok(a, b) for a, b in pairs), default=math.inf) / JND_OK,
        closest_2000=min((d_00(a, b) for a, b in pairs), default=math.inf) / JND_00,
    )


def block_rows(blocks: Sequence[Block]) -> list[tuple[str, ...]]:
    """One table row per block, with its distance to the nearest earlier block."""
    colours = [Colour(block) for block, _ in blocks]
    rows = []
    for index, (block, label) in enumerate(blocks):
        colour = colours[index]
        earlier = min((jnd(colour, other) for other in colours[:index]), default=None)
        rows.append(
            (
                str(index + 1),
                block,
                label,
                f"{wcag_contrast(label, block):.1f}",
                f"{apca_lc(label, block):.0f}",
                f"{colour.oklab[0]:.2f}",
                f"{colour.chroma:.2f}",
                f"{colour.hue:.0f}",
                "-" if earlier is None else f"{earlier:.1f}",
            )
        )
    return rows


def swatch(block: str, label: str) -> str:
    """The block as the strip draws it: label text on the block colour."""
    background = ";".join(str(c) for c in hex_to_bytes(block))
    foreground = ";".join(str(c) for c in hex_to_bytes(label))
    return f"\033[48;2;{background}m\033[38;2;{foreground}m {block} \033[0m"


def report(blocks: Sequence[Block], *, show: bool) -> None:
    metrics = palette_metrics(blocks)
    print("## Block palette\n")
    print(
        f"{metrics.blocks} blocks. The weakest label reads at "
        f"{metrics.worst_label_contrast:.2f}:1 (WCAG 2). The closest two blocks "
        f"are {metrics.closest_both:.2f} JND apart by both metrics: "
        f"{metrics.closest_ok:.2f} by deltaEOK and {metrics.closest_2000:.2f} by "
        "deltaE2000.\n"
    )
    header = (
        "#",
        "block",
        "label",
        "WCAG",
        "APCA Lc",
        "Oklab L",
        "Oklab C",
        "hue",
        "nearest earlier block, JND",
    )
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join("---" for _ in header) + "|")
    for row in block_rows(blocks):
        print("| " + " | ".join(row) + " |")
    print()
    if show:
        print(" ".join(swatch(block, label) for block, label in blocks))
        print()


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--foreground",
        default="#d0d0d0",
        help="light text colour the contrast floor is measured against",
    )
    parser.add_argument("--ratio", type=float, default=7.0, help="WCAG contrast floor")
    parser.add_argument(
        "--repo-gap",
        type=float,
        default=5.0,
        help="JND between any two blocks, by both metrics",
    )
    parser.add_argument("--min-lightness", type=float, default=0.15, help="Oklab L")
    parser.add_argument("--max-lightness", type=float, default=1.0, help="Oklab L")
    parser.add_argument("--max-chroma", type=float, default=0.16, help="Oklab C")
    parser.add_argument(
        "--text-flip",
        action="store_true",
        help="a colour is legible if black OR the foreground meets the ratio on it",
    )
    parser.add_argument(
        "--emit-blocks", metavar="PATH", help="also write the table as JSON"
    )
    parser.add_argument("--show", action="store_true", help="print ANSI swatches")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    limits = Limits(
        args.foreground,
        args.ratio,
        args.min_lightness,
        args.max_chroma,
        text_flip=args.text_flip,
        max_lightness=args.max_lightness,
    )
    blocks = generate_blocks(limits, args.repo_gap)
    report(blocks, show=args.show)
    if args.emit_blocks:
        table = [{"hex": block, "text": label} for block, label in blocks]
        Path(args.emit_blocks).write_text(
            json.dumps(table, indent=1) + "\n", encoding="utf-8"
        )
        print(f"{len(blocks)} block colours written to {args.emit_blocks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

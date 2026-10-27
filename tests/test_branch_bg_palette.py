"""Behaviour contract for the branch-bg palette generator and its colour science.

Every expected value comes from a published source or a definition, never from
the code under test. The three reference tables were fetched and compared with
their sources on 2026-10-27:

- Oklab: the "Table of example XYZ and Oklab pairs" in
  https://bottosson.github.io/posts/oklab/ (rounded there to three decimals).
- CIEDE2000: all 34 pairs of Sharma, Wu and Dalal's test data,
  https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/dataNprograms/ciede2000testdata.txt
- APCA: `test/index.js` of https://github.com/Myndex/apca-w3 at commit
  6c5c066cf0c853507930a4239b129283b8e05353 (package 0.1.9), whose `calcAPCA`
  takes the text colour first. CSS shorthand hex is written out in full here.
"""

import importlib.util
import json
import shlex
import subprocess
from itertools import combinations, product
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "denubis-hook-branch-bg"
SCRIPTS = PLUGIN / "scripts"
HOOK = PLUGIN / "hooks" / "branch-bg.py"
CONTEXT_PAGE = (
    ROOT
    / "docs"
    / "architecture"
    / "plugins"
    / "denubis-hook-branch-bg"
    / "0-context.md"
)

# CSS Color 4 section 14.2.1: one just-noticeable difference is 0.02 in deltaEOK
# and 2 in deltaE2000. The shipped table was generated with a gap of 5 JND.
REPO_GAP_DELTA_E_OK = 5 * 0.02
REPO_GAP_DELTA_E_2000 = 5 * 2.0


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def science() -> ModuleType:
    return _load("branch_bg_colour_science", SCRIPTS / "colour_science.py")


@pytest.fixture(scope="module")
def generator() -> ModuleType:
    # The generator imports its sibling module by name, as `uv run --script`
    # allows by putting the script's directory first on sys.path.
    with pytest.MonkeyPatch.context() as patch:
        patch.syspath_prepend(str(SCRIPTS))
        return _load("branch_bg_palette", SCRIPTS / "palette.py")


@pytest.fixture(scope="module")
def hook_blocks() -> list[tuple[str, str]]:
    return list(_load("branch_bg_hook_for_palette", HOOK).BLOCKS)


# --- colour science against its published references ------------------------


@pytest.mark.parametrize(
    ("xyz", "oklab"),
    [
        ((0.950, 1.000, 1.089), (1.000, 0.000, 0.000)),
        ((1.000, 0.000, 0.000), (0.450, 1.236, -0.019)),
        ((0.000, 1.000, 0.000), (0.922, -0.671, 0.263)),
        ((0.000, 0.000, 1.000), (0.153, -1.415, -0.449)),
    ],
)
def test_oklab_matches_ottossons_reference_table(
    science: ModuleType,
    xyz: tuple[float, float, float],
    oklab: tuple[float, float, float],
) -> None:
    # The table is rounded to three decimals.
    assert science.xyz_to_oklab(xyz) == pytest.approx(oklab, abs=5e-4)


def test_colour_oklab_agrees_with_the_definition_across_srgb(
    science: ModuleType,
) -> None:
    # Colour uses Oklab's linear-sRGB form. It must agree with the XYZ
    # definition, reached through the sRGB primaries, to the table's precision.
    steps = range(0, 256, 51)
    disagreements = []
    for red, green, blue in product(steps, repeat=3):
        colour = science.Colour(f"#{red:02x}{green:02x}{blue:02x}")
        rgb = science.linear_rgb(colour.hex)
        defined = science.xyz_to_oklab(science.linear_rgb_to_xyz(rgb))
        if colour.oklab != pytest.approx(defined, abs=5e-4):
            disagreements.append((colour.hex, colour.oklab, defined))
    assert not disagreements


SHARMA_PAIRS = [
    ((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485), 2.0425),
    ((50.0000, 3.1571, -77.2803), (50.0000, 0.0000, -82.7485), 2.8615),
    ((50.0000, 2.8361, -74.0200), (50.0000, 0.0000, -82.7485), 3.4412),
    ((50.0000, -1.3802, -84.2814), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, -1.1848, -84.8006), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, -0.9009, -85.5211), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, 0.0000, 0.0000), (50.0000, -1.0000, 2.0000), 2.3669),
    ((50.0000, -1.0000, 2.0000), (50.0000, 0.0000, 0.0000), 2.3669),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0009), 7.1792),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0010), 7.1792),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0011), 7.2195),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0012), 7.2195),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0009, -2.4900), 4.8045),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0010, -2.4900), 4.8045),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0011, -2.4900), 4.7461),
    ((50.0000, 2.5000, 0.0000), (50.0000, 0.0000, -2.5000), 4.3065),
    ((50.0000, 2.5000, 0.0000), (73.0000, 25.0000, -18.0000), 27.1492),
    ((50.0000, 2.5000, 0.0000), (61.0000, -5.0000, 29.0000), 22.8977),
    ((50.0000, 2.5000, 0.0000), (56.0000, -27.0000, -3.0000), 31.9030),
    ((50.0000, 2.5000, 0.0000), (58.0000, 24.0000, 15.0000), 19.4535),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.1736, 0.5854), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.2972, 0.0000), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 1.8634, 0.5757), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.2592, 0.3350), 1.0000),
    ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
    ((63.0109, -31.0961, -5.8663), (62.8187, -29.7946, -4.0864), 1.2630),
    ((61.2901, 3.7196, -5.3901), (61.4292, 2.2480, -4.9620), 1.8731),
    ((35.0831, -44.1164, 3.7933), (35.0232, -40.0716, 1.5901), 1.8645),
    ((22.7233, 20.0904, -46.6940), (23.0331, 14.9730, -42.5619), 2.0373),
    ((36.4612, 47.8580, 18.3852), (36.2715, 50.5065, 21.2231), 1.4146),
    ((90.8027, -2.0831, 1.4410), (91.1528, -1.6435, 0.0447), 1.4441),
    ((90.9257, -0.5406, -0.9208), (88.6381, -0.8985, -0.7239), 1.5381),
    ((6.7747, -0.2908, -2.4247), (5.8714, -0.0985, -2.2286), 0.6377),
    ((2.0776, 0.0795, -1.1350), (0.9033, -0.0636, -0.5514), 0.9082),
]


@pytest.mark.parametrize(("lab1", "lab2", "expected"), SHARMA_PAIRS)
def test_ciede2000_matches_sharma_wu_dalal_pairs(
    science: ModuleType,
    lab1: tuple[float, float, float],
    lab2: tuple[float, float, float],
    expected: float,
) -> None:
    # The published differences are rounded to four decimals.
    assert science.delta_e_2000(lab1, lab2) == pytest.approx(expected, abs=5e-5)
    assert science.delta_e_2000(lab2, lab1) == pytest.approx(expected, abs=5e-5)


def test_cie_lab_places_srgb_white_and_black_at_the_reference_ends(
    science: ModuleType,
) -> None:
    # sRGB white is the D65 reference white, which CIE Lab defines as L* = 100
    # with no chroma; black is L* = 0.
    assert science.Colour("#ffffff").lab == pytest.approx((100.0, 0.0, 0.0), abs=1e-4)
    assert science.Colour("#000000").lab == pytest.approx((0.0, 0.0, 0.0), abs=1e-4)


def test_wcag_contrast_of_black_on_white_is_21_to_1(science: ModuleType) -> None:
    assert science.wcag_contrast("#000000", "#ffffff") == pytest.approx(21.0)
    assert science.wcag_contrast("#ffffff", "#000000") == pytest.approx(21.0)


@pytest.mark.parametrize(
    ("text", "background", "expected"),
    [
        ("#888888", "#ffffff", 63.056469930209424),
        ("#ffffff", "#888888", -68.54146436644962),
        ("#000000", "#aaaaaa", 58.146262578561334),
        ("#aaaaaa", "#000000", -56.24113336839742),
        ("#112233", "#ddeeff", 91.66830811481631),
        ("#ddeeff", "#112233", -93.06770049484275),
        ("#112233", "#444444", 8.32326136957393),
        ("#444444", "#112233", -7.526878460278154),
    ],
)
def test_apca_matches_the_apca_w3_reference_tests(
    science: ModuleType, text: str, background: str, expected: float
) -> None:
    assert science.apca_lc(text, background) == pytest.approx(expected, abs=1e-9)


# --- the shipped table ----------------------------------------------------------


def test_every_hook_block_label_reads_at_4_5_to_1(
    science: ModuleType, hook_blocks: list[tuple[str, str]]
) -> None:
    weak = [
        (block, label, science.wcag_contrast(label, block))
        for block, label in hook_blocks
        if science.wcag_contrast(label, block) < 4.5
    ]
    assert hook_blocks
    assert not weak


def test_every_pair_of_hook_blocks_is_the_repo_gap_apart_under_both_metrics(
    science: ModuleType, hook_blocks: list[tuple[str, str]]
) -> None:
    colours = [science.Colour(block) for block, _ in hook_blocks]
    close = [
        (a.hex, b.hex, science.d_ok(a, b), science.d_00(a, b))
        for a, b in combinations(colours, 2)
        if science.d_ok(a, b) < REPO_GAP_DELTA_E_OK
        or science.d_00(a, b) < REPO_GAP_DELTA_E_2000
    ]
    assert len(colours) > 1
    assert not close


def _documented_generator_arguments() -> list[str]:
    """Generator arguments from the architecture page's provenance claim for BLOCKS."""
    text = CONTEXT_PAGE.read_text(encoding="utf-8")
    spans = [span for span in text.split("`")[1::2] if "scripts/palette.py" in span]
    commands = [span for span in spans if "--emit-blocks" in span]
    assert len(commands) == 1, f"expected one generator command, found {commands}"
    tokens = shlex.split(commands[0])
    script = next(i for i, token in enumerate(tokens) if token.endswith("palette.py"))
    arguments = tokens[script + 1 :]
    output = arguments.index("--emit-blocks")
    del arguments[output : output + 2]
    return [tokens[script], *arguments]


def test_documented_command_regenerates_the_hook_blocks(
    tmp_path: Path, hook_blocks: list[tuple[str, str]]
) -> None:
    script, *arguments = _documented_generator_arguments()
    emitted = tmp_path / "blocks.json"
    result = subprocess.run(
        ["uv", "run", "--script", script, *arguments, "--emit-blocks", str(emitted)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    blocks = [
        (entry["hex"], entry["text"]) for entry in json.loads(emitted.read_text())
    ]
    assert blocks == hook_blocks


# --- palette metrics --------------------------------------------------------------


def test_metrics_measure_black_and_white_as_fifty_jnd_apart(
    generator: ModuleType,
) -> None:
    # Oklab puts black at L = 0 and white at L = 1; CIE Lab at L* = 0 and 100,
    # where CIEDE2000's lightness weight is 1 at their mean of 50. One JND is
    # 0.02 and 2 respectively, so both metrics give 50 JND.
    metrics = generator.palette_metrics(
        [("#000000", "#ffffff"), ("#ffffff", "#000000")]
    )
    assert metrics.blocks == 2
    assert metrics.worst_label_contrast == pytest.approx(21.0)
    assert metrics.closest_ok == pytest.approx(50.0, rel=1e-4)
    assert metrics.closest_2000 == pytest.approx(50.0, rel=1e-4)
    assert metrics.closest_both == pytest.approx(50.0, rel=1e-4)


def test_metrics_report_the_weakest_label_and_the_closest_pair(
    generator: ModuleType,
) -> None:
    blocks = [("#000000", "#ffffff"), ("#ffffff", "#ffffff"), ("#000000", "#ffffff")]
    metrics = generator.palette_metrics(blocks)
    assert metrics.worst_label_contrast == pytest.approx(1.0)
    assert metrics.closest_both == pytest.approx(0.0)

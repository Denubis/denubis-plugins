# Handover: a perceptually grounded branch-bg colour mapping

Proposal only. `plugins/denubis-hook-branch-bg/hooks/branch-bg.py` is unchanged.
Numbers come from `docs/branch-bg-colour-eval.py`, run 2026-10-09 against hook
version 0.2.6. Claims are tagged **[measured]** (script output), **[source]**, or
**[inference]**.

> **Superseded in part, 2026-10-09.** After seeing the proposed field colours live, Brian
> ruled that a repo colour works as a highlight on black, not as the field under white
> text, and asked for a four-block pane strip (person, repo, branch, session). The shipped
> design (plugin 0.3.0) therefore uses this script's `--text-flip --emit-blocks` mode: one
> flat table of 40 block colours legible under black or white text at 4.5:1, rather than
> the 11 dark families below. The diagnosis, metrics and sources here still hold.

## Result

The current mapping gives **3** repo colours that are mutually well separated; a
replacement gives **11** under the same contrast floor. The ceiling is low either
way: dark backgrounds hold roughly 7 to 8 colours people would name differently
**[measured]**. A dozen is the realistic limit.

The dispatching diagnosis is half right; two parts are refuted (section 1).

## Method

- **Units.** One just-noticeable difference (JND) is 0.02 in Oklab distance
  (deltaEOK) and 2 in deltaE2000 **[source: CSS Color 4 §14.2.1]**.
- **The two metrics disagree.** CSS Color 4 §20.4 says deltaEOK "under-estimates
  differences in colorfulness, compared to differences in lightness"
  **[source]**; Ottosson says Oklab lacks CIEDE2000's chroma compression
  **[source, summary]**. On the current mapping they answer 3 and "at least 10"
  to the same question **[measured]**. Following the repository rule for
  disagreeing sources, a pair counts as *k* JND apart only when **both** say so.
- **Thresholds.** 5 JND matches the deltaE2000 = 10 level below which
  palette optimisers penalise a pair **[source: arXiv 2407.14742, secondary]**.
  2.5 JND is my midpoint **[inference]**.
- **Names.** Heer and Stone's naming model (3.25 million XKCD responses, 153
  names) gives an independent, threshold-free count **[source]**.

## 1. Diagnosis

| Measure (both metrics unless stated) | Current | Proposed |
|---|---|---|
| Possible main colours | 216 | 11 |
| sRGB channel values, mains | 12 to 48 | 0 to 145 |
| Oklab lightness, mains | 0.18 to 0.30 | 0.15 to 0.38 |
| Oklab chroma, mains | 0.04 to 0.08 | 0.04 to 0.16 |
| WCAG contrast, `#d0d0d0` text | 6.9 to 12.8 | 7.0 to 12.9 |
| WCAG contrast, `#ffffff` text | 10.6 to 19.7 | 10.8 to 19.8 |
| APCA \|Lc\|, `#d0d0d0` text | 69 to 78 | 67 to 78 |
| WCAG contrast, `#666666` dim text | 1.8 to 3.4 | 1.9 to 3.5 |
| Closest two mains, JND | 0.04 | 5.1 |
| Largest set of mains, every pair ≥ 5 JND | 3 | 11 |
| Same, deltaEOK alone | 3 | 11 |
| Same, deltaE2000 alone | at least 10 | 11 |
| Largest set, every pair ≥ 2.5 JND | at least 8 | 11 |
| Distinct modal colour names | 5 | 7 |
| Largest set with name distance ≥ 0.5 | at least 4 | 6 |
| Distinguishable among 5 random repos, 5 JND | 1.9 | 4.2 |
| Distinguishable among 8 random repos, 5 JND | 2.0 | 5.9 |
| Distinguishable among 5 random repos, 2.5 JND | 3.1 | 4.2 |
| 178 real local repos: largest set ≥ 5 JND | 3 | 11 |
| Branch under 1 JND from its main | 20% | 0% |
| Median branch to main, JND | 1.7 | 1.9 |
| Two branches of one repo under 1 JND apart | 14% | 16% |
| Branch session nearer another repo's main than its own | 40% | 0% |

**Confirmed [measured].** Few repo colours are distinguishable: 3 at 5 JND, and
five random repos yield about 3 at 2.5 JND, matching "only 3 colours". The
current mains carry five names: dark green 27%, brown 23%, **black 19%**, navy
17%, dark purple 14%. One repo in five reads as no colour at all.

**Refuted [measured].** "±0.03 lightness offsets are invisible." The lightness
part of a branch offset has a median of 1.2 JND, and 80% of branches sit at least
1 JND from main. The real branch defect is the ±40° hue swing: it is as large as
the gap between repos, so 40% of branch sessions look more like another repo's
main than their own.

**Refuted in part [measured].** Dark RGB channels are not the limit; luminance
is. The proposal uses channel values up to 145 at the same contrast.

**Also found [measured].** Fixed HLS lightness is not fixed perceived lightness:
Oklab lightness runs 0.18 to 0.30 across hues, so contrast swings from 6.9 to
12.8, as Ottosson's critique of HSL predicts **[source]**.

## 2. Proposed mapping

**Repo picks one of 11 fixed colours; branch picks one of 6 small steps around
it; `main` and `master` get the base colour.**

- **Colour space.** Oklab for geometry, every gap also required in deltaE2000.
- **Repo colours.** Farthest-point selection over all sRGB colours inside the
  bounds, the method of Glasbey et al. **[source]**, with I Want Hue-style
  limits on lightness and chroma **[source, summary]**. It spends lightness and
  chroma on repo identity as well as hue. A hue ring alone cannot: Healey found
  seven isoluminant colours the maximum for rapid identification, and that
  same-named neighbours are confused **[source]**.
- **Bounds (defaults).** WCAG contrast ≥ 7:1 against `#d0d0d0`; Oklab lightness
  ≥ 0.15; Oklab chroma ≤ 0.16, twice today's maximum.
- **Branches.** Each step is 1.5 to 1.95 JND from its main and at least 2.1 JND
  from every colour of every other repo. A branch is visibly not main, and
  always nearer its own repo than any other.
- **Hook code.** A baked table of 77 hex strings and two hash lookups; no colour
  arithmetic, so the Python 3.9 floor is trivial. `proposed_colour` in the
  script is that function; it parses under the 3.9 grammar (best-effort check).
- **Checked exhaustively [measured].** All 77 colours: worst contrast 7.00:1;
  closest two mains 5.1 JND; closest two branches of one repo 1.2 JND.

**Stateless hashing has a cost no colour science removes.** With 11 colours, five
repos have a 66% chance that some pair is identical (birthday bound), and 178
repositories were found on this machine. Avoiding that needs state or a per-repo
override, which the no-state requirement rules out. Flagged, not reopened.

## 3. Trade-offs

Gaps are JND by both metrics.

| Palette | Repo colours | Branch steps | Closest two mains | Closest colours of different repos | Nearest branch to its main | Closest two branches of one repo | 5 repos: some pair identical | 2 branches identical |
|---|---|---|---|---|---|---|---|---|
| **Proposed default** | 11 | 6 | 5.1 | 2.1 | 1.5 | 1.2 | 66% | 17% |
| Four branch steps | 11 | 4 | 5.1 | 2.2 | 1.5 | 1.6 | 66% | 25% |
| Wider repo gap | 7 | 6 | 6.0 | 2.7 | 1.5 | 1.2 | 85% | 17% |
| Narrower repo gap | 18 | 6 | 4.0 | 2.0 | 1.5 | 0.1 | 46% | 17% |
| Larger branch step | 7 | 6 | 6.0 | 2.5 | 2.0 | 1.2 | 85% | 17% |
| No chroma cap | 13 | 6 | 5.2 | 2.1 | 1.5 | 0.5 | 58% | 17% |
| Chroma cap 0.10 | 9 | 6 | 5.2 | 2.0 | 1.5 | 1.2 | 74% | 17% |
| Hue ring, 8 hues, 4 lightness steps | 8 | 4 | 3.3 | 2.0 | 1.6 | 1.6 | 79% | 25% |
| Hue ring, 12 hues, 4 lightness steps | 12 | 4 | 2.5 | 1.6 | 1.6 | 1.6 | 62% | 25% |

More repos and bolder branches draw on the same small volume: 2 JND branch steps
cost four repo colours. The hue ring is the formula-only alternative: simpler,
and weaker.

| Contrast floor | Max relative luminance | Repo colours ≥ 5 JND | Repo colours ≥ 4 JND | `#666666` dim text on the lightest |
|---|---|---|---|---|
| 9:1 against `#d0d0d0` | 0.026 | 9 | 12 | 2.4 |
| **7:1 against `#d0d0d0`** | 0.047 | 11 | 18 | 1.9 |
| 4.5:1 against `#d0d0d0` | 0.101 | 15 | 31 | 1.2 |
| 7:1 against `#ffffff` | 0.100 | 18 | 28 | 1.2 |

## 4. Swatches

| Repo | Branch | Current | Proposed |
|---|---|---|---|
| This repository | `main` | `#301d0c` | `#41001e` |
| This repository | `feature/synthetic-alpha` | `#37140b` | `#500f2a` |
| This repository | `fix/synthetic-beta` | `#32100f` | `#4a030f` |
| Synthetic `repo-00000` | `main` | `#0c2930` | `#233291` |
| Synthetic `repo-00001` | `main` | `#302a0c` | `#194150` |
| Synthetic `repo-00002` | `main` | `#0d0c30` | `#7d0028` |
| Synthetic `repo-00004` | `main` | `#0c1730` | `#5a1478` |
| Synthetic `repo-00005` | `main` | `#300c11` | `#502841` |

Full table, main then its six branch steps:

| Main | Step 1 | Step 2 | Step 3 | Step 4 | Step 5 | Step 6 | Oklab L, C, hue |
|---|---|---|---|---|---|---|---|
| `#5a1478` | `#661a6f` | `#480872` | `#512681` | `#511d66` | `#5a0266` | `#481d72` | 0.36, 0.16, 313 |
| `#050f00` | `#171b12` | `#140900` | `#021800` | `#020f0f` | `#111209` | `#02150c` | 0.15, 0.04, 133 |
| `#503700` | `#5f310f` | `#3e3d00` | `#472e09` | `#443a1e` | `#50311e` | `#3e3400` | 0.36, 0.07, 80 |
| `#001e55` | `#152a64` | `#090f4f` | `#002446` | `#001b6a` | `#1e1e52` | `#001840` | 0.26, 0.11, 260 |
| `#41001e` | `#500f2a` | `#38030c` | `#3b002d` | `#4a030f` | `#3b1224` | `#32031e` | 0.24, 0.10, 0 |
| `#7d0028` | `#7d003d` | `#77090a` | `#6e1e31` | `#6b001f` | `#6e0934` | `#6e151f` | 0.38, 0.15, 14 |
| `#003200` | `#123e12` | `#122909` | `#00351e` | `#1e3206` | `#003b00` | `#002900` | 0.27, 0.09, 142 |
| `#194150` | `#253e62` | `#0a443e` | `#073544` | `#343b44` | `#013b59` | `#25354a` | 0.35, 0.05, 226 |
| `#140028` | `#201234` | `#1a0019` | `#0e0037` | `#0b0922` | `#200031` | `#1a0925` | 0.16, 0.08, 303 |
| `#233291` | `#382c91` | `#052c7f` | `#2c357c` | `#0b3885` | `#262682` | `#382f82` | 0.37, 0.16, 270 |
| `#502841` | `#5f2b4d` | `#412535` | `#4a2250` | `#59222c` | `#47344a` | `#59193e` | 0.34, 0.07, 343 |

To view them in the real terminal (fish):

```fish
uv run --no-project docs/branch-bg-colour-eval.py --show
```

## 5. Decisions for Brian

Defaults are mine; none is settled.

1. **Contrast floor.** Default 7:1 against `#d0d0d0`, also the current mapping's
   own worst case (6.9). Ghostty's default foreground here is `#ffffff` and the
   config sets none **[measured]**; 7:1 against white allows 18 repo colours but
   drops dim `#666666` text to 1.2:1.
2. **How far apart repos must be.** Default 5 JND, giving 11.
3. **Branch boldness.** Default six steps at 1.5 JND. Two worktrees then share a
   colour 17% of the time, about today's rate (14% under 1 JND).
4. **Vividness.** Default chroma cap 0.16. Uncapped adds two colours, including
   a pure `#0000d2` blue.
5. **Near-black.** Default lightness ≥ 0.15, which keeps one black-green and one
   black-violet repo colour.

## 6. Not verified

- **Whether Brian can see it.** No perceptual test was run. Both metrics assume
  an sRGB display; gamma, black level, ambient light, and colour-vision
  deficiency are unmeasured. Near-black steps are the likeliest to fail.
- **JND for a full-screen dark field.** The JND figures are generic. Stone,
  Szafir and Setlur report that perceived difference depends on size
  **[source, abstract only]**; their numbers were not retrieved.
- **Contrast models disagree.** WCAG calls 7:1 enhanced contrast; APCA's body
  minimum is Lc 75 **[source, summary]**, and `#d0d0d0` reaches only Lc 67 to 78
  under both mappings. With `#ffffff`, Lc is at least 97.
- **Actual text colours** drawn by Claude Code, fish, and byobu.
- **OSC 11 path.** tmux 3.7c under byobu reports `pane_bg=#300c23` for this pane,
  a hook-shaped value **[measured]**, which suggests tmux holds the colour per
  pane **[inference]**. How it reaches Ghostty 1.3.1, and other terminals, was
  not tested. No OSC 11 was sent.
- **Naming model.** Collected on white backgrounds with uncalibrated monitors.
- **Optimality.** Farthest-point selection is greedy; counts are lower bounds.
- **Read only in summary.** Colorgorical and I Want Hue; Berlin and Kay only
  through Heer and Stone.
- **Reference values.** Oklab and CIEDE2000 test values were fetched. CIE Lab,
  WCAG, and APCA values were recalled; the code reproduces all of them.
- **Not done.** No hook edit, tests, or version bump. Implementing this touches
  the plugin manifests, `CHANGELOG.md`, and the plugin's architecture page.

## Reproduce

```fish
uv run --no-project docs/branch-bg-colour-eval.py
```

Self-checks run first; output is identical across runs. `--c3-data` adds the
name rows; `--repo-ids-file` adds the real-repo row, as counts only.

## Sources

- CSS Color 4, §14.2.1 and §20: <https://www.w3.org/TR/css-color-4/>
- Ottosson, Oklab: <https://bottosson.github.io/posts/oklab/>
- Ottosson on HSL: <https://bottosson.github.io/posts/colorpicker/>
- Ottosson on chroma compression: <https://lists.w3.org/Archives/Public/public-css-archive/2024Mar/0390.html>
- CIEDE2000 test data: <https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/>
- Healey 1996: <https://www.cs.ubc.ca/sites/default/files/tr/1996/TR-96-10_0.pdf>
- Heer and Stone 2012: <https://idl.uw.edu/papers/color-naming-models>
- C3 naming data: <https://github.com/uwdata/c3>
- Glasbey et al. 2007: <https://strathprints.strath.ac.uk/30312/>
- Colorgorical: <https://schlosslab.discovery.wisc.edu/portfolio/color-preference>
- I Want Hue, via `hues`: <https://search.r-project.org/CRAN/refmans/hues/html/hues.html>
- Palette threshold: <https://arxiv.org/pdf/2407.14742>
- Stone, Szafir and Setlur 2014: <https://www.tableau.com/research/publications/engineering-model-color-difference-function-size>
- WCAG 2 contrast: <https://w3c.github.io/wcag/understanding/contrast-enhanced>
- APCA: <https://github.com/Myndex/apca-w3>, <https://github.com/Myndex/apca-introduction>

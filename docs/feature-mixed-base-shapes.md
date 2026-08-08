# Feature: Mixed base shapes in one tray

## Goal

Allow each base in a tray to have its own cutout shape, instead of one
global `--cutout-shape` for the whole tray. Motivating use case: a tray
with one oval base and the rest circles, e.g.

```bash
python tray_generator.py oval:60x35 24.7 24.7 24.7 24.7
```

Full flexibility is wanted: any mix of `circle`, `square`, `hex`, and
`oval` (and any future shape registered in `Trays/functions/shapes.py`)
in a single tray.

## Current state (read these files first)

- `Trays/functions/shapes.py` — shape registry. Each `CutoutShape`
  already exposes everything the layouts need per base:
  `layout_sizes(size, tolerance)` (per-axis bounding sizes), `nesting`
  (`'circle'` for exact tangency, `'box'` for conservative bounding-box
  spacing), `size_format` (`'scalar'` vs `'pair'`), `validate_size`,
  and `build(size, **params)`. All four `build()` implementations take
  the identical kwarg set, so mixing shapes in the build loop is
  already safe.
- `Trays/functions/full_tray_generator.py` — the orchestrator. This is
  the main coupling point: `generate_full_tray` calls
  `get_shape(config.cutout_shape)` **once** and uses that single shape
  object for validation, `layout_sizes`, `nesting`, and every
  `build()` call.
- `Trays/functions/calculate_cutout_positions/calculate_linear_cutout_positions.py`
  — already fully per-base via the `layout_sizes` list. Needs no
  spacing-math changes, only the `index` addition described below.
- `Trays/functions/calculate_cutout_positions/calculate_alternating_cutout_positions.py`
  — per-base via `layout_sizes`, **except** that `nesting` is a single
  string applied to every neighboring pair. This is the one real
  geometry change.
- `Trays/tray_generator.py` — CLI. Sizes are positional tokens parsed
  by `shapes.parse_size` (`31.6` → scalar, `60x35` → pair); the shape
  comes from `--cutout-shape`.
- Tests live in `tests/` (`test_shapes.py`, `test_linear_positions.py`,
  `test_alternating_positions.py`, `test_full_tray_helpers.py`,
  `test_cutout_generator.py`). They run without the CAD libraries;
  keep `shapes.py` importable without build123d (lazy imports inside
  `build()`), and note `full_tray_generator` imports build123d at
  module level, so pure-layout tests should target the
  `calculate_cutout_positions` modules and `shapes.py` directly, as
  the existing tests do.

## CLI design

Extend each positional size token with an optional shape prefix:

```
[shape:]size
```

- `24.7` — no prefix, uses the default shape (`--cutout-shape`, which
  keeps its current default of `circle`). Fully backward compatible.
- `oval:60x35` — an oval base 60 mm wide, 35 mm deep.
- `square:31.6`, `hex:25.4`, `circle:24.7` — explicit prefixes.

Examples:

```bash
# One oval, four circles (the motivating case)
python tray_generator.py oval:60x35 24.7 24.7 24.7 24.7

# Default shape square, with one hex thrown in
python tray_generator.py --cutout-shape square 31.6 hex:25.4 31.6
```

Rules:

- Unknown prefix → error listing valid shapes (reuse the message from
  `shapes.get_shape`).
- Size-format mismatch (e.g. `oval:31.6` or `circle:60x35`) → the
  existing `validate_size` error, raised per token at parse time so
  the user sees which token is wrong (wrap it as
  `argparse.ArgumentTypeError` like the current `size_argument` does).
- A bare `60x35` with a scalar default shape is a mismatch error (this
  matches current behavior, where pair sizes require
  `--cutout-shape oval`).

Implementation: add `parse_base(token, )` to `shapes.py` (alongside
`parse_size`) returning `(shape_name_or_None, size)` — `None` meaning
"use the tray default". Splitting rule: if the token contains a `:`,
the part before the first `:` is the shape name; the remainder goes
through the existing `parse_size`. Keep `parse_size` unchanged for
callers that want just a size.

## Data model

Thread a per-base shape list through the stack, parallel to `sizes`
(same pattern as `edge_offsets` / `edge_adjusts`):

```python
def generate_full_tray(sizes, config=None, edge_offsets=None,
                       edge_adjusts=None, shapes=None):
```

- `shapes` is an optional list of shape-name strings (or `None`
  entries), padded with `config.cutout_shape` to match `len(sizes)`.
  Omitting it entirely reproduces today's behavior exactly.
- Resolve once at the top: `base_shapes = [get_shape(name) for name in
  padded_names]`, then `base_shapes[i].validate_size(sizes[i])` per
  base.
- `config.cutout_shape` stays and becomes "the default shape for bases
  without an explicit one". No `TrayConfig` changes are required.

## Orchestrator changes (`full_tray_generator.py`)

1. `layout_sizes` — compute with each base's own shape:
   `[base_shapes[i].layout_sizes(sizes[i], config.tolerance) for i in
   range(len(sizes))]`. The linear/alternating selection in
   `calculate_cutout_positions` (the `max_y_size` check) already works
   off `layout_sizes` and needs no change.
2. `nesting` — pass a per-base list `[s.nesting for s in base_shapes]`
   instead of the single `shape.nesting` (see next section).
3. Build loop — call `base_shapes[position['index']].build(...)` per
   position (see the `index` section below for why the position, not
   the loop counter, must supply the base index).

## Alternating layout: per-pair nesting

In `calculate_alternating_cutout_positions.py`, `nesting` becomes a
per-base list (keep accepting a single string for convenience by
broadcasting it, so existing tests/callers still work).

The rule for any pair of bases (i, j): **use circle tangency math only
when both bases have `nesting == 'circle'`; otherwise use the
bounding-box math (`_box_min_dx` / the per-axis `x_gap`/`y_gap`
check).** Box math is conservative and correct for any footprint, so a
circle paired with an oval is safely spaced by bounding boxes.

Three places branch on `nesting` today; each becomes a per-pair check:

- `_calculate_initial_positions` — the consecutive-pair offset
  (`if nesting == 'circle'` at ~line 96) checks
  `nesting[i-1] == nesting[i] == 'circle'`.
- `_redistribution_pass.calculate_dx(i, ...)` — same check for the
  pair (i, i+1).
- `_validate_positions` — the all-pairs overlap check uses circle math
  only when both `nesting[i]` and `nesting[j]` are `'circle'`.

Note: an all-circle tray must produce **bit-identical positions** to
today (the broadcast list is all-`'circle'`, so every pair takes the
circle branch). Likewise all-box trays. Add a regression test for
this.

Optional refinement, explicitly out of scope for the first cut: exact
circle–ellipse and ellipse–ellipse tangency spacing (packs a mixed
oval/circle tray tighter than bounding boxes). The
`CutoutShape.min_center_distance` hook in `shapes.py` was designed as
the seam for this — a follow-up could route the pair spacing through
it — but bounding-box spacing is correct and sufficient now.

## Positions must carry the original base index

Add `'index': <original position in the sizes list>` to every position
dict produced by **both** layout modules (`calculate_linear_cutout_positions.py`
already tracks it internally as `line_one_indices`/`line_two_indices`;
the alternating layout's position order equals input order, so it's
just `i`).

Then in the `generate_full_tray` build loop, use
`idx = position['index']` for `base_shapes[idx]`, `edge_adjusts[idx]`,
and `edge_offsets[idx]` instead of the enumerate counter.

This is required for mixed shapes (the linear layout reorders bases
into two rows, so position order ≠ input order) **and it fixes a
latent bug**: today `full_tray_generator.py:148-149` indexes
`edge_adjusts`/`edge_offsets` by position order, so on a reordered
double-row linear layout, per-base edge adjustments can be applied to
the wrong base. (The layout modules themselves apply `edge_offsets` by
original index, correctly — the mismatch is only in the build loop.)
Add a regression test: a double-tray linear layout with distinct
edge_offsets, asserting each position's offset matches its original
base.

## Output filename

`tray_generator.py` builds the filename from a `Counter` of sizes.
Count `(shape_name, size)` pairs instead, and prefix the shape name
when it differs from the tray's default shape, e.g.

```
tray_1xoval60x35mm_4x24.7mm
```

(An all-default tray keeps producing exactly today's filenames.) Sort
key must handle mixed tuple/scalar sizes as the current code does —
sort by `(shape_name, size_key)`.

## Error handling

- The "math domain error" hint and the layout `ValueError`s in
  `tray_generator.py` stay as-is; the per-pair box fallback means
  mixed pairs can't hit the circle-only `_side_from_hyp` failure
  unless both are circles (message already suggests
  `--force-linear-positions`).
- Per-token parse/validation errors should name the offending token.

## Tests (all runnable without build123d)

1. **Parsing**: `parse_base` round-trips `24.7`, `oval:60x35`,
   `square:31.6`; rejects `bogus:31.6`, `oval:31.6`, `circle:60x35`,
   `oval:60x35x2`.
2. **Backward compat**: all-circle alternating layout with the
   broadcast nesting list produces positions identical to passing
   `nesting='circle'` today (and same for all-box).
3. **Mixed alternating**: one oval among circles — every adjacent pair
   involving the oval is spaced by box math, circle–circle pairs by
   tangency; `_validate_positions` passes; all positions inside the
   usable area.
4. **Mixed linear**: force-linear with an oval and circles; assert
   `index` keys map each position back to its input base.
5. **Edge-offset regression**: double-tray linear layout with distinct
   per-base edge_offsets — build-loop inputs (via `index`) match the
   original bases.
6. **Validation**: per-base `validate_size` fires for a pair size on a
   scalar shape at position N with a message naming that base.
7. **Filename**: mixed-shape summary produces the documented pattern;
   all-default trays produce unchanged filenames.

If a full end-to-end check is wanted and build123d is available,
generate the motivating tray (`oval:60x35 24.7 24.7 24.7 24.7`) and
assert it exports without error — but keep it optional/marked so the
suite still runs without CAD libs.

## Non-goals

- Per-base `taper_angle`, `tolerance`, or `flap_clearance` (stay
  global in `TrayConfig`).
- Rotated shapes (ovals rotate by swapping WIDTHxDEPTH, as today).
- Exact ellipse tangency packing (see optional refinement above).
- Changes to the cutout builders in `cutout_generator.py` — none are
  needed; they already share one kwarg interface.

## Acceptance criteria

- `python tray_generator.py oval:60x35 24.7 24.7 24.7 24.7` generates
  and exports a tray with one oval and four circle cutouts.
- Existing invocations (no prefixes, with or without
  `--cutout-shape`) produce byte-identical layouts to before.
- `pytest` passes, including the new tests above.

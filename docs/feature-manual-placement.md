# Feature: Manual base placement

> **Status: Phase 1 implemented** (manual x + edge choice, layout
> files, `--layout` / `--export-layout` / `--validate-only`). Phase 2
> (free y) remains open. Two findings from implementation adjusted the
> plan:
>
> 1. **Opposite-edge pairs need the linear layout's row rule, not the
>    strict 0.4mm gap.** The standard double tray runs opposing rows as
>    close as ~0.1mm nominal by design, so a strict all-pairs
>    `MIN_EDGE_GAP` check rejects layouts the linear auto-layout itself
>    produces — exported trays would fail re-import. The shared
>    validator (`calculate_cutout_positions/validate_positions.py`)
>    therefore accepts an opposite-edge pair when the normal
>    nesting-aware check passes **or** the row rule allows it
>    (nominally deep enough for both, or clear along x). The automatic
>    layouts keep the historical strict behavior.
> 2. **Exported `x` keeps full float precision** (no rounding), so an
>    unedited export regenerates the tray byte-identically.
>
> The pure-math entry point ended up as
> `functions/layout_engine.py::compute_layout` (which also absorbed
> `calculate_usable_area` and the auto-layout dispatch from
> `full_tray_generator`, keeping re-exports there). See the README's
> "Building a UI on top" section for the UI-facing API.

## Goal

Allow the user to place each base on the tray explicitly instead of
relying on the automatic linear/alternating layouts. The motivating use
case is a UI where the user drags cases around a tray canvas and the
generator produces exactly that arrangement — but the generator itself
must support explicit placement first, via a layout file and a public
API, so any UI (or a hand-edited file) can drive it.

```bash
# Auto-layout once, dump the computed placement, tweak it, regenerate
python Trays/tray_generator.py 24.7 24.7 31.6 --export-layout my_tray.json
python Trays/tray_generator.py --layout my_tray.json
```

## Feasibility summary

**Feasible, and most of the plumbing already exists.** The layout
modules and the orchestrator communicate through a plain list of
position dicts:

```python
{'x': float, 'y': float, 'size': ..., 'index': int, 'flipped': bool}
```

`generate_full_tray` (`Trays/functions/full_tray_generator.py`) consumes
that list without caring how it was produced. Manual placement is
therefore "a third layout source" next to
`calculate_linear_cutout_positions` and
`calculate_alternating_cutout_positions`.

The one real architectural constraint: **the cutout builders assume
every base rests against the front or back tray edge.** In
`Trays/functions/cutout_generator.py`:

- Every builder computes its slide-path length from
  `flap_depth - edge_margin` — the distance from the cutout's front
  edge to the flap gap line **when the cutout front sits exactly at
  `safety_margin[1]` from the tray edge**. Move the base inward and
  that distance is wrong.
- The circular cutout's revolved lip/hinge relief
  (`hinge_radius = hinge_diameter/2 - edge_margin`) models the flap's
  swept arc under the same resting assumption.
- Back-edge bases are handled by the `flipped` 180° rotation, not by a
  free y coordinate.

There is also a physical constraint behind that code: the flap is what
retains a base, and the slide path is what lets it in and out. A base
placed so it never reaches under a flap is not just unsupported by the
code — it is a tray that cannot hold or release that base.

So the feature splits naturally into two phases:

- **Phase 1 — manual x + edge choice.** The user places each base
  anywhere along its row and picks which edge (front/back) it rests
  on. y stays derived exactly as the auto layouts derive it (resting
  edge + `edge_offset`). **Zero cutout-geometry changes**; this is
  pure plumbing and validation, and it already covers the bulk of the
  UI value: reordering, asymmetric spacing, grouping, choosing rows.
- **Phase 2 — free y.** Generalize the builders' edge-resting
  assumption to an explicit per-base edge distance, plus retention
  validation. Real geometry work with print-testing risk; scoped but
  deferred.

## Current state (read these files first)

- `Trays/functions/full_tray_generator.py` — orchestrator.
  `calculate_cutout_positions` picks linear vs alternating; the build
  loop consumes position dicts and looks up per-base inputs via
  `position['index']`. Manual placement plugs in at exactly this seam.
- `Trays/functions/calculate_cutout_positions/calculate_linear_cutout_positions.py`
  — shows how y is derived from the resting edge:
  `usable_area['min']['y'] + layout_sizes[idx][1]/2 + edge_offset`
  (mirrored with `flipped=True` for the back row). Manual Phase 1
  computes y the same way.
- `Trays/functions/calculate_cutout_positions/calculate_alternating_cutout_positions.py`
  — contains `_validate_positions`: bounds checking plus all-pairs
  overlap with per-pair nesting math (`circle` tangency vs `box`).
  This is exactly the validation a manual layout needs; extract and
  share it rather than duplicating.
- `Trays/functions/cutout_generator.py` — the edge-resting assumption
  described above (slide paths, circle lip relief). Phase 2 only.
- `Trays/functions/shapes.py` — per-shape `layout_sizes`, `footprint`,
  `nesting`, `parse_base`. Importable without build123d — important,
  because a UI backend wants to validate placements without the CAD
  stack (see "What a UI needs" below).
- `Trays/tray_generator.py` — CLI. Gains `--layout`,
  `--export-layout`, and `--validate-only`.
- `tests/` — layout tests run without build123d; keep every new
  layout/parsing module CAD-free the same way.

## Layout file format

JSON is the interchange format between a UI and the generator (and the
`--export-layout` output, so auto → edit → regenerate round-trips).

```json
{
  "version": 1,
  "tray": {
    "width": 189.5,
    "depth": 66.0,
    "double_sided": true
  },
  "defaults": { "shape": "circle" },
  "bases": [
    { "shape": "oval", "size": [60, 35], "x": -45.0, "edge": "front" },
    { "size": 24.7, "x": 10.0, "edge": "front", "edge_offset": 0.5 },
    { "size": 24.7, "x": 40.0, "edge": "back", "edge_adjust": 0.2 }
  ]
}
```

- Coordinates are tray-centered millimeters: origin at the tray
  center, x positive to the right, y positive toward the back. `x` is
  the cutout center. This matches the internal position dicts, so no
  coordinate translation layer is needed.
- `edge` is `"front"` or `"back"` (`"back"` invalid on single-sided
  trays). It replaces the layouts' internal `flipped` flag in
  user-facing form.
- `size` follows the existing conventions: scalar for circle/square/hex,
  `[width, depth]` pair for oval. `shape` omitted → `defaults.shape`
  (→ `circle`).
- `edge_offset` / `edge_adjust` are the existing per-base fine-tuning
  knobs, now attached to the base they belong to instead of positional
  parallel lists — a usability win by itself.
- Phase 2 adds an optional `y` per base. In Phase 1, a `y` key is an
  error with a clear "free y placement is not yet supported" message,
  so files stay forward-compatible.
- `tray` settings are defaults; explicit CLI flags (`--width`,
  `--depth`, `--single-sided`, `--tolerance`, ...) override them.
  Global settings not in the file keep their `TrayConfig` defaults.

`--export-layout FILE` runs the normal auto layout and writes the
computed placement in this same schema (translating `flipped` →
`edge`). That gives users and UIs a correct starting point to nudge,
instead of authoring coordinates from scratch.

## Phase 1 implementation plan

### 1. Manual layout module

New file
`Trays/functions/calculate_cutout_positions/calculate_manual_cutout_positions.py`:

```python
def calculate_manual_cutout_positions(
    usable_area, sizes, placements, edge_offsets, tolerance,
    is_double_tray, layout_sizes=None, nesting='box'):
```

- `placements` is a per-base list of `{'x': float, 'edge': 'front'|'back'}`.
- y is computed exactly as the linear layout does:
  front → `usable_area['min']['y'] + layout_sizes[i][1]/2 + edge_offsets[i]`,
  back → mirrored with `flipped=True`.
- Position order is input order, so `'index': i`.
- Ends by calling the shared validator (next item). No packing, no
  redistribution — the user's x is authoritative.

### 2. Extract the shared validator

Move `_validate_positions` (plus its constants `EDGE_TOLERANCE`,
`MIN_EDGE_GAP`, and helpers `_pair_nests_as_circles`, `_box_min_dx`'s
overlap counterpart) from `calculate_alternating_cutout_positions.py`
into a sibling module, e.g.
`calculate_cutout_positions/validate_positions.py`. The alternating
layout imports it back — behavior must stay bit-identical (existing
alternating tests are the regression net).

Manual placement needs one addition the alternating layout never
needed: error messages that **name the offending base** ("Base 3
(24.7mm circle at x=40.0) overlaps Base 2 ..."), because with manual
input the user must know *which* placement to fix, and a UI wants to
highlight it. Keep the generic wording for auto layouts; add an
optional flag or message-builder parameter for the per-base detail.

Front/back row collision: the all-pairs box/circle overlap check
already covers two deep bases meeting in the middle (that is how the
alternating layout self-checks), so no extra
`_validate_row_overlap`-style pass is needed.

### 3. Orchestrator seam

`generate_full_tray` gains an optional `placements=None` parameter
(same style as `shapes`/`edge_offsets`). When given:

- Skip `calculate_cutout_positions` and call the manual module.
- Everything downstream is untouched — the build loop already handles
  `flipped` rotation, per-index `edge_offsets`/`edge_adjusts`, and
  per-base shapes.

`calculate_cutout_positions` itself stays as the auto-only dispatcher;
manual is selected one level up so the auto heuristics
(`force_linear_positions`, the `max_y_size` check) never interact with
manual input.

### 4. CLI

- `--layout FILE` — mutually exclusive with positional sizes (error if
  both given, pointing at whichever to drop). Parses the JSON, applies
  `tray`/`defaults`, and produces `sizes`, `shapes`, `edge_offsets`,
  `edge_adjusts`, `placements` for `generate_full_tray`.
- `--export-layout FILE` — with positional sizes: run the auto layout,
  write the schema above, and continue to generation as normal (or
  combine with `--validate-only` to skip generation).
- `--validate-only` — parse and validate (layout math only, no
  build123d geometry), print the result, exit nonzero on failure. This
  is the cheap check a UI calls on every drag-drop; it must not import
  the CAD stack (see next item).
- Layout parsing (`load_layout` / `save_layout`) lives in a new
  CAD-free module, e.g. `Trays/functions/layout_io.py`, not inside
  `tray_generator.py` (which imports build123d at module level) — so
  tests and UI backends can import it standalone.
- Output filename: a `--layout` run without `--output` uses the same
  `format_base_summary` naming as today (placement does not change
  which bases are in the tray). Nice-to-have: `_manual` suffix.

### 5. Errors

All manual-placement failures are `ValueError`s with actionable,
base-naming messages (the CLI already prints `ValueError`s verbatim):

- out of usable area (report the base and the violated bound, and the
  usable-area rectangle so the user knows the legal range),
- overlap between two named bases,
- `back` edge on a single-sided tray,
- `y` key present (Phase 1),
- malformed file: unknown keys, missing `x`, bad shape/size (reuse
  `get_shape` / `validate_size` messages, prefixed with the base's
  position in the list).

## What a UI needs from this project (and gets from Phase 1)

- **Interchange format**: the layout JSON, in both directions
  (`--export-layout` out, `--layout` in).
- **Cheap validation**: `--validate-only`, or direct import of the
  CAD-free modules (`shapes.py`, `layout_io.py`,
  `calculate_cutout_positions/*`) for in-process checking. No
  build123d needed until the final generate.
- **Geometry facts to render a canvas**: `calculate_usable_area` for
  the placeable rectangle, `shape.footprint(size, tolerance)` for each
  base's outline box, `shape.nesting` for how close pairs may sit.
  These all exist; the plan adds no UI code to this repo, just keeps
  these importable without CAD libraries.

## Phase 2: free y placement (scoped, deferred)

Allow an explicit `y` per base (still center coordinates), with the
base no longer resting on an edge.

1. **Generalize the builders.** Add an `edge_distance` kwarg (distance
   from the resting tray edge to the cutout's front bounding edge,
   default `edge_margin` — today's behavior) to all four builders in
   `cutout_generator.py`. Slide-path lengths replace `edge_margin`
   with it, e.g. the prismatic
   `slide_path_length = half_depth - flap_depth - flap_center_gap + edge_distance`,
   and the circle's `size/2 > flap_depth - edge_margin` guard and
   extrude length likewise. With the default value, output must be
   **bit-identical** to today (regression test on exported STL bytes
   or position/volume checks).
2. **Circle lip relief.** The revolved relief's
   `hinge_radius = hinge_diameter/2 - edge_margin` models the flap
   sweeping over the cutout lip; with the base moved inward the swept
   arc intersects the cutout differently. This is the riskiest part —
   needs derivation against the flap/hinge geometry in
   `base_tray_generator.py` and a physical test print. Budget it as
   its own task.
3. **Retention validation.** A base is held (and insertable) only if
   its cutout reaches under a flap: front bounding edge within
   `flap_depth` of its resting tray edge. Violations are an error by
   default with an explicit `--allow-loose-bases` override (there are
   legitimate display-only trays).
4. **Keep-out zones.** Free y opens placements the auto layouts could
   never produce, so validation must add the hinge pockets (hinge
   boxes sit at the flap ends, `hinge_depth` = 17.5 mm deep from the
   center-section edge) and the flap-center gap line as keep-out
   rectangles. Phase 1 cannot hit these (edge-resting bases stay
   inside the same envelope the auto layouts use); mid-tray bases can.
5. **`edge` becomes optional** when `y` is given (inferred from sign),
   and `edge_offset` is rejected alongside `y` (it is the edge-resting
   fine-tune; `y` supersedes it).

Out of scope even for Phase 2: rotated shapes (ovals still rotate only
by swapping WIDTHxDEPTH), bases straddling the centerline of a double
tray.

## Tests (Phase 1, all runnable without build123d)

1. **Manual layout math**: given x/edge placements, positions carry
   the right derived y, `index`, `flipped`; `edge_offset` moves the
   base inward on both edges (same convention as linear).
2. **Validator extraction regression**: alternating layouts produce
   bit-identical positions and identical error behavior after the
   `_validate_positions` move (run existing alternating tests against
   the new import path).
3. **Overlap detection**: two manually placed bases overlapping →
   error naming both bases; circle–circle pairs judged by tangency,
   any pair involving a box shape by bounding boxes (reuse the mixed
   nesting cases from `test_mixed_shapes.py` as placement inputs).
4. **Bounds**: a base past the usable-area edge → error naming the
   base; `back` on single-sided → error.
5. **Layout IO round-trip**: `save_layout(load_layout(f))` is
   idempotent; unknown keys, missing `x`, bad sizes, and a `y` key all
   produce the documented errors; `defaults.shape` and per-base
   `shape` interact like the CLI prefix rules.
6. **Export**: auto layout → `--export-layout` → `--layout` reproduces
   the same positions exactly (the round-trip that makes the UI flow
   trustworthy).
7. **CLI wiring**: `--layout` + positional sizes → error;
   `--validate-only` exits 0/nonzero appropriately.

Optional CAD end-to-end (marked, like the existing ones): generate a
small manual tray and assert export succeeds.

## Acceptance criteria (Phase 1)

- `--export-layout` on an existing auto-layout invocation, followed by
  `--layout` on the unmodified file, exports an identical tray.
- Editing an x value or swapping `front`/`back` in the file changes
  the generated tray accordingly.
- Invalid placements (overlap, out of bounds, back-on-single-sided)
  fail with messages naming the offending base, and `--validate-only`
  reports them without the CAD stack loaded.
- All existing invocations and their outputs are unchanged; `pytest`
  passes, including the new tests.

#!/usr/bin/env python3

"""Assemble UMAP plots into gamma-grouped summary grids.

The script scans experiment result folders for run logs, extracts the recorded
gamma and pose dimensions, and builds one grid per plot type:

- embedding_UMAP.png
- embedding_UMAPpose.png

Each output grid groups rows by gamma and columns by pose dimension so the
effect of changing pose dimensionality is visible within a fixed gamma.
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


LOG_GAMMA_RE = re.compile(r"^Parameter gamma set to value: (?P<value>.+)$", re.MULTILINE)
LOG_POSE_RE = re.compile(r"^Parameter pose_dims set to value: (?P<value>.+)$", re.MULTILINE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build gamma-grouped UMAP summary grids from experiment results."
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=Path("results"),
        help="Root directory that contains the results_* run folders.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to write the summary images to. Defaults to <repo-root>/compiled_UMAP_figures.",
    )
    parser.add_argument(
        "--plot-names",
        nargs="+",
        default=["embedding_UMAP.png", "embedding_UMAPpose.png"],
        help="Plot filenames to assemble into summary grids.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search for logs recursively under the results root instead of only one level deep.",
    )
    return parser.parse_args()


def find_log_files(results_root: Path, recursive: bool) -> List[Path]:
    if recursive:
        return sorted(results_root.rglob("*.log"))
    return sorted(results_root.glob("results_*/logs/*.log"))


def read_run_metadata(log_path: Path) -> Optional[Tuple[str, str]]:
    text = log_path.read_text(errors="ignore")
    gamma_match = LOG_GAMMA_RE.search(text)
    pose_match = LOG_POSE_RE.search(text)
    if not gamma_match or not pose_match:
        return None
    return gamma_match.group("value").strip(), pose_match.group("value").strip()


def format_gamma_label(value: str) -> str:
    try:
        return f"gamma={float(value):g}"
    except ValueError:
        return f"gamma={value}"


def format_pose_label(value: str) -> str:
    try:
        return f"pose={int(float(value))}"
    except ValueError:
        return f"pose={value}"


def discover_runs(results_root: Path, recursive: bool) -> Tuple[Dict[str, Dict[str, Dict[str, Path]]], List[str], List[str]]:
    runs: Dict[str, Dict[str, Dict[str, Path]]] = defaultdict(dict)
    gamma_values = set()
    pose_values = set()

    for log_path in find_log_files(results_root, recursive):
        metadata = read_run_metadata(log_path)
        if metadata is None:
            continue

        gamma_value, pose_value = metadata
        gamma_values.add(gamma_value)
        pose_values.add(pose_value)

        run_dir = log_path.parent.parent
        plots_dir = run_dir / "plots"
        for plot_name in ("embedding_UMAP.png", "embedding_UMAPpose.png"):
            plot_path = plots_dir / plot_name
            if plot_path.exists():
                runs.setdefault(plot_name, {}).setdefault(gamma_value, {})[pose_value] = plot_path

    sorted_gamma_values = sorted(gamma_values, key=lambda item: float(item))
    sorted_pose_values = sorted(pose_values, key=lambda item: float(item))
    return runs, sorted_gamma_values, sorted_pose_values


def make_grid_image(
    plot_name: str,
    plot_runs: Dict[str, Dict[str, Path]],
    gamma_values: Iterable[str],
    pose_values: Iterable[str],
    output_path: Path,
) -> None:
    gamma_values = list(gamma_values)
    pose_values = list(pose_values)

    if not gamma_values or not pose_values:
        return

    header_font = ImageFont.load_default()
    body_font = ImageFont.load_default()

    cell_size = 320
    label_col_width = 180
    label_row_height = 80
    padding = 18
    gap = 14

    nrows = len(gamma_values) + 1
    ncols = len(pose_values) + 1
    canvas_width = label_col_width + ncols * cell_size + (ncols + 1) * gap
    canvas_height = label_row_height + nrows * cell_size + (nrows + 1) * gap + 48
    canvas = Image.new("RGB", (canvas_width, canvas_height), "white")
    draw = ImageDraw.Draw(canvas)

    title_text = f"{plot_name} grouped by gamma"
    title_width, title_height = draw.textsize(title_text, font=header_font)
    draw.text(
        ((canvas_width - title_width) // 2, 12),
        title_text,
        fill="black",
        font=header_font,
    )

    def cell_xy(row_index: int, col_index: int) -> Tuple[int, int, int, int]:
        x0 = label_col_width + gap + (col_index - 1) * (cell_size + gap) if col_index > 0 else gap
        y0 = label_row_height + 48 + gap + (row_index - 1) * (cell_size + gap) if row_index > 0 else gap + 48
        if row_index == 0 and col_index > 0:
            y0 = 48 + gap
        if col_index == 0 and row_index > 0:
            x0 = gap
        return x0, y0, x0 + (label_col_width if col_index == 0 else cell_size), y0 + (label_row_height if row_index == 0 else cell_size)

    for col_index, pose_value in enumerate(pose_values, start=1):
        x0, y0, x1, y1 = cell_xy(0, col_index)
        label = format_pose_label(pose_value)
        label_width, label_height = draw.textsize(label, font=body_font)
        draw.text(((x0 + x1 - label_width) // 2, (y0 + y1 - label_height) // 2), label, fill="black", font=body_font)

    for row_index, gamma_value in enumerate(gamma_values, start=1):
        x0, y0, x1, y1 = cell_xy(row_index, 0)
        label = format_gamma_label(gamma_value)
        label_width, label_height = draw.textsize(label, font=body_font)
        label_image = Image.new("RGB", (label_width + 20, label_height + 20), "white")
        label_draw = ImageDraw.Draw(label_image)
        label_draw.text((10, 10), label, fill="black", font=body_font)
        rotated = label_image.rotate(90, expand=True)
        paste_x = x0 + (x1 - x0 - rotated.size[0]) // 2
        paste_y = y0 + (y1 - y0 - rotated.size[1]) // 2
        canvas.paste(rotated, (paste_x, paste_y))

    for row_index, gamma_value in enumerate(gamma_values, start=1):
        for col_index, pose_value in enumerate(pose_values, start=1):
            x0, y0, x1, y1 = cell_xy(row_index, col_index)
            image_path = plot_runs.get(gamma_value, {}).get(pose_value)
            draw.rectangle([x0, y0, x1, y1], outline="black", width=1)

            if image_path is None:
                missing_text = "missing"
                missing_width, missing_height = draw.textsize(missing_text, font=body_font)
                draw.text(
                    (x0 + (x1 - x0 - missing_width) // 2, y0 + (y1 - y0 - missing_height) // 2),
                    missing_text,
                    fill="gray",
                    font=body_font,
                )
                continue

            image = Image.open(str(image_path)).convert("RGB")
            image.thumbnail((cell_size - padding * 2, cell_size - padding * 2), Image.ANTIALIAS)
            paste_x = x0 + (x1 - x0 - image.size[0]) // 2
            paste_y = y0 + (y1 - y0 - image.size[1]) // 2
            canvas.paste(image, (paste_x, paste_y))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(str(output_path))


def main() -> int:
    args = parse_args()
    results_root = args.results_root.resolve()
    output_dir = args.output_dir.resolve() if args.output_dir is not None else results_root.parent / "compiled_UMAP_figures"

    runs, gamma_values, pose_values = discover_runs(results_root, args.recursive)
    if not runs:
        raise SystemExit(f"No run logs with gamma and pose metadata were found under {results_root}")

    for plot_name in args.plot_names:
        if plot_name not in runs:
            continue
        output_path = output_dir / f"{Path(plot_name).stem}_by_gamma.png"
        make_grid_image(plot_name, runs[plot_name], gamma_values, pose_values, output_path)
        print(f"Wrote {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
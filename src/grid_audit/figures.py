"""Step 3 figures: each a PNG in results/figures/ with a CSV of the data it plots."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # files only, no display

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

FIGURES_DIR = Path("results/figures")
# Reference palette of the dataviz method, light surface.
SURFACE, INK, INK_2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
BLUE, ORANGE = "#2a78d6", "#eb6834"  # categorical slots 1 and 2
BLUES = LinearSegmentedColormap.from_list(
    "blues", ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]
)
Y_LIMIT = 10.0  # Figure 4's y range, percentage points
# Label positions to try, in points from the marker, nearest first.
LABEL_OFFSETS = [(6, 5), (6, -7), (-6, 5), (-6, -7), (10, 16), (10, -18), (-10, 16), (-10, -18)]
LABEL_OFFSETS += [(14, 28), (14, -30), (-14, 28), (-14, -30), (24, 0), (-24, 0)]
STYLE = {
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 9,
    "text.color": INK,
    "axes.labelcolor": INK_2,
    "axes.edgecolor": AXIS,
    "axes.linewidth": 0.8,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelcolor": INK_2,
    "ytick.labelcolor": INK_2,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "grid.linestyle": "-",
    "legend.frameon": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
}


def save(fig: plt.Figure, data: pd.DataFrame, name: str) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / f"{name}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    data.to_csv(FIGURES_DIR / f"{name}.csv", float_format="%.4f")


def q1_dot_plot(
    final: pd.DataFrame, median: float, national: float, top: list[str], year: int
) -> None:
    """MAPE per BA (sorted, best at the top) with the naive MAPE as a second marker, and lines
    for the median across BAs and the national figure. Log scale: MAPEs span two orders of
    magnitude."""
    data = final[["mape", "naive_mape", "skill"]].sort_values("mape", ascending=False)
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(7.5, 0.19 * len(data) + 1.6))
        y = range(len(data))
        ax.hlines(
            y,
            data[["mape", "naive_mape"]].min(axis=1),
            data[["mape", "naive_mape"]].max(axis=1),
            color=GRID,
            linewidth=1.5,
            zorder=1,
        )
        ax.scatter(
            data["naive_mape"],
            y,
            s=30,
            color=ORANGE,
            edgecolor=SURFACE,
            linewidth=1.2,
            zorder=3,
            label="Naive forecast (demand 24 h earlier)",
        )
        ax.scatter(
            data["mape"],
            y,
            s=36,
            color=BLUE,
            edgecolor=SURFACE,
            linewidth=1.2,
            zorder=4,
            label="Published day-ahead forecast",
        )
        ax.axvline(median, color=INK_2, linewidth=1, zorder=2)
        ax.axvline(national, color=MUTED, linewidth=1, zorder=2)
        # The two lines can nearly coincide: label the higher one above the plot to its right and
        # the lower one at the bottom to its left.
        lines = [("median", median, INK_2), ("national", national, MUTED)]
        (high, high_x, high_color), (low, low_x, low_color) = sorted(
            lines, key=lambda line: line[1], reverse=True
        )
        ax.text(high_x, len(data) - 0.2, f" {high} {high_x:.2f}%", color=high_color, va="bottom")
        ax.text(low_x, -1.0, f"{low} {low_x:.2f}% ", color=low_color, va="center", ha="right")
        ax.set_yticks(list(y), data.index)
        for label in ax.get_yticklabels():
            if label.get_text() in top:
                label.set_fontweight("bold")
                label.set_color(INK)
        ax.set_xscale("log")
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
        ax.grid(axis="x", which="major")
        ax.set_ylim(-1.7, len(data) + 0.6)
        ax.set_xlabel("MAPE (log scale)")
        ax.set_title(f"Day-ahead forecast MAPE by BA, {year}", pad=24)
        ax.legend(
            loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, handletextpad=0.2, borderaxespad=0.2
        )
        ax.tick_params(axis="y", length=0)
        save(fig, data, f"q1_mape_{year}")


def q2_lines(panel: pd.DataFrame, by_year: pd.DataFrame) -> None:
    """Yearly MAPE per panel BA (thin), the median across BAs (bold) and the national figure
    (dashed). Log scale."""
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(7.5, 4.8))
        for ba in panel.index:
            ax.plot(panel.columns, panel.loc[ba], color=AXIS, linewidth=0.7, zorder=1)
        ax.plot([], [], color=AXIS, linewidth=0.7, label=f"Each panel BA ({len(panel)})")
        ax.plot(
            by_year.index,
            by_year["median_mape"],
            color=BLUE,
            linewidth=2.5,
            zorder=3,
            solid_capstyle="round",
            label="Median across BAs (MAPE)",
        )
        ax.plot(
            by_year.index,
            by_year["national"],
            color=INK,
            linewidth=2,
            linestyle="--",
            zorder=3,
            label="National (Σ|e| / Σ demand)",
        )
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
        ax.grid(axis="y", which="major")
        ax.set_xticks(list(panel.columns))
        ax.set_ylabel("Error (log scale)")
        ax.set_title("Yearly day-ahead forecast error, BAs eligible every year 2016–2025", pad=24)
        ax.legend(
            loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, handlelength=2.2, borderaxespad=0.2
        )
        data = panel.copy()
        data.loc["Median across BAs"] = by_year["median_mape"]
        data.loc["National"] = by_year["national"]
        save(fig, data, "q2_mape_by_year")


def national_by_year(lines: pd.DataFrame, caption: str) -> None:
    """Headline: the panel's national figure (Σ|e| / Σ demand) per year, one line per column of
    `lines` (years as the index), coloured in column order. Linear scale from 0, so the change
    reads against the level; each line is labelled at its last year."""
    colors = [BLUE, ORANGE]
    if len(lines.columns) > len(colors):
        raise ValueError(f"at most {len(colors)} lines, got {len(lines.columns)}")
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(7.5, 4.6))
        for name, color in zip(lines.columns, colors, strict=False):
            ax.plot(
                lines.index,
                lines[name],
                color=color,
                linewidth=2,
                solid_capstyle="round",
                solid_joinstyle="round",
                marker="o",
                markersize=5,
                markeredgecolor=SURFACE,
                markeredgewidth=1.5,
                zorder=3,
                label=name,
            )
            last = lines.index[-1]
            ax.annotate(
                f"{name} {lines.loc[last, name]:.2f}%",
                (last, lines.loc[last, name]),
                xytext=(8, 0),
                textcoords="offset points",
                color=INK_2,
                va="center",
            )
        ax.set_ylim(0, 1.15 * lines.max().max())
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
        ax.grid(axis="y", which="major")
        ax.set_axisbelow(True)
        ax.set_xticks(list(lines.index))
        ax.set_ylabel("National error, Σ|e| / Σ demand")
        # Top down: title, caption, legend, then the plot.
        title = "National day-ahead forecast error by year, as published and corrected"
        ax.set_title(title, pad=58)
        ax.text(0, 1.09, caption, transform=ax.transAxes, color=INK_2, va="bottom")
        ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, borderaxespad=0.2)
        save(fig, lines, "national_by_year")


def q3_heatmap(grid: pd.DataFrame) -> None:
    """Median MAPE across BAs by season (rows) and local hour ending (columns)."""
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(9, 2.8))
        image = ax.imshow(grid.to_numpy(dtype=float), cmap=BLUES, aspect="auto")
        ax.set_xticks(range(grid.shape[1]), [str(h) for h in grid.columns])
        ax.set_yticks(range(grid.shape[0]), [str(s) for s in grid.index])
        ax.tick_params(length=0)
        for side in ("left", "bottom"):
            ax.spines[side].set_visible(False)
        ax.set_xlabel("Local hour ending")
        ax.set_title("Median MAPE across BAs by season and hour, 2016–2025", pad=10)
        bar = fig.colorbar(image, ax=ax, fraction=0.03, pad=0.02)
        bar.outline.set_visible(False)
        bar.ax.tick_params(length=0)
        bar.set_label("MAPE (%)", color=INK_2)
        save(fig, grid, "q3_season_hour")


def q4_scatter(
    points: pd.DataFrame, top: list[str], rho: float, p: float, base_year: int, year: int
) -> None:
    """Demand change (x) against MAPE change (y), one point per BA, the 10 largest labelled.
    Points beyond ±Y_LIMIT sit at the edge as triangles with their value, so a few broken series
    do not flatten the rest."""
    x, y = 100 * points["x"], points["y"]
    inside = y.abs() <= Y_LIMIT
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(7.5, 5.2))
        ax.axhline(0, color=AXIS, linewidth=0.8, zorder=1)
        ax.axvline(0, color=AXIS, linewidth=0.8, zorder=1)
        ax.scatter(
            x[inside], y[inside], s=36, color=BLUE, edgecolor=SURFACE, linewidth=1.2, zorder=3
        )
        edge = Y_LIMIT + 0.6
        labels = {ba: (x[ba], y[ba]) for ba in points.index.intersection(top)}
        markers = list(zip(x[inside], y[inside], strict=True))
        for ba in points.index[~inside]:
            at = edge if y[ba] > 0 else -edge
            ax.scatter(
                x[ba],
                at,
                s=44,
                marker="^" if y[ba] > 0 else "v",
                color=BLUE,
                edgecolor=SURFACE,
                linewidth=1.2,
                zorder=3,
            )
            labels[f"{ba} {y[ba]:+.1f} pp"] = (x[ba], at)
            markers.append((x[ba], at))
        ax.set_ylim(-edge - 1.6, edge + 1.6)
        ax.grid(which="major")
        ax.set_axisbelow(True)
        ax.set_xlabel(f"Mean demand change, {base_year} to {year} (%)")
        ax.set_ylabel(f"MAPE change, {base_year} to {year} (percentage points)")
        ax.set_title(f"Demand growth and forecast error change, {len(points)} BAs", pad=34)
        beyond = int((~inside).sum())
        off_scale = f"; {beyond} beyond ±{Y_LIMIT:g} pp sit at the edge" if beyond else ""
        ax.text(
            0,
            1.015,
            f"Spearman ρ = {rho:.3f}, permutation p = {p:.2f}. The 10 largest BAs "
            f"are labelled{off_scale}.",
            transform=ax.transAxes,
            color=INK_2,
        )
        place_labels(fig, ax, labels, markers)
        save(fig, points, "q4_growth_vs_error")


def place_labels(
    fig: plt.Figure,
    ax: plt.Axes,
    labels: dict[str, tuple[float, float]],
    markers: list[tuple[float, float]],
) -> None:
    """Label points without covering other labels or markers: try offsets nearest first; a
    label set further out gets a hairline leader to its point."""
    ax.set_xlim(ax.get_xlim())
    renderer = fig.canvas.get_renderer()
    centres = [tuple(ax.transData.transform(m)) for m in markers]
    placed: list = []
    for name, xy in sorted(labels.items(), key=lambda item: item[1]):
        for dx, dy in LABEL_OFFSETS:
            far = abs(dy) > 12 or abs(dx) > 8
            label = ax.annotate(
                name,
                xy,
                xytext=(dx, dy),
                textcoords="offset points",
                fontsize=8,
                color=INK_2,
                ha="left" if dx > 0 else "right",
                va="center",
                arrowprops={"arrowstyle": "-", "color": AXIS, "linewidth": 0.6} if far else None,
            )
            box = label.get_window_extent(renderer).expanded(1.1, 1.3)
            clear = not any(box.overlaps(other) for other in placed)
            if clear and not any(box.contains(cx, cy) for cx, cy in centres):
                placed.append(box)
                break
            label.remove()
        else:  # nowhere clear: keep the nearest position
            dx, dy = LABEL_OFFSETS[0]
            ax.annotate(
                name,
                xy,
                xytext=(dx, dy),
                textcoords="offset points",
                fontsize=8,
                color=INK_2,
                va="center",
            )

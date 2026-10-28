"""Step 3 statistics: Theil–Sen slope, Mann–Kendall test, Spearman correlation with a permutation
p-value. Pure functions on numpy (no scipy)."""

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

PERMUTATIONS = 10_000
PERMUTATION_SEED = 0
TOLERANCE = 1e-12  # a permuted |rho| this close to the observed one counts as at least as large


def theil_sen_slope(x: ArrayLike, y: ArrayLike) -> float:
    """Median of the slopes (y_j − y_i) / (x_j − x_i) over all pairs with x_i ≠ x_j."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    i, j = np.triu_indices(len(x), k=1)
    dx = x[j] - x[i]
    keep = dx != 0
    return float(np.median((y[j] - y[i])[keep] / dx[keep]))


@dataclass(frozen=True)
class MannKendall:
    s: int  # Σ sign(y_j − y_i) over pairs in x order; positive: rising
    variance: float
    z: float
    p: float  # two-sided


def mann_kendall(x: ArrayLike, y: ArrayLike) -> MannKendall:
    """Two-sided Mann–Kendall trend test of `y` in the order of `x`: the variance of S has the
    tie correction, z the continuity correction, and p comes from the normal distribution."""
    y = np.asarray(y, dtype=float)[np.argsort(np.asarray(x), kind="stable")]
    n = len(y)
    i, j = np.triu_indices(n, k=1)
    s = int(np.sign(y[j] - y[i]).sum())
    _, ties = np.unique(y, return_counts=True)
    variance = float(n * (n - 1) * (2 * n + 5) - np.sum(ties * (ties - 1) * (2 * ties + 5))) / 18
    z = (s - np.sign(s)) / math.sqrt(variance) if variance > 0 else 0.0
    return MannKendall(s, variance, float(z), math.erfc(abs(z) / math.sqrt(2)))


def ranks(values: ArrayLike) -> np.ndarray:
    """Ranks 1..n; tied values share their average rank."""
    _, inverse, counts = np.unique(np.asarray(values), return_inverse=True, return_counts=True)
    last = np.cumsum(counts)
    return (last - (counts - 1) / 2)[inverse]


def pearson(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Pearson correlation of `x` with `y`, or with each row of `y` when it is 2-D."""
    dx = x - x.mean()
    dy = y - y.mean(axis=-1, keepdims=True)
    return (dy @ dx) / np.sqrt((dx @ dx) * (dy * dy).sum(axis=-1))


def spearman(x: ArrayLike, y: ArrayLike) -> float:
    """Spearman's rank correlation (Pearson correlation of the ranks)."""
    return float(pearson(ranks(x), ranks(y)))


def permutation_p(
    x: ArrayLike, y: ArrayLike, permutations: int = PERMUTATIONS, seed: int = PERMUTATION_SEED
) -> float:
    """Two-sided permutation p-value for Spearman's rho: (b + 1) / (permutations + 1), where b
    counts random reorderings of `y` whose |rho| is at least the observed |rho|."""
    rx, ry = ranks(x), ranks(y)
    observed = abs(float(pearson(rx, ry)))
    rng = np.random.default_rng(seed)
    shuffled = rng.permuted(np.tile(ry, (permutations, 1)), axis=1)
    hits = int((np.abs(pearson(rx, shuffled)) >= observed - TOLERANCE).sum())
    return (hits + 1) / (permutations + 1)

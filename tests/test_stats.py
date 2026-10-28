import numpy as np
import pytest

from grid_audit.stats import mann_kendall, permutation_p, ranks, spearman, theil_sen_slope


def test_theil_sen_slope() -> None:
    # Pair slopes of (1,1), (2,3), (3,2), (4,5): 2, 0.5, 4/3, -1, 1, 3. Sorted: -1, 0.5, 1, 4/3,
    # 2, 3; median (1 + 4/3) / 2 = 7/6.
    assert theil_sen_slope([1, 2, 3, 4], [1, 3, 2, 5]) == pytest.approx(7 / 6)
    # Gaps in x (missing years) count: (2016, 1), (2018, 3), (2019, 4) -> slopes 1, 1.5, 1;
    # median 1.
    assert theil_sen_slope([2016, 2018, 2019], [1, 3, 4]) == pytest.approx(1.0)


def test_mann_kendall_no_ties() -> None:
    # y = 1, 3, 2, 5: of the 6 pairs only (3, 2) falls, so S = 5 - 1 = 4. Var = 4 x 3 x 13 / 18
    # = 8.667. z = (4 - 1) / sqrt(8.667) = 1.0190; p = 2 (1 - Phi(1.0190)) = 0.3082.
    result = mann_kendall([1, 2, 3, 4], [1, 3, 2, 5])
    assert result.s == 4
    assert result.variance == pytest.approx(156 / 18)
    assert result.z == pytest.approx(1.0190, abs=1e-4)
    assert result.p == pytest.approx(0.3082, abs=1e-4)
    # The order comes from x, not from the input order.
    assert mann_kendall([4, 3, 2, 1], [5, 2, 3, 1]).s == 4


def test_mann_kendall_ties_and_falling() -> None:
    # y = 3, 2, 2, 1: five falling pairs, one tie: S = -5. Tie group of 2 removes
    # 2 x 1 x 9 = 18: Var = (156 - 18) / 18 = 7.667. z = (-5 + 1) / sqrt(7.667) = -1.4446;
    # p = 0.1486.
    result = mann_kendall([1, 2, 3, 4], [3, 2, 2, 1])
    assert result.s == -5
    assert result.variance == pytest.approx(138 / 18)
    assert result.z == pytest.approx(-1.4446, abs=1e-4)
    assert result.p == pytest.approx(0.1486, abs=1e-4)


def test_mann_kendall_significant_rise() -> None:
    # 10 strictly rising values: S = 45, Var = 10 x 9 x 25 / 18 = 125, z = 44 / sqrt(125) =
    # 3.9355, p = 8.3e-5.
    result = mann_kendall(range(10), range(10))
    assert result.s == 45 and result.variance == pytest.approx(125)
    assert result.z == pytest.approx(3.9355, abs=1e-4)
    assert result.p == pytest.approx(8.3e-5, abs=1e-6)


def test_ranks_average_ties() -> None:
    assert ranks([30, 10, 20, 20]).tolist() == [4.0, 1.0, 2.5, 2.5]


def test_spearman() -> None:
    # Ranks of y: 1, 3, 2, 4; d = 0, -1, 1, 0; rho = 1 - 6 x 2 / (4 x 15) = 0.8.
    assert spearman([1, 2, 3, 4], [1, 3, 2, 5]) == pytest.approx(0.8)
    assert spearman([1, 2, 3], [9, 5, 1]) == pytest.approx(-1.0)


def test_permutation_p() -> None:
    # Two points: every ordering gives |rho| = 1, so p = (10,000 + 1) / (10,000 + 1) = 1.
    assert permutation_p([1, 2], [5, 7]) == 1.0
    # Four points in the same order: 2 of the 24 orderings reach |rho| = 1, exact p = 1/12 =
    # 0.0833. 10,000 draws estimate it within about 3 x 0.0028.
    p = permutation_p([1, 2, 3, 4], [1, 2, 3, 4])
    assert p == pytest.approx(1 / 12, abs=0.01)
    # A fixed seed gives the same value every run.
    assert permutation_p([1, 2, 3, 4], [1, 2, 3, 4]) == p
    assert np.isclose(permutation_p([1, 2, 3, 4], [4, 3, 2, 1]), p)

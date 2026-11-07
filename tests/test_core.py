import numpy as np

from src.common import Grid, minmax, training_grid
from src.risk.priority import jaccard, priority_index, priority_sd, top_mask


def test_training_grid_matches_worldclim():
    g = training_grid()
    assert g.shape == (216, 624)
    # edges are integer multiples of the 2.5' WorldClim resolution from -180/90
    assert abs(((g.lon_min + 180) / g.res) - round((g.lon_min + 180) / g.res)) < 1e-9
    assert abs(((90 - g.lat_max) / g.res) - round((90 - g.lat_max) / g.res)) < 1e-9


def test_cell_index_corners():
    g = Grid(0, 2, 0, 1, 0.5)
    row, col, inside = g.cell_index([0.01, 1.99, 2.5], [0.99, 0.01, 0.5])
    assert inside.tolist() == [True, True, False]
    assert (row[0], col[0]) == (0, 0)
    assert (row[1], col[1]) == (1, 3)


def test_priority_index_formula():
    suit = np.array([[[1.0, 0.5]], [[0.0, 0.5]]])  # 2 species, 1x2 grid
    pressure = np.array([[0.5, 1.0]])
    protected = np.array([[0, 1]])
    p = priority_index(suit, pressure, protected)
    assert np.allclose(p, [[0.5, 0.0]])  # protected cell contributes nothing
    w = priority_index(suit, pressure, np.zeros((1, 2)), weights=[2, 1])
    assert np.allclose(w, [[1.0, 1.5]])


def test_priority_sd_propagation():
    sd = np.array([[[0.3]], [[0.4]]])
    out = priority_sd(sd, np.array([[1.0]]), np.array([[0.0]]))
    assert np.allclose(out, 0.5)  # sqrt(0.09 + 0.16)
    assert np.allclose(priority_sd(sd, np.array([[1.0]]), np.array([[1.0]])), 0)


def test_top_mask_and_jaccard():
    v = np.arange(100, dtype=float).reshape(10, 10)
    m = np.ones_like(v, dtype=bool)
    t = top_mask(v, m, 0.05)
    assert t.sum() == 5 and t[9, 9]
    assert jaccard(t, t) == 1.0
    assert jaccard(t, ~t) == 0.0


def test_minmax_range():
    a = np.array([[2.0, 4.0, np.nan]])
    out = minmax(a)
    assert np.nanmin(out) == 0 and np.nanmax(out) == 1

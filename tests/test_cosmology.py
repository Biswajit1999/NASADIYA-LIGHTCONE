import numpy as np

from nasadiya_lightcone.cosmology import spherical_to_cartesian


def test_spherical_coordinate_axes():
    x, y, z = spherical_to_cartesian(
        np.array([0.0, 90.0, 0.0]), np.array([0.0, 0.0, 90.0]), np.array([10.0, 10.0, 10.0])
    )
    assert np.allclose(x, [10.0, 0.0, 0.0], atol=1e-8)
    assert np.allclose(y, [0.0, 10.0, 0.0], atol=1e-8)
    assert np.allclose(z, [0.0, 0.0, 10.0], atol=1e-8)

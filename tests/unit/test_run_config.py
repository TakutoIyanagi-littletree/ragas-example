from typing import Protocol
import sys, importlib

import pytest
from numpy.random import default_rng, Generator

from ragas.run_config import RunConfig

class RandomComparison(Protocol):
    """Pytest fixture wrapper to check :py:cls:`numpy.random.Generator` object equivalence.
    
    Args:
        rng_0 (numpy.random.Generator) : The first generator to compare with.
        rng_1 (numpy.random.Generator) : The second generator to compare with.
    
    Returns:
        bool: Whether the two generators are at the same state.

    """
    def __call__(self, a:Generator, b:Generator) -> bool: ...

@pytest.fixture(scope="function")
def compare_rng() -> RandomComparison:
    def _compare_rng(rng_0:Generator, rng_1:Generator) -> bool:
        return rng_0.random() == rng_1.random()
    
    return _compare_rng


@pytest.mark.parametrize(
    "seed, expected_equivalence",
    (
        [42, True],
        [None, False],
    )
)
def test_random_num_generator(seed, compare_rng:RandomComparison, expected_equivalence):
    """Check :py:mod:`numpy.random` functionality and seed behaviour control."""
    rc = RunConfig(seed=seed)

    # Check type
    assert isinstance(rc.rng, Generator)

    # Check generated value
    rng = default_rng(seed=seed)
    assert compare_rng(rc.rng, rng) == expected_equivalence

    # Check generation consistency
    importlib.reload(sys.modules['numpy.random'])
    new_rc = RunConfig(seed=seed)
    new_rng = default_rng(seed=seed)

    # Put generator into the same state
    new_rc.rng.random()
    new_rng.random()

    # Check equivalence
    if expected_equivalence:
        assert all(
             list(
                  map(
                       compare_rng,
                       [rc.rng, new_rc.rng],
                       [new_rng, rng]
                    )
                )
            )
    else:
        assert all(
             list(
                  map(
                       lambda x, y:not compare_rng(x, y),
                       [rc.rng, new_rc.rng],
                       [new_rng, rng]
                    )
                )
            )

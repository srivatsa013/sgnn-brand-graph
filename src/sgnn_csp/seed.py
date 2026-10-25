"""Seed policy. Every stochastic step names the seed key it uses."""

from __future__ import annotations

import random


def set_global_seed(seed: int) -> None:
    """Seed the libraries that are installed. Missing ML libraries are skipped."""
    random.seed(seed)
    try:
        import numpy as np
    except ImportError:
        np = None
    if np is not None:
        np.random.seed(seed)
    try:
        import torch
    except ImportError:
        torch = None
    if torch is not None:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

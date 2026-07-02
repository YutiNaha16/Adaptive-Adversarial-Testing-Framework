import random

import numpy


def seed_everything(seed: int) -> None:
    random.seed(seed)
    numpy.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
    except ImportError:
        pass

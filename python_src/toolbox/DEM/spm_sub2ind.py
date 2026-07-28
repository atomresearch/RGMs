"""
Linear index from multiple subscripts (MATLAB ``spm_sub2ind`` / ``sub2ind``).

Translated from ``spm_sub2ind.m`` (Pass 1 faithful transliteration). Used by
the drone process-model handle ``spm_fg`` (projective geometry) to map
``(x,y,z)`` place subscripts to a linear latent-state index.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def spm_sub2ind(siz: Any, *subs: Any) -> Any:
    """FORMAT ndx = spm_sub2ind(siz, v1, v2, ...) — 1-based, MATLAB semantics.

    ``subs`` are the subscript arrays ``v1, v2, ...`` (scalars or arrays).
    Returns ``double`` linear indices, matching MATLAB ``sub2ind`` order.
    """
    siz = np.asarray(siz, dtype=np.float64).reshape(-1)
    lensiz = int(siz.size)

    numOfIndInput = len(subs)
    if lensiz < numOfIndInput:
        # Adjust for trailing singleton dimensions
        siz = np.concatenate([siz, np.ones(numOfIndInput - lensiz, dtype=np.float64)])
    elif lensiz > numOfIndInput:
        # Adjust for linear indexing on last element
        head = siz[: numOfIndInput - 1]
        tail = np.asarray([float(np.prod(siz[numOfIndInput - 1 :]))], dtype=np.float64)
        siz = np.concatenate([head, tail])

    ndx = np.asarray(subs[0], dtype=np.float64)
    if numOfIndInput >= 2:
        ndx = ndx + (np.asarray(subs[1], dtype=np.float64) - 1.0) * siz[0]
    if numOfIndInput > 2:
        k = np.cumprod(siz)
        for i in range(3, numOfIndInput + 1):
            v = np.asarray(subs[i - 1], dtype=np.float64)
            ndx = ndx + (v - 1.0) * k[i - 2]

    if np.ndim(ndx) == 0:
        return float(ndx)
    return ndx

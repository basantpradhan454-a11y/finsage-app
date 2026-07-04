"""Safe JSON dumps helper — coerces numpy types to native Python types.
Prevents 'Object of type bool/int64/float32 is not JSON serializable' errors
that occur when numpy scalars leak into chart-data dicts."""
import json
import numpy as np


def _default(o):
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def safe_dumps(obj, **kwargs):
    """Drop-in replacement for json.dumps that never crashes on numpy scalars."""
    return json.dumps(obj, default=_default, **kwargs)

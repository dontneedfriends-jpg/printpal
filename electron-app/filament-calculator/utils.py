def safe_float(value, default=0.0, min_val=None, max_val=None):
    try:
        result = float(value)
        if result < 0:
            return default
        if min_val is not None and result < min_val:
            return default
        if max_val is not None and result > max_val:
            return max_val
        return result
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0, min_val=None, max_val=None):
    try:
        result = int(value)
        if result < 0:
            return default
        if min_val is not None and result < min_val:
            return default
        if max_val is not None and result > max_val:
            return max_val
        return result
    except (TypeError, ValueError):
        return default

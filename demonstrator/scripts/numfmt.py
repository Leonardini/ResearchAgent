"""Number formatting for demonstration narration (HTML).

    import sys; sys.path.insert(0, "<skill-dir>/scripts"); from numfmt import num
    f"the gap is {num(gap)}"    # 0.0732 -> "0.0732"; 2.1e-6 -> "2.1 × 10<sup>−6</sup>"

Four significant figures by default (never more than five), and scientific notation once a
value is below 1e-3 or at least 1e5 in size, so a quantity converging to zero never prints
as 0.00 and the viewer can watch its exponent fall.
"""
import math


def num(x, sig=4):
    assert 1 <= sig <= 5, "at most 5 significant figures"
    if x == 0 or not math.isfinite(x):
        return str(x if x else 0)
    a = abs(x)
    if a < 1e-3 or a >= 1e5:
        m, e = f"{x:.{sig - 1}e}".split("e")
        m = m.rstrip("0").rstrip(".")
        return f"{m} × 10<sup>{int(e)}</sup>".replace("-", "−")
    return f"{float(f'{x:.{sig}g}'):g}".replace("-", "−")


if __name__ == "__main__":
    for v in (0.0732, -0.5732, 2.1e-4, 3.4e-9, 802.589, 123456.0, 0.0, -1e-7):
        print(v, num(v))

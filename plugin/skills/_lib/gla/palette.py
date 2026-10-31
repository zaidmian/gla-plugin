"""The GLA print palette: one maroon, one gold, one gray scale.

Lighter values are tints mixed with white: tint(c, p) keeps share p of the
base colour. gla-plan-formatter/assets/tokens.json and the constants in
semester/scripts/md2docx.py hold the values the builders use; this module
is the rule they follow, so a check can compare against it.
"""

MAROON = "872634"
GOLD = "DABE81"
INK = "272727"
GOLD_TEXT = "8C6D2A"   # gold that must read as text on white; DABE81 is 1.8:1 there
GRAY_STEPS = (1.00, 0.75, 0.55, 0.40, 0.25, 0.12, 0.06, 0.03)


def tint(hexcolor, p):
    """Mix a colour with white, keeping share p of the colour."""
    rgb = [int(hexcolor[i:i + 2], 16) for i in (0, 2, 4)]
    return "".join("%02X" % round(255 - (255 - c) * p) for c in rgb)


GRAYS = tuple(tint(INK, p) for p in GRAY_STEPS)


def _lum(hexcolor):
    out = []
    for i in (0, 2, 4):
        c = int(hexcolor[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]


def contrast(a, b):
    """WCAG contrast ratio of two hex colours."""
    la, lb = _lum(a.lstrip("#")), _lum(b.lstrip("#"))
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def is_tint_of(hexcolor, base, tolerance=1):
    """True when hexcolor equals tint(base, p) for some p in 0..1 (within tolerance per channel)."""
    hexcolor = hexcolor.lstrip("#").upper()
    for k in range(0, 1001):
        t = tint(base, k / 1000)
        if all(abs(int(t[i:i + 2], 16) - int(hexcolor[i:i + 2], 16)) <= tolerance for i in (0, 2, 4)):
            return True
    return False

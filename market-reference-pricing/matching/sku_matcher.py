"""
SKU normalisation and exact-match logic.

Matching rule: two SKUs are the same product if and only if their
normalised strings are character-for-character identical.
No fuzzy / similarity matching is permitted at this layer —
it would silently merge different specs into the same price bucket.
"""

import re
import unicodedata

# ----- Noise word lists -----

_CN_NOISE = [
    "热销",
    "特价",
    "包邮",
    "厅家直销",
    "工厅直销",
    "正品",
    "原装",
    "全国包邮",
    "现货",
    "批发",
    "促销",
    "精品",
    "高品质",
    "质优价廉",
    "刚性需求",
    "同城对答",
    "可定制",
    "定制",
    "定冶",
    "制造商直销",
    "优选",
    "精选",
    "火爆",
    "爆款",
    "下单即发",
    "快速发货",
    "质量保证",
    "做工精细",
    "工厅直出",
    "价格优惠",
]
_EN_NOISE = [
    r"\bhot\s*sale\b",
    r"\bfree\s*shipping\b",
    r"\bfactory\s*direct\b",
    r"\bgenuine\b",
    r"\boriginal\b",
    r"\bbest\s*price\b",
    r"\bhigh\s*quality\b",
    r"\bpromot\w*\b",
    r"\bwholesale\b",
    r"\bcustomiz\w*\b",
    r"\bOEM\b",
    r"\bstock\b",
    r"\bin\s*stock\b",
]

_CN_NOISE_PATTERN = re.compile("|".join(re.escape(w) for w in _CN_NOISE))
_EN_NOISE_PATTERN = re.compile("|".join(_EN_NOISE), re.IGNORECASE)

# ----- Unit conversion to mm -----

_UNIT_PATTERNS = [
    # e.g. "25.4cm" or "25.4 cm"
    (re.compile(r"([\d.]+)\s*cm\b", re.IGNORECASE), lambda m: f"{float(m.group(1)) * 10:.2f}mm"),
    (re.compile(r"([\d.]+)\s*厘米\b"), lambda m: f"{float(m.group(1)) * 10:.2f}mm"),
    # inches: support ", inch, inches, 英寸, in
    (re.compile(r'([\d.]+)\s*("|inch(?:es)?|英寸)\b', re.IGNORECASE), lambda m: f"{float(m.group(1)) * 25.4:.2f}mm"),
    (re.compile(r"([\d.]+)\s*\bin\b"), lambda m: f"{float(m.group(1)) * 25.4:.2f}mm"),
]

# ----- Full-width to half-width -----

def _to_halfwidth(text: str) -> str:
    """Convert full-width ASCII characters (！-～) to half-width."""
    result = []
    for ch in text:
        code = ord(ch)
        if 0xFF01 <= code <= 0xFF5E:
            result.append(chr(code - 0xFEE0))
        elif ch == "　":  # Ideographic space
            result.append(" ")
        else:
            result.append(ch)
    return "".join(result)


def normalize_sku(raw_text: str) -> str:
    """
    Normalise a raw SKU/model string for exact matching.

    Steps (applied in order):
      1. Unicode NFC normalisation
      2. Full-width -> half-width conversion
      3. Remove Chinese marketing noise words
      4. Remove English noise phrases
      5. Convert unit strings to mm (cm, inch, 英寸, 厘米)
      6. Collapse whitespace
      7. Uppercase
      8. Strip leading/trailing whitespace

    Matching rule: two SKUs that produce the same normalised string
    are considered the same product. Different normalised strings
    MUST be treated as different products — never use fuzzy matching here.
    """
    if not raw_text:
        return ""

    text = unicodedata.normalize("NFC", raw_text)
    text = _to_halfwidth(text)
    text = _CN_NOISE_PATTERN.sub("", text)
    text = _EN_NOISE_PATTERN.sub("", text)

    for pattern, replacer in _UNIT_PATTERNS:
        text = pattern.sub(replacer, text)

    # Collapse all whitespace to single space
    text = re.sub(r"\s+", " ", text)
    text = text.upper().strip()

    return text


def is_exact_match(a: str, b: str) -> bool:
    """Return True iff the two raw SKU strings normalise to the same string."""
    return normalize_sku(a) == normalize_sku(b)

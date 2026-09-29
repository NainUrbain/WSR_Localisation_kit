"""Japanese (ja-JP) review checks for the locale framework.

locale_framework.py picks this module through the profile's "morphology"
field. Japanese needs no VAR metadata beyond `target`.
"""

import re

HANGUL_RE = re.compile(r"[가-힣]")
# Korean particle notation left behind when adapting a Korean translation.
KOREAN_PARTICLE_RE = re.compile(r"@[A-Z]+\d*(?:은/는|이/가|을/를|과/와|이나/나|로/으로|\(으\)로|:(?:TOPIC|SUBJECT|OBJECT|AND|ALSO_EVEN|RO)\b)")


def review_target(target):
    """Return (errors, warnings) for one Japanese target string."""
    errors = []
    if HANGUL_RE.search(target):
        errors.append("Hangul remains in the Japanese target")
    if KOREAN_PARTICLE_RE.search(target):
        errors.append("Korean particle notation after a token; write the Japanese particle directly")
    return errors, []

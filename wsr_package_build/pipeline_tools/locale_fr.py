"""French (fr-FR) morphology rules for the data-only locale framework.

locale_framework.py picks this module through the profile's "morphology"
field. It supplies:

- REQUIRED_VAR_COLUMNS: locales/fr-FR/vars columns French needs filled
  (gender/number drive game_files/js/frenchArticles.js);
- review_target(): French-specific review checks for one target string.
"""

import re


ARTICLE_TOKEN_RE = re.compile(
    r"""(?ix)
    \b(?:
        de\s+la\s+ | de\s+l[’']\s* |
        à\s+la\s+  | à\s+l[’']\s*  |
        a\s+la\s+  | a\s+l[’']\s*  |
        le\s+ | la\s+ | les\s+ | un\s+ | une\s+ |
        du\s+ | des\s+ | de\s+ | au\s+ | aux\s+ | à\s+ | a\s+ | que\s+
    )
    @(CORP(?:FULL)?|IND|COUNTRY|REGION|ASSET|COMMODITY|PLAYER)\d*\b
    """,
)
MISSING_GRAVE_RE = re.compile(
    r"(?i)\ba\s+(?:la\s+|l[’']\s*)"
    r"@(CORP(?:FULL)?|IND|COUNTRY|REGION|ASSET|COMMODITY|PLAYER)\d*\b"
)
AGREEMENT_RE = re.compile(
    r"\b(?:ce|cet|cette|ces|nouveau|nouvelle|nouveaux|nouvelles)\s+@", re.I
)
HANGUL_RE = re.compile(r"[가-힣]")
# Blank values in these locales/fr-FR/vars columns are reported for review.
REQUIRED_VAR_COLUMNS = ("gender", "number")


def review_target(target):
    """Return (errors, warnings) for one French target string."""
    errors = []
    warnings = []
    if HANGUL_RE.search(target):
        errors.append("Hangul remains in French target")
    if ARTICLE_TOKEN_RE.search(target):
        warnings.append("review French gender/elision or contraction before token")
    if MISSING_GRAVE_RE.search(target):
        warnings.append("use French 'à la' or 'à l’', not unaccented 'a'")
    punctuation_text = re.sub(r"@[A-Z]+\d*(?::[A-Z_]+)+", "@TOKEN", target)
    if re.search(r"\S[:;!?]", punctuation_text):
        warnings.append("use a non-breaking space before French : ; ! ?")
    if AGREEMENT_RE.search(target):
        warnings.append("review gender/number agreement around token")
    return errors, warnings

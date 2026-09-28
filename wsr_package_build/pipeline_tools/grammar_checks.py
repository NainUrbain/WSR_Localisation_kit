"""Validate target-only agreement expressions before shipping them."""
import re

SELECTOR = re.compile(r"\{\{@([A-Z]+)(\d+)?\.(gender|number|agreement|plural)\|([^{}]*)\}\}")


def selector_problems(target):
    errors = []
    stripped = SELECTOR.sub("", target)
    if "{{" in stripped or "}}" in stripped:
        errors.append("malformed grammar selector (nested choices/selectors are not supported)")
    for match in SELECTOR.finditer(target):
        _, index, feature, body = match.groups()
        if index and int(index) < 1:
            errors.append("grammar token indexes start at 1")
        keys = set()
        allowed = {"gender": {"m", "f", "n", "other"},
                   "number": {"sg", "pl", "other"},
                   "agreement": {"m_sg", "f_sg", "n_sg", "m_pl", "f_pl", "n_pl", "other"},
                   "plural": {"zero", "one", "two", "few", "many", "other"}}[feature]
        for branch in body.split("|"):
            key, sep, _ = branch.partition("=")
            key = key.strip()
            if not sep or not key or key in keys:
                errors.append("grammar branches need unique key=value pairs")
            if key not in allowed and not (feature == "plural" and re.fullmatch(r"-?\d+(?:\.\d+)?", key)):
                errors.append(f"unsupported {feature} branch: {key!r}")
            keys.add(key)
        if "other" not in keys:
            errors.append("grammar selector requires an other= fallback")
    return errors


def without_selectors(target):
    """Keep references/branch text for token checking, but hide grammar pipes."""
    return SELECTOR.sub(lambda m: "@" + m[1] + (m[2] or "") + " " + " ".join(
        part.partition("=")[2] for part in m[4].split("|")), target)

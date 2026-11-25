import re

_MARK = re.compile(r"\[S(\d+)\]")


def validate_markers(answer: str, n_sources: int) -> tuple[str, list[int]]:
    """Keep only [S#] markers that map to a real retrieved source.

    Returns the cleaned answer and the source numbers actually cited, in order.
    """
    used: list[int] = []

    def keep_or_drop(match: re.Match) -> str:
        i = int(match.group(1))
        if 1 <= i <= n_sources:
            if i not in used:
                used.append(i)
            return match.group(0)
        return ""

    cleaned = _MARK.sub(keep_or_drop, answer)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    return cleaned, used

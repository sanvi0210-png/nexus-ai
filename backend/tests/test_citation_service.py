from app.services.citation_service import validate_markers


def test_valid_markers_are_kept_in_order():
    text, used = validate_markers("A [S2] and B [S1] and again [S2].", 3)
    assert used == [2, 1]
    assert "[S2]" in text


def test_invented_markers_are_removed():
    text, used = validate_markers("Claim [S9] here.", 3)
    assert used == []
    assert "[S9]" not in text

from app.services.fusion import reciprocal_rank_fusion
from app.services.json_utils import parse_json


def test_rrf_promotes_items_found_by_both_lists():
    a = [{"id": "x"}, {"id": "y"}, {"id": "z"}]
    b = [{"id": "z"}, {"id": "x"}]
    assert [i["id"] for i in reciprocal_rank_fusion([a, b])][:2] == ["x", "z"]


def test_rrf_keeps_first_list_item_data():
    out = reciprocal_rank_fusion([[{"id": "x", "score": 0.9}], [{"id": "x", "score": 0.0}]])
    assert out[0]["score"] == 0.9


def test_parse_json_handles_fences_and_noise():
    assert parse_json('```json\n["a","b"]\n```', []) == ["a", "b"]
    assert parse_json('Sure! {"unsupported": []} done', {}) == {"unsupported": []}
    assert parse_json("not json", []) == []

import asyncio
import json

import pytest

from app import services
from app.services import contains_prohibited, unavailable_ingredients, validate_recipe

GOOD = {"title": "Spinach Tomato Saute", "ingredients": ["tomato", "spinach", "olive oil"],
        "steps": ["Heat oil.", "Cook tomato and spinach."]}


@pytest.fixture(autouse=True)
def clear_cache():
    services._cache.clear()


def fake_llm(*responses):
    """Build a stand-in for _call_llm that returns the given raw responses in order."""
    calls = iter(responses)

    async def _fake(messages):
        return next(calls)
    return _fake


def test_vegan_filter_flags_prohibited_items():
    assert "egg" in contains_prohibited("Scrambled egg with spinach", "vegan")


def test_vegan_filter_ignores_eggplant():
    assert contains_prohibited("Roasted eggplant", "vegan") == []


def test_unavailable_ingredient_detected():
    assert unavailable_ingredients(["tomato", "chicken breast"], ["tomato", "spinach"]) == ["chicken breast"]


def test_validate_rejects_bad_json():
    recipe, errors = validate_recipe("not json", ["tomato"], None)
    assert recipe is None and errors


def test_validate_accepts_good_recipe():
    recipe, errors = validate_recipe(json.dumps(GOOD), ["tomato", "spinach"], "vegan")
    assert recipe == GOOD and errors == []


def test_generate_retries_after_diet_violation(monkeypatch):
    bad = dict(GOOD, ingredients=["tomato", "egg"])
    monkeypatch.setattr(services, "_call_llm", fake_llm(json.dumps(bad), json.dumps(GOOD)))
    result = asyncio.run(services.generate_refined_recipe(["tomato", "egg", "spinach"], "vegan"))
    assert result["title"] == GOOD["title"] and result["cached"] is False


def test_generate_raises_after_repeated_failures(monkeypatch):
    monkeypatch.setattr(services, "_call_llm", fake_llm("nope", "still nope"))
    with pytest.raises(services.RecipeValidationError):
        asyncio.run(services.generate_refined_recipe(["tomato"], None))


def test_second_identical_request_is_cached(monkeypatch):
    monkeypatch.setattr(services, "_call_llm", fake_llm(json.dumps(GOOD)))
    asyncio.run(services.generate_refined_recipe(["tomato", "spinach"], None))
    again = asyncio.run(services.generate_refined_recipe(["Spinach", "tomato"], None))
    assert again["cached"] is True

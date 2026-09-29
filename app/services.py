"""AI service: recipe generation with structured output and a validation layer."""
import json
import os
import re

# Pantry staples the model may add without them being "hallucinated".
PANTRY_STAPLES = {"salt", "pepper", "water", "oil", "olive oil", "cooking spray"}

PROHIBITED_BY_DIET = {
    "vegan": ["egg", "milk", "butter", "meat", "cheese", "honey", "chicken", "beef",
              "pork", "fish", "yogurt", "cream"],
    "vegetarian": ["meat", "chicken", "beef", "pork", "fish", "bacon", "ham", "shrimp"],
    "dairy-free": ["milk", "butter", "cheese", "yogurt", "cream"],
    "gluten-free": ["wheat", "flour", "bread", "pasta", "barley", "rye", "soy sauce"],
}

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_ATTEMPTS = 2

_cache: dict[str, dict] = {}


class RecipeGenerationError(Exception):
    """The upstream model call failed."""


class RecipeValidationError(Exception):
    """The model's output failed validation after all retries."""


class MissingAPIKeyError(Exception):
    """OPENAI_API_KEY is not configured."""


# ---------- validation layer ----------

def contains_prohibited(recipe_text: str, diet: str) -> list[str]:
    """Return items in recipe_text that violate the diet (whole-word match, so
    'eggplant' does not trigger 'egg')."""
    text = recipe_text.lower()
    return [
        item for item in PROHIBITED_BY_DIET.get((diet or "").lower(), [])
        if re.search(rf"\b{re.escape(item)}s?\b", text)
    ]


def _norm(name: str) -> str:
    name = re.sub(r"[^a-z\s-]", " ", name.lower())
    return " ".join(name.split())


def _stem(word: str) -> str:
    return word[:-1] if word.endswith("s") and len(word) > 3 else word


def unavailable_ingredients(recipe_ingredients: list[str], available: list[str]) -> list[str]:
    """Return recipe ingredients that are neither provided by the user nor pantry staples."""
    have = [_norm(a) for a in available]
    have_stems = {_stem(w) for a in have for w in a.split()}
    missing = []
    for ing in recipe_ingredients:
        n = _norm(ing)
        if any(s in n for s in PANTRY_STAPLES):
            continue
        words = {_stem(w) for w in n.split()}
        if not words & have_stems:
            missing.append(ing)
    return missing


def validate_recipe(raw: str, available: list[str], preference: str | None) -> tuple[dict | None, list[str]]:
    """Parse and validate model output. Returns (recipe, errors)."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None, ["Output was not valid JSON."]
    if not isinstance(data, dict):
        return None, ["Output must be a JSON object."]

    errors = []
    if not isinstance(data.get("title"), str) or not data["title"].strip():
        errors.append("Missing or empty 'title'.")
    for key in ("ingredients", "steps"):
        val = data.get(key)
        if not isinstance(val, list) or not val or not all(isinstance(v, str) for v in val):
            errors.append(f"'{key}' must be a non-empty list of strings.")
    if errors:
        return None, errors

    bad = unavailable_ingredients(data["ingredients"], available)
    if bad:
        errors.append(f"Uses ingredients that were not provided: {', '.join(bad)}.")
    if preference:
        text = " ".join(data["ingredients"] + data["steps"])
        violations = contains_prohibited(text, preference)
        if violations:
            errors.append(f"Violates '{preference}' diet: {', '.join(violations)}.")

    return (data if not errors else None), errors


# ---------- LLM call ----------

def _system_prompt(preference: str | None) -> str:
    diet = f" Dietary preference: {preference}. No ingredient or step may violate it." if preference else ""
    return (
        "You are the FridgeChef AI. Generate a recipe using ONLY the ingredients the user "
        "provides, plus basic pantry staples (salt, pepper, water, oil)." + diet +
        " Return ONLY a JSON object with keys: 'title' (string), 'ingredients' "
        "(list of strings), 'steps' (list of strings)."
    )


async def _call_llm(messages: list[dict]) -> str:
    """Single chat-completion call in JSON mode."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise MissingAPIKeyError("OPENAI_API_KEY is not set.")
    from openai import AsyncOpenAI  # imported lazily so the app/tests load without it

    client = AsyncOpenAI(api_key=api_key, timeout=20.0)
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=700,
        )
    except Exception as exc:  # network, auth, rate limit, etc.
        raise RecipeGenerationError(str(exc)) from exc
    return response.choices[0].message.content


def _cache_key(ingredients: list[str], preference: str | None) -> str:
    return json.dumps([sorted(_norm(i) for i in ingredients), (preference or "").lower()])


async def generate_refined_recipe(ingredients: list[str], preference: str | None = None) -> dict:
    """Generate a validated recipe. Retries once with the validation errors as feedback."""
    ingredients = [i.strip() for i in ingredients if i and i.strip()]
    key = _cache_key(ingredients, preference)
    if key in _cache:
        return {**_cache[key], "cached": True}

    messages = [
        {"role": "system", "content": _system_prompt(preference)},
        {"role": "user", "content": f"Ingredients: {', '.join(ingredients)}."},
    ]
    errors: list[str] = []
    for _ in range(MAX_ATTEMPTS):
        raw = await _call_llm(messages)
        recipe, errors = validate_recipe(raw, ingredients, preference)
        if recipe:
            _cache[key] = recipe
            return {**recipe, "cached": False}
        messages += [
            {"role": "assistant", "content": raw or ""},
            {"role": "user", "content": "That recipe was rejected: " + " ".join(errors) + " Fix these and return the JSON again."},
        ]
    raise RecipeValidationError(" ".join(errors))

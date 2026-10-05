import logging
import httpx
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("meals")

BASE_URL = "https://www.themealdb.com/api/json/v1/1"


def format_meal_details(meal):
    ingredients = []

    for index in range(1, 21):
        ingredient = meal.get(f"strIngredient{index}")
        measure = meal.get(f"strMeasure{index}")

        if ingredient and ingredient.strip():
            ingredients.append(
                {
                    "name": ingredient.strip(),
                    "measure": measure.strip() if measure else "",
                }
            )

    return {
        "id": meal["idMeal"],
        "name": meal["strMeal"],
        "category": meal["strCategory"],
        "area": meal["strArea"],
        "instructions": meal["strInstructions"],
        "image": meal["strMealThumb"],
        "source": meal.get("strSource"),
        "youtube": meal.get("strYoutube"),
        "ingredients": ingredients,
    }


@mcp.tool()
def search_meals_by_name(query: str, limit: int = 5):
    if limit < 1 or limit > 25:
        raise ValueError("limit must be between 1 and 25")

    try:
        response = httpx.get(
            f"{BASE_URL}/search.php",
            params={"s": query},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise RuntimeError(f"TheMealDB request failed: {error}") from error

    meals = data.get("meals")

    if meals is None:
        return {
            "message": "no matches",
            "results": [],
        }

    results = []

    for meal in meals[:limit]:
        results.append(
            {
                "id": meal["idMeal"],
                "name": meal["strMeal"],
                "area": meal["strArea"],
                "category": meal["strCategory"],
                "thumb": meal["strMealThumb"],
            }
        )

    return results


@mcp.tool()
def meals_by_ingredient(ingredient: str, limit: int = 12):
    if limit < 1 or limit > 25:
        raise ValueError("limit must be between 1 and 25")

    try:
        response = httpx.get(
            f"{BASE_URL}/filter.php",
            params={"i": ingredient},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise RuntimeError(f"TheMealDB request failed: {error}") from error

    meals = data.get("meals")

    if meals is None:
        return {
            "message": "no matches",
            "results": [],
        }

    results = []

    for meal in meals[:limit]:
        results.append(
            {
                "id": meal["idMeal"],
                "name": meal["strMeal"],
                "thumb": meal["strMealThumb"],
            }
        )

    return results


@mcp.tool()
def random_meal():
    try:
        response = httpx.get(
            f"{BASE_URL}/random.php",
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise RuntimeError(f"TheMealDB request failed: {error}") from error

    meals = data.get("meals")

    if not meals:
        return {
            "message": "no matches",
            "result": None,
        }

    return format_meal_details(meals[0])


@mcp.tool()
def meal_details(id: str | int):
    try:
        response = httpx.get(
            f"{BASE_URL}/lookup.php",
            params={"i": str(id)},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise RuntimeError(f"TheMealDB request failed: {error}") from error

    meals = data.get("meals")

    if not meals:
        return {
            "message": "no matches",
            "result": None,
        }

    return format_meal_details(meals[0])


if __name__ == "__main__":
    mcp.run()
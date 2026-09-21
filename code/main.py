import os
import uvicorn
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from routers.auth import router as auth_router


# Create FastAPI app
app = FastAPI()


# Paths
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web_application"


# HW3 session management
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-key")

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    https_only=True,
    same_site="lax",
    max_age=3600
)


# HW3 authentication routes
app.include_router(auth_router)


# Previous homework static files
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/styles.css")
def stylesheet():
    return FileResponse(BASE_DIR / "styles.css")


# Previous homework page
# Moved from "/" because HW3 authentication uses "/"
@app.get("/restaurant-app")
def restaurant_app():
    return FileResponse(WEB_DIR / "index.html")


# Previous homework restaurant data/API
restaurants = [
    {
        "id": 1,
        "restaurantName": "O2 Valley",
        "restaurantAddress": "452 University Ave"
    }
]


class RestaurantCreate(BaseModel):
    restaurantName: str
    restaurantAddress: str


@app.get("/api/restaurants")
def get_restaurants():
    return restaurants


@app.post("/api/restaurants")
def add_restaurant(restaurant: RestaurantCreate):
    next_id = max((r["id"] for r in restaurants), default=0) + 1

    new_restaurant = {
        "id": next_id,
        "restaurantName": restaurant.restaurantName,
        "restaurantAddress": restaurant.restaurantAddress
    }

    restaurants.append(new_restaurant)
    return new_restaurant


@app.put("/api/restaurants/1")
def update_restaurant_one(restaurant: RestaurantCreate):
    for existing_restaurant in restaurants:
        if existing_restaurant["id"] == 1:
            existing_restaurant["restaurantName"] = restaurant.restaurantName
            existing_restaurant["restaurantAddress"] = restaurant.restaurantAddress
            return existing_restaurant

    return {"error": "Restaurant with ID 1 not found"}


@app.delete("/api/restaurants/highest")
def delete_highest_restaurant():
    if not restaurants:
        return {"error": "No restaurants to delete"}

    highest_id = max(r["id"] for r in restaurants)

    for restaurant in restaurants:
        if restaurant["id"] == highest_id:
            restaurants.remove(restaurant)
            return restaurant


@app.get("/api/restaurants/search")
def search_restaurants(query: str):
    query = query.lower()

    return [
        restaurant
        for restaurant in restaurants
        if query in restaurant["restaurantName"].lower()
        or query in restaurant["restaurantAddress"].lower()
    ]


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8081,
        reload=True
    )
from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Annotated
import models as models
from database import engine, SessionLocal
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from google import genai
import json
from dotenv import load_dotenv
import os
from collections import defaultdict
from time import time as _time
import auth
from auth import get_current_user

load_dotenv()

app = FastAPI()
app.include_router(auth.router)
# models.Base.metadata.create_all(bind=engine) # Using Alembic for migrations, so this line is commented out

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def calculate_nutri(meal: str) -> dict:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=f'Give me the nutritional values of: {meal}. Reply ONLY in pure JSON, no markdown, no extra text: {{"calories": 0, "carbohydrates": 0, "proteins": 0, "fats": 0}}'
    )
    text = response.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

# ── In-memory rate limiter for /meals/analyse/ ──
# Tracks {user_id: [timestamp, ...]} of recent calls
_analyse_calls: dict = defaultdict(list)
RATE_LIMIT   = 5   # max calls
RATE_WINDOW  = 120   # per N seconds

def check_analyse_rate(user_id: int):
    now = _time()
    window_start = now - RATE_WINDOW
    # Keep only timestamps within the rolling window
    _analyse_calls[user_id] = [t for t in _analyse_calls[user_id] if t > window_start]
    if len(_analyse_calls[user_id]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: max {RATE_LIMIT} meal analyses per {RATE_WINDOW}s. Try again shortly."
        )
    _analyse_calls[user_id].append(now)

class AnalyseMeal(BaseModel):
    meal_details: str

class MealCreate(BaseModel):
    date: date
    meal_type: str
    calories: int
    carbohydrates: int
    proteins: int
    fats: int
    meal_details: str

class FavMeal(BaseModel):
    calories: int
    carbohydrates: int
    proteins: int
    fats: int
    meal_details: str


# @app.get("/")
# async def root():
#     return {"message": "Welcome to the Nutri Calc"}

#----------------CREATE------------------


@app.post("/meals/")
async def create_meal(meal: MealCreate, db: db_dependency, user: user_dependency):

    db_meal = models.Meals(
        date=meal.date,
        meal_type=meal.meal_type,
        calories=meal.calories,
        carbohydrates=meal.carbohydrates,
        proteins=meal.proteins,
        fats=meal.fats,
        meal_details=meal.meal_details,
        user_id=user['id']
    )
    db.add(db_meal)
    db.commit()
    db.refresh(db_meal)
    return db_meal


'''@app.post("/meals/fav/")
async def create_meal_fav(meal: FavMeal, db: db_dependency):
    db_meal = models.Favorites(
        calories=meal.calories,
        carbohydrates=meal.carbohydrates,
        proteins=meal.proteins,
        fats=meal.fats,
        meal_details=meal.meal_details
    )
    db.add(db_meal)
    db.commit()
    db.refresh(db_meal)
    return db_meal'''

@app.post("/meals/fav/")
async def create_meal_fav(meal_id: int, db: db_dependency, user: user_dependency):
    db_meal = db.query(models.Meals).filter(models.Meals.id == meal_id).first()
    if not db_meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    
    db_fav = models.Favorites(
        calories=db_meal.calories,
        carbohydrates=db_meal.carbohydrates,
        proteins=db_meal.proteins,
        fats=db_meal.fats,
        meal_details=db_meal.meal_details,
        user_id=user['id']
    )
    db.add(db_fav)
    db.commit()
    db.refresh(db_fav)
    return db_fav

@app.post("/meals/single_fav/")
async def create_meal_fav_single(meal: FavMeal, db: db_dependency, user: user_dependency):
    
    db_fav = models.Favorites(
        calories=meal.calories,
        carbohydrates=meal.carbohydrates,
        proteins=meal.proteins,
        fats=meal.fats,
        meal_details=meal.meal_details,
        user_id=user['id']
    )
    db.add(db_fav)
    db.commit()
    db.refresh(db_fav)
    return db_fav

@app.post("/meals/analyse/")
async def analyze_meal(meal: AnalyseMeal, user: user_dependency):
    check_analyse_rate(user['id'])   # raises 429 if limit exceeded
    return calculate_nutri(meal.meal_details)
    
#----------------READ------------------

@app.get("/user/")
async def get_user_profile(user: user_dependency, db: db_dependency):
    db_user = db.query(models.Users).filter(models.Users.id == user['id']).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": db_user.id,
        "username": db_user.username,
        "role": db_user.role,
        "target_calorie": db_user.target_calorie
    }

@app.get("/meals/")
async def all_meals(db: db_dependency, user: user_dependency):
    if user['role'] != 'admin':
        meals = db.query(models.Meals).filter(models.Meals.user_id == user['id']).all()
    else:
        meals = db.query(models.Meals).all()
    return meals

@app.get("/meals/fav/")
async def fav_meals(db:db_dependency,user:user_dependency):
    favs = db.query(models.Favorites).filter(models.Favorites.user_id == user['id']).all()
    if not favs:
        raise HTTPException(status_code=404, detail="No favorites found")
    return favs

@app.get("/meals/{meal_date}/")
async def search_all_meals_date(meal_date: str, db: db_dependency,user:user_dependency):
    if user['role'] != 'admin':
        db_meal = db.query(models.Meals).filter(models.Meals.date == meal_date,models.Meals.user_id == user['id']).all()
    else:
        db_meal = db.query(models.Meals).filter(models.Meals.date == meal_date).all()
    if not db_meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    return db_meal

@app.get("/meals/summary/{meal_date}/")
async def summary_meal_date(meal_date: str, db: db_dependency,user: user_dependency):
    db_meal = db.query(models.Meals).filter(models.Meals.date == meal_date,models.Meals.user_id == user['id']).all()
    if not db_meal:
        raise HTTPException(status_code=404, detail="Meal not found")

    total_calories = db.query(func.sum(models.Meals.calories)).filter(models.Meals.date == meal_date,models.Meals.user_id == user['id']).scalar() or 0
    total_carbohydrates = db.query(func.sum(models.Meals.carbohydrates)).filter(models.Meals.date == meal_date,models.Meals.user_id == user['id']).scalar() or 0
    total_proteins = db.query(func.sum(models.Meals.proteins)).filter(models.Meals.date == meal_date,models.Meals.user_id == user['id']).scalar() or 0
    total_fats = db.query(func.sum(models.Meals.fats)).filter(models.Meals.date == meal_date,models.Meals.user_id == user['id']).scalar() or 0
    return {
        "total_calories": total_calories,
        "total_carbohydrates": total_carbohydrates,
        "total_proteins": total_proteins,
        "total_fats": total_fats
    }

@app.get("/meals/{meal_date}/{meal_type}/")
async def search_meal_date_type(meal_date: str, meal_type: str, db: db_dependency,user:user_dependency):
    db_meal = db.query(models.Meals).filter(models.Meals.date == meal_date, models.Meals.meal_type == meal_type,models.Meals.user_id == user['id']).all()
    if not db_meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    return db_meal



#----------------UPDATE------------------

@app.put("/meals/{meal_id}/")
async def update_meal(meal_id: int, meal: MealCreate, db: db_dependency,user:user_dependency):
    db_meal = db.query(models.Meals).filter(models.Meals.id == meal_id,models.Meals.user_id == user['id']).first()
    if not db_meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    
    db_meal.calories = meal.calories
    db_meal.carbohydrates = meal.carbohydrates
    db_meal.proteins = meal.proteins
    db_meal.fats = meal.fats
    db_meal.meal_details = meal.meal_details
    
    db.commit()
    db.refresh(db_meal)
    return db_meal


@app.put("/user/calorie_target/")
async def update_calorie_target(calories: int, user: user_dependency, db: db_dependency):
    db_user = db.query(models.Users).filter(models.Users.id == user['id']).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.target_calorie = calories
    db.commit()
    return {"message": "Calorie target updated", "target_calorie": calories}
#----------------DELETE------------------

@app.delete("/meals/{meal_id}/")
async def delete_meal(meal_id: int, db: db_dependency,user:user_dependency):
    db_meal = db.query(models.Meals).filter(models.Meals.id == meal_id,models.Meals.user_id == user['id']).first()
    if not db_meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    
    db.delete(db_meal)
    db.commit()
    return {"message": "Meal deleted successfully"}

@app.delete("/meals/fav/{fav_id}/")
async def delete_fav(fav_id: int, db: db_dependency,user:user_dependency):
    db_fav = db.query(models.Favorites).filter(models.Favorites.id == fav_id,models.Favorites.user_id == user['id']).first()
    if not db_fav:
        raise HTTPException(status_code=404, detail="Favorite not found")
    
    db.delete(db_fav)
    db.commit()
    return {"message": "Favorite deleted successfully"}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
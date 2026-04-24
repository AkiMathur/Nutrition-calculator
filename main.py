from fastapi import FastAPI,HTTPException, Depends
from pydantic import BaseModel
from typing import List, Annotated
import models as models
from database import engine,SessionLocal
from sqlalchemy.orm import Session

app = FastAPI()
# models.Base.metadata.create_all(bind=engine) # Using Alembic for migrations, so this line is commented out

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

class MealCreate(BaseModel):
    date: str
    meal_type: str
    calories: int
    carbohydrates: int
    proteins: int
    fats: int
    meal_details: str


@app.get("/")
async def root():
    return {"message": "Welcome to the Nutri Calc"}

#----------------CREATE------------------

@app.post("/meals/")
async def create_meal(meal: MealCreate, db: db_dependency):
    db_meal = models.Meals(
        date=meal.date,
        meal_type=meal.meal_type,
        calories=meal.calories,
        carbohydrates=meal.carbohydrates,
        proteins=meal.proteins,
        fats=meal.fats,
        meal_details=meal.meal_details
    )
    db.add(db_meal)
    db.commit()
    db.refresh(db_meal)
    return db_meal

#----------------READ------------------

@app.get("/meals/")
async def all_meals(db: db_dependency):
    meals = db.query(models.Meals).all()
    return meals


@app.get("/meals/{meal_date}/")
async def search_all_meals_date(meal_date: str, db: db_dependency):
    db_meal = db.query(models.Meals).filter(models.Meals.date == meal_date).all()
    if not db_meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    return db_meal

@app.get("/meals/{meal_date}/{meal_type}/")
async def search_meal_date_type(meal_date: str, meal_type: str, db: db_dependency):
    db_meal = db.query(models.Meals).filter(models.Meals.date == meal_date, models.Meals.meal_type == meal_type).all()
    if not db_meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    return db_meal

#----------------UPDATE------------------




@app.post("/meals/fav/")
async def create_meal_fav(meal: MealCreate, db: db_dependency):
    
    pass
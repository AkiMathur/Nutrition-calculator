from sqlalchemy import Boolean, Column,Integer,String,Date,ForeignKey
from database import Base


class Users(Base):
    __tablename__ = "users"

    id = Column(Integer,primary_key=True,index=True)
    username = Column(String,unique=True,index=True,nullable=False)
    hashed_password = Column(String,nullable=False)
    role = Column(String, default="user", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    target_calorie = Column(Integer,default=2000,nullable=False)

class Meals(Base):
    __tablename__ = "meals"
    
    id = Column(Integer,primary_key=True,index=True)
    user_id = Column(Integer,ForeignKey("users.id"), nullable=False)
    date = Column(Date,nullable=False,index=True)
    meal_type = Column(String,nullable=False,index=True)
    calories = Column(Integer,default=0,nullable=False)
    carbohydrates = Column(Integer,default=0,nullable=False)
    proteins = Column(Integer,default=0,nullable=False)
    fats = Column(Integer,default=0,nullable=False)
    meal_details = Column(String,nullable=False)

class Favorites(Base):
    __tablename__ = "favorites"
    
    id = Column(Integer,primary_key=True,index=True)
    user_id = Column(Integer,ForeignKey("users.id"), nullable=False)
    calories = Column(Integer,default=0,nullable=False)
    carbohydrates = Column(Integer,default=0,nullable=False)
    proteins = Column(Integer,default=0,nullable=False)
    fats = Column(Integer,default=0,nullable=False)
    meal_details = Column(String,nullable=False)
    
#alembic revision --autogenerate -m "new table"
#alembic upgrade head
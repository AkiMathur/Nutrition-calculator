from sqlalchemy import Boolean, Column,Integer,String,Date
from database import Base

class Meals(Base):
    __tablename__ = "meals"

    id = Column(Integer,primary_key=True,index=True)
    date = Column(Date,nullable=False,index=True)
    meal_type = Column(String,nullable=False,index=True)
    calories = Column(Integer,default=0,nullable=False)
    carbohydrates = Column(Integer,default=0,nullable=False)
    proteins = Column(Integer,default=0,nullable=False)
    fats = Column(Integer,default=0,nullable=False)
    meal_details = Column(String,nullable=False)
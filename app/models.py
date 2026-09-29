from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    dietary_preferences = Column(JSON, nullable=True)  # e.g., ["vegan", "keto"]

    recipes = relationship("SavedRecipe", back_populates="owner")


class SavedRecipe(Base):
    __tablename__ = "saved_recipes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    ingredients_used = Column(JSON)
    instructions = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="recipes")

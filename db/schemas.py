from pydantic import BaseModel
from fastapi import Body
from typing import Union


class BookBase(BaseModel):
    title: str
    pages: int = Body(ge=10)


class BookCreate(BookBase):
    # author_id: int
    pass


class BookResponse(BaseModel):
    author_id: int

    class Config:
        form_attributes = True


class AuthorBase(BaseModel):
    name: str = Body(min_length=3, max_length=30)


class AuthorResponse(AuthorBase):
    id: int


class UserBase(BaseModel):
    username: str
    password: str


class AuthorResponse(BaseModel):
    pass


class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True


class Book():
    books: list[BookResponse] = []

    class Config:
        from_attributes = True


class Author():
    name: str = Body(min_length=3, max_length=30)
    id: int


class User():
    id: int
    username: str = Body(min_length=3, max_length=30)
    year: int = Body(le=1900, ge=2024)
    email: str
    description: str = Body(min_length=10, max_length=100)


class UserDB(User):
    password: str


class UserCreate(BaseModel):
    username: str
    password: str
    year: int
    email: Union[str, None] = None
    description: Union[str, None] = None

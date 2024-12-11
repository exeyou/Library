from sqlalchemy.orm import Session
from . import models, schemas
from datetime import *
import bcrypt


def create_author(db: Session, author: schemas.AuthorBase):
    author = models.Author(name=author.name)
    db.add(author)
    db.commit()
    db.refresh(author)
    return author


def create_book(db: Session, book: schemas.BookBase, author_id: int):
    book = models.Book(title=book.title, pages=book.pages, author_id=author_id)
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def create_user(db: Session, user: schemas.UserBase):
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_user = models.User(username=user.username, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

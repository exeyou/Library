from fastapi import FastAPI, Path, HTTPException, Query, Body, Depends, Form
from pydantic import BaseModel, ValidationError
from typing import List, Annotated, Optional
from sqlalchemy.orm import Session
from db import crud, models, schemas
from db.database import SessionLocal, engine
#from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

import bcrypt
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

# SECRET_KEY = "19109197bd5e7c289b92b2b355083ea26c71dee2085ceccc19308a7291b2ea06"
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 30

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") #

app = FastAPI()
templates = Jinja2Templates(directory="templates")
models.Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

library = {}


def find_book_by_title(title, books):
    for i in books:
        if title == i["title"]:
            return i
    return None


@app.post("/token")
async def token_get(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not db_user or not bcrypt.checkpw(form_data.password.encode('utf-8'), db_user.password.encode('utf-8')):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    return {"access_token": db_user.username, "token_type": "bearer"}


@app.post("/library/adduser", response_model=schemas.UserResponse)
async def add_user(user: schemas.UserBase, db: Session = Depends(get_db)):
    return crud.create_user(db, user)


@app.post("/library/addauthor", response_model=schemas.AuthorResponse)
async def add_author(author: schemas.AuthorBase, db: Session = Depends(get_db), token=Depends(oauth2_scheme)):
    return crud.create_author(db, author)


@app.post("/library/{author}/addbook/", response_model=schemas.BookBase)
def add_book(author: Annotated[str, Path(min_length=3, max_length=30)],
             book: schemas.BookCreate,
             db: Session = Depends(get_db),
             token=Depends(oauth2_scheme)):
    db_author = db.query(models.Author).filter(models.Author.name == author).first()
    if not db_author:
        raise HTTPException(status_code=404, detail="Author not found")

    # book.author_id = db_author.id

    return crud.create_book(db=db, book=book, author_id=db_author.id)


@app.delete("/library/{author}/deleteauthor")
def delete_author(author: Annotated[str, Path(min_length=3, max_length=30)], db: Session = Depends(get_db),
                  token=Depends(oauth2_scheme)):
    db_author = db.query(models.Author).filter(models.Author.name == author).first()
    if not db_author:
        return HTTPException(status_code=404, detail="Author not found")
    db.delete(db_author)
    db.commit()
    return {"message": f"Author '{author}' was successfully deleted"}


@app.get("/library/{author}/getbook", response_model=List[schemas.BookBase])
def getbook(author: Annotated[Optional[str], Path(min_length=3, max_length=10)], db: Session = Depends(get_db)):
    if author:
        db_author = db.query(models.Author).filter(models.Author.name == author).first()
        if not db_author:
            raise HTTPException(status_code=404, detail="Author not found")
        books = db.query(models.Book).filter(models.Book.author_id == db_author.id).all()
        return [schemas.BookBase(title=book.title, pages=book.pages) for book in books]
    books = db.query(models.Book).all()
    return [schemas.BookBase(title=book.title, pages=book.pages) for book in books]


@app.put("/library/{author}/updatebook/", response_model=schemas.BookBase)
def bookupdate(
        author: Annotated[str, Path(min_length=3, max_length=10)],
        title: str,
        new_book: schemas.BookCreate,
        db: Session = Depends(get_db),
        token=Depends(oauth2_scheme)
):
    db_author = db.query(models.Author).filter(models.Author.name == author).first()
    if not db_author:
        return HTTPException(status_code=404, detail="Author not found")
    book = db.query(models.Book).filter(models.Book.author_id == db_author.id, models.Book.title == title).first()
    if not book:
        return HTTPException(status_code=404, detail="Book not found")

    book.title = new_book.title
    book.pages = new_book.pages
    db.commit()
    db.refresh(book)

    return schemas.BookBase(title=book.title, pages=book.pages)


@app.delete("/library/{author}/deletebook")
def deletebook(author: Annotated[str, Path(min_length=3, max_length=10)],
               title: str,
               db: Session = Depends(get_db),
               token=Depends(oauth2_scheme)
               ):
    db_author = db.query(models.Author).filter(models.Author.name == author).first()
    if not db_author:
        return HTTPException(status_code=404, detail="Author is not found")
    db_book = db.query(models.Book).filter(models.Book.author_id == db_author.id, models.Book.title == title).first()
    if not db_book:
        return HTTPException(status_code=404, detail="Book not found")
    db.delete(db_book)
    db.commit()
    return {"message": f"{db_book.title} by {db_author} was succedfully deleted"}
    # if author in library:
    #     book = find_book_by_title(title, library[author])
    #     library[author].remove(book)
    #     # return {"library": library


@app.get("/", response_class=HTMLResponse)  # -> GET 127.0.0.1:8000
async def main_view(request: Request):
    return templates.TemplateResponse("library/main.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)  # -> GET 127.0.0.1:8000/register
async def register_view(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})


@app.post("/register", response_class=HTMLResponse)  # -> POST 127.0.0.1:8000/register
async def register_form(request: Request, username: str = Form(...), password: str = Form(...),
                        db: Session = Depends(get_db)):
    user_date = schemas.UserBase(username=username, password=password)
    error = ""
    try:
        await add_user(user_date, db)
    except HTTPException as exp:
        error = exp.detail
    return templates.TemplateResponse("auth/register.html", {"request": request, "error": error})


@app.get("/login", response_class=HTMLResponse)
async def login_view(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})


@app.post("/login")
async def login_form(request: Request, username: str = Form(...), password: str = Form(...),
                     db: Session = Depends(get_db)):
    form_data = OAuth2PasswordRequestForm(username=username, password=password)
    try:
        await token_get(form_data, db)
        return RedirectResponse(url="/", status_code=303)
    except HTTPException as e:
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": e.detail
        })


@app.get("/books")
def books_view(request: Request, author: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        books = getbook(author, db)
        return templates.TemplateResponse("library/books_view.html", {"request": request, "books": books})
    except HTTPException as e:
        return templates.TemplateResponse("library/books_view.html", {"request": request, "error": e.detail})


@app.get("/author/create")
def author_create_view(request: Request):
    return templates.TemplateResponse("library/author_create.html", {"request": request})


@app.post("/author/create")
async def author_create_form(request: Request, author: str = Form(...), db: Session = Depends(get_db)):
    try:
        author_scheme = schemas.AuthorBase(name=author)
    except ValidationError:
        return templates.TemplateResponse("library/author_create.html", {"request": request, "error": "Incorrect author name"})

    try:
        await add_author(author_scheme, db)
        return templates.TemplateResponse("library/author_create.html", {"request": request})
    except HTTPException as e:
        return templates.TemplateResponse("library/author_create.html", {"request": request, "error": e.detail})


@app.get("/book/create")
def book_create_view(request: Request):
    return templates.TemplateResponse("library/book_create.html", {"request": request})


@app.post("/book/create")
def book_create_form(request: Request, author: str = Form(...),
                     name: str = Form(...),
                     pages: int = Form(...),
                     db: Session = Depends(get_db)):
    book_scheme = schemas.BookCreate(title=name, pages=pages)
    try:
        add_book(author, book_scheme, db)
        return templates.TemplateResponse("library/book_create.html", {"request": request})
    except HTTPException as e:
        return templates.TemplateResponse("library/book_create.html", {"request": request, "error": e.detail})


@app.get("/book/update")
def book_create_view(request: Request):
    return templates.TemplateResponse("library/book_update.html", {"request": request})

@app.post("/book/update")
def book_update_form(request: Request, author: str = Form(...),
                     name: str = Form(...),
                     newname: str = Form(...),
                     newpages: str = Form(...),
                     db: Session = Depends(get_db)):
    book_scheme = schemas.BookCreate(title=name, pages=pages)
    try:
        new_book_scheme = schemas.BookCreate(title=newname, pages=newpages)
        bookupdate(author, name, new_book_scheme, db)
        return templates.TemplateResponse("library/book_update.html", {"request": request})
    except HTTPException as e:
        return templates.TemplateResponse("library/book_update.html", {"request": request, "error": e.detail})

@app.get("/book/delete")
def book_delete_view(request: Request):
    return templates.TemplateResponse("library/book_delete.html", {"request": request})


@app.post("/book/delete")
def book_delete_form(request: Request, author: str = Form(...),
                     name: str = Form(...),
                     db: Session = Depends(get_db)):
    try:
        deletebook(author=author, title=name, db=db)
        return templates.TemplateResponse("library/book_delete.html", {"request": request})
    except HTTPException as e:
        return templates.TemplateResponse("library/book_delete.html", {"request": request, "error": e.detail})

if __name__ == "__main__":
    import os
    os.system("uvicorn main:app --reload")
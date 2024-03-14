from contextlib import asynccontextmanager
from typing import Union, Optional, Annotated
from sqlmodel import Field, Session, SQLModel, create_engine, select
from fastapi import FastAPI, Depends, HTTPException
from fastapi.openapi.utils import get_openapi
from fastapi_neon import settings


class Todo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(index=True)

# only needed for psycopg 3 - replace postgresql
# with postgresql+psycopg in settings.DATABASE_URL
connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)


# recycle connections after 5 minutes
# to correspond with the compute scale down
engine = create_engine(
    connection_string, connect_args={"sslmode": "require"}, pool_recycle=300
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# The first part of the function, before the yield, will
# be executed before the application starts.
# https://fastapi.tiangolo.com/advanced/events/#lifespan-function
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating tables..")
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan, title="Hello World API with DB", 
    version="0.0.1",
    servers=[
        {
            "url": "http://0.0.0.0:8000", # ADD NGROK URL Here Before Creating GPT Action
            "description": "Development Server"
        }
        ])

def get_session():
    with Session(engine) as session:
        yield session


@app.get("/")
def read_root():
    return {"Name": "ToDo App",
            "Description": "Using Fast API and SQLModel to create a simple ToDo App",
            "Devlivery": "Dockerized FastAPI App with Postgres DB",
            "Author": "Azfar Suhail"}

@app.post("/todos/", response_model=Todo)
def create_todo(todo: Todo, session: Annotated[Session, Depends(get_session)]):
        session.add(todo)
        session.commit()
        session.refresh(todo)
        return todo


@app.get("/todos/", response_model=list[Todo])
def read_todos(session: Annotated[Session, Depends(get_session)]):
        todos = session.exec(select(Todo)).all()
        return todos

@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int, session: Session = Depends(get_session)):
    # Retrieve the todo from the database using the provided todo_id
    db_todo = session.exec(select(Todo).filter(Todo.id == todo_id)).first()
    
    # Check if the todo exists
    if db_todo is None:
        # If todo doesn't exist, raise a 404 HTTPException
        raise HTTPException(status_code=404, detail="Todo not found")
    
    # If todo exists, delete it from the database
    session.delete(db_todo)
    session.commit()
    
    # Return a success message
    return {"message": "Todo deleted"}

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Todo App with SQLModel and FastAPI",
        version="0.0.1",
        summary="This is a very custom OpenAPI schema",
        description="Welcome to the FastAPI Neon API documentation! Our API empowers developers to create lightning-fast and scalable APIs with ease. Leveraging the speed of FastAPI and the simplicity of SQLModel, developers can quickly define and interact with database models using pure Python code. With built-in support for asynchronous programming and automatic interactive documentation generation, building robust and efficient APIs has never been easier. Whether you're a seasoned developer or just starting out, FastAPI Neon API provides the tools and flexibility you need to bring your ideas to life. Dive in, explore our API, and start building amazing applications today! 🚀🐍",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://icons.veryicon.com/png/o/internet--web/internet-simple-icon/api-management.png"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
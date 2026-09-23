from app.db.session import SessionLocal


def get_db():
    db = SessionLocal()  # 创建数据库 session 对象
    try:
        yield db  # 把 db 交给 FastAPI
    finally:
        db.close()

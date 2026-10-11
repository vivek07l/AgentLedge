"""Create or promote the local marketplace admin account using console prompts."""
from getpass import getpass

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from src.auth.security import get_password_hash
from src.config import get_settings
from src.database.models import User


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        raise SystemExit("The database schema is not initialized. Apply the reviewed Alembic migrations first.")
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "is_admin" not in columns:
        raise SystemExit("The users.is_admin migration is missing. Apply the reviewed Alembic migrations first.")

    username = input("Admin username: ").strip()
    email = input("Admin email: ").strip()
    password = getpass("Admin password (12+ characters): ")
    confirm = getpass("Confirm password: ")
    if len(password) < 12 or password != confirm:
        raise SystemExit("Password must be at least 12 characters and both entries must match.")

    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(username=username, email=email, token_balance=0)
            db.add(user)
        user.email = email
        user.hashed_password = get_password_hash(password)
        user.is_active = True
        user.is_developer = False
        user.is_admin = True
        db.commit()
    print(f"Admin account '{username}' is ready. Use /admin/login or the admin sign-in page.")


if __name__ == "__main__":
    main()

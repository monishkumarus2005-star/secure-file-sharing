from app.database import engine
import sqlalchemy as sa
from sqlalchemy import inspect

def cleanup():
    with engine.connect() as conn:
        insp = inspect(engine)
        tables = insp.get_table_names()
        print(f"Current tables: {tables}")
        for t in tables:
            if t.startswith('_alembic_tmp_'):
                print(f"Dropping temporary table: {t}")
                conn.execute(sa.text(f"DROP TABLE {t}"))
        conn.commit()
    print("Cleanup complete.")

if __name__ == "__main__":
    cleanup()

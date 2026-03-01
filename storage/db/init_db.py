from __future__ import annotations

from .engine import engine
from .models import Base

def main():
    Base.metadata.create_all(bind=engine())
    print("DB initialized (tables created).")

if __name__ == "__main__":
    main()
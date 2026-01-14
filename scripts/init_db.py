"""
Initialize database and seed initial data.

Run this script once to set up the application:
    python scripts/init_db.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, engine, SessionLocal
from app.models import CryCategory
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def init_database():
    """Create all tables in the database."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created")


def seed_cry_categories():
    """Seed predefined cry categories."""
    db = SessionLocal()
    try:
        # Check if categories already exist
        existing = db.query(CryCategory).first()
        if existing:
            print("✓ Cry categories already exist, skipping seed")
            return

        # Define categories
        categories = [
            {"name": "hungry", "description": "Baby needs feeding"},
            {"name": "tired", "description": "Baby needs sleep"},
            {"name": "diaper", "description": "Diaper needs changing"},
            {"name": "pain", "description": "Baby is in pain or discomfort"},
            {"name": "comfort", "description": "Baby needs comfort or attention"},
            {"name": "overstimulated", "description": "Baby is overstimulated"},
            {"name": "other", "description": "Other reason"},
        ]

        # Insert categories
        print("Seeding cry categories...")
        for cat_data in categories:
            category = CryCategory(**cat_data)
            db.add(category)

        db.commit()
        print(f"✓ Seeded {len(categories)} cry categories")

    except Exception as e:
        print(f"✗ Error seeding categories: {e}")
        db.rollback()
    finally:
        db.close()


def create_directories():
    """Create necessary directories for file storage."""
    audio_dir = os.getenv("AUDIO_FILES_DIR", "./audio_files")
    chroma_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

    for directory in [audio_dir, chroma_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ Created directory: {directory}")
        else:
            print(f"✓ Directory already exists: {directory}")


def main():
    """Run all initialization tasks."""
    print("=" * 50)
    print("BabelFish Baby - Database Initialization")
    print("=" * 50)

    try:
        init_database()
        seed_cry_categories()
        create_directories()

        print("\n" + "=" * 50)
        print("✓ Initialization complete!")
        print("=" * 50)
        print("\nYou can now start the server:")
        print("  uvicorn main:app --reload")

    except Exception as e:
        print(f"\n✗ Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Initialize database and create necessary directories.

Run this script once to set up the application:
    python scripts/init_db.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, engine
from dotenv import load_dotenv
# Import all models so they register with Base.metadata
from app.models import User, CryInstance, ChatConversation, CryEmbeddingRaw, UserEmbeddingStats

# Load environment variables
load_dotenv()


def init_database():
    """Create all tables in the database."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created")


def create_directories():
    """Create necessary directories for file storage."""
    audio_dir = os.getenv("AUDIO_FILES_DIR", "./audio_files")
    chroma_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    photo_dir = os.getenv("PHOTO_FILES_DIR", "./photo_files")

    for directory in [audio_dir, chroma_dir, photo_dir]:
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

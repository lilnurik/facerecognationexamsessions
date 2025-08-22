import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///database.db')
    
    # Face recognition settings
    FACE_RECOGNITION_THRESHOLD = float(os.getenv('FACE_RECOGNITION_THRESHOLD', '0.45'))  # Slightly increased for better tolerance to appearance changes
    FACE_RECOGNITION_MODEL = os.getenv('FACE_RECOGNITION_MODEL', 'large')  # small, large
    
    # Admin settings
    ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', 'admin_secret_token_2023')
    
    # File paths
    FACE_ID_DOCS_PATH = os.getenv('FACE_ID_DOCS_PATH', 'Face ID docs')
    EXCEL_FILE_PATH = os.getenv('EXCEL_FILE_PATH', 'Face ID docs/list of students.xlsx')
    PHOTOS_PATH = os.getenv('PHOTOS_PATH', 'Face ID docs/photos')
    
    # Upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'uploads'
    
    # Performance settings
    USE_FAISS = os.getenv('USE_FAISS', 'false').lower() == 'true'
    USE_ANNOY = os.getenv('USE_ANNOY', 'false').lower() == 'true'
    
    # Embedding cache
    EMBEDDINGS_CACHE_PATH = os.getenv('EMBEDDINGS_CACHE_PATH', 'data/embeddings.npy')
    EMBEDDINGS_METADATA_PATH = os.getenv('EMBEDDINGS_METADATA_PATH', 'data/embeddings_metadata.json')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'app.log')
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
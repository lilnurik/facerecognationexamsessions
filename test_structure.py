"""
Simple test script to verify basic structure without heavy dependencies
"""
import os
import sqlite3
from datetime import datetime

def test_basic_structure():
    """Test basic project structure"""
    print("Testing project structure...")
    
    required_files = [
        'app.py',
        'models.py',
        'db.py',
        'config.py',
        'face_utils.py',
        'loader.py',
        'requirements.txt',
        'templates/index.html',
        'static/js/main.js',
        'benchmarks/test_lookup.py',
        'INSTALL.md'
    ]
    
    required_dirs = [
        'templates',
        'static',
        'static/js',
        'data',
        'benchmarks',
        'Face ID docs',
        'Face ID docs/photos'
    ]
    
    print("\nChecking required files:")
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
    
    print("\nChecking required directories:")
    for dir_path in required_dirs:
        if os.path.isdir(dir_path):
            print(f"✅ {dir_path}/")
        else:
            print(f"❌ {dir_path}/")

def test_config():
    """Test configuration loading"""
    print("\nTesting configuration...")
    try:
        from config import Config
        print(f"✅ Config loaded successfully")
        print(f"   - Database URL: {Config.DATABASE_URL}")
        print(f"   - Threshold: {Config.FACE_RECOGNITION_THRESHOLD}")
        print(f"   - Admin Token: {Config.ADMIN_TOKEN[:8]}...")
    except Exception as e:
        print(f"❌ Config error: {e}")

def test_models():
    """Test models definition"""
    print("\nTesting models...")
    try:
        from models import Student, Pass, LoadSession, Base
        print(f"✅ Models loaded successfully")
        print(f"   - Student model: {Student.__tablename__}")
        print(f"   - Pass model: {Pass.__tablename__}")
        print(f"   - LoadSession model: {LoadSession.__tablename__}")
    except Exception as e:
        print(f"❌ Models error: {e}")

def test_database():
    """Test database initialization"""
    print("\nTesting database...")
    try:
        from db import engine, init_db
        print(f"✅ Database engine created")
        print(f"   - Database URL: {engine.url}")
        
        # Test table creation
        init_db()
        print(f"✅ Database tables created")
        
        # Test basic operations
        from models import Student
        from db import get_db_session
        
        db = get_db_session()
        student_count = db.query(Student).count()
        db.close()
        
        print(f"✅ Database operations work (students: {student_count})")
        
    except Exception as e:
        print(f"❌ Database error: {e}")

def create_sample_excel_simple():
    """Create sample Excel file without pandas"""
    print("\nCreating sample Excel file structure...")
    
    # Create simple CSV first
    sample_data = [
        "Matricula,Lastname,Firstname,Lotin,Short,Group,Идентификатор,Date of birth,Passport number,File path",
        "2021001,Иванов,Александр,Alexandr,Саша,ИП-21-1,ID001,15.03.2003,AB1234567,student1.jpg",
        "2021002,Петров,Михаил,Mikhail,Миша,ИП-21-1,ID002,22.07.2003,CD7654321,student2.jpg",
        "2021003,Сидоров,Дмитрий,Dmitriy,Дима,ИП-21-2,ID003,10.12.2002,EF1122334,student3.jpg"
    ]
    
    os.makedirs('Face ID docs', exist_ok=True)
    
    with open('Face ID docs/sample_students.csv', 'w', encoding='utf-8') as f:
        f.write('\n'.join(sample_data))
    
    print("✅ Sample CSV created: Face ID docs/sample_students.csv")

def main():
    """Run all tests"""
    print("Face Recognition Exam Sessions - Basic Structure Test")
    print("=" * 60)
    
    test_basic_structure()
    test_config()
    test_models()
    test_database()
    create_sample_excel_simple()
    
    print("\n" + "=" * 60)
    print("Basic structure test completed!")
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Create Excel file: Face ID docs/list of students.xlsx")
    print("3. Add student photos to: Face ID docs/photos/")
    print("4. Run loader: python loader.py")
    print("5. Start server: python app.py")

if __name__ == '__main__':
    main()
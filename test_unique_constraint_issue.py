#!/usr/bin/env python3
"""
Test script to reproduce and verify the fix for UNIQUE constraint issue
This test doesn't require the full dependencies, just simulates the issue
"""
import os
import tempfile
import sqlite3
from datetime import datetime

def test_unique_constraint_issue():
    """Test to reproduce the UNIQUE constraint issue"""
    print("Testing UNIQUE constraint handling issue...")
    
    # Create a temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        # Create connection and tables
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create students table with UNIQUE constraint
        cursor.execute('''
            CREATE TABLE students (
                id INTEGER PRIMARY KEY,
                matricula TEXT UNIQUE NOT NULL,
                lastname TEXT NOT NULL,
                firstname TEXT NOT NULL,
                identifier TEXT UNIQUE,
                created_at TEXT
            )
        ''')
        
        # Insert first record
        cursor.execute('''
            INSERT INTO students (matricula, lastname, firstname, identifier, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', ('U16108', 'FAYZULLAYEV', 'IBROKHIM', '4908141706.0', datetime.utcnow().isoformat()))
        
        conn.commit()
        print("✅ First record inserted successfully")
        
        # Try to insert duplicate record (this should fail)
        try:
            cursor.execute('''
                INSERT INTO students (matricula, lastname, firstname, identifier, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', ('U16108', 'FAYZULLAYEV', 'IBROKHIM', '4908141706.0', datetime.utcnow().isoformat()))
            conn.commit()
            print("❌ Duplicate insert should have failed!")
            return False
        except sqlite3.IntegrityError as e:
            print(f"✅ Expected UNIQUE constraint error: {e}")
            # Simulate NOT calling rollback (the bug)
            # In SQLAlchemy, this would put the session in dirty state
        
        # Try to insert a different record (this should work if we handle rollback properly)
        try:
            cursor.execute('''
                INSERT INTO students (matricula, lastname, firstname, identifier, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', ('U16109', 'DIFFERENT', 'STUDENT', '4908141707.0', datetime.utcnow().isoformat()))
            conn.commit()
            print("✅ Different record inserted successfully after constraint error")
            return True
        except Exception as e:
            print(f"❌ Failed to insert different record after constraint error: {e}")
            return False
        
    finally:
        conn.close()
        os.unlink(db_path)

def test_sqlalchemy_session_simulation():
    """Simulate the SQLAlchemy session issue"""
    print("\nSimulating SQLAlchemy session rollback issue...")
    
    class MockSession:
        def __init__(self):
            self.dirty = False
            self.records = []
        
        def add(self, record):
            if self.dirty:
                raise Exception("This Session's transaction has been rolled back due to a previous exception during flush. To begin a new transaction with this Session, first issue Session.rollback().")
            # Simulate UNIQUE constraint check
            for existing in self.records:
                if existing.get('identifier') == record.get('identifier'):
                    self.dirty = True
                    raise Exception("(sqlite3.IntegrityError) UNIQUE constraint failed: students.identifier")
            self.records.append(record)
        
        def commit(self):
            if self.dirty:
                raise Exception("This Session's transaction has been rolled back due to a previous exception during flush.")
            # Simulate successful commit
            pass
        
        def rollback(self):
            self.dirty = False
    
    # Test without rollback (current bug)
    print("Testing WITHOUT proper rollback (reproduces the bug):")
    session = MockSession()
    
    # First record - should work
    try:
        session.add({'identifier': '4908141706.0', 'name': 'Student 1'})
        session.commit()
        print("✅ First record added")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    # Duplicate record - should fail with constraint error
    try:
        session.add({'identifier': '4908141706.0', 'name': 'Student 1 Duplicate'})
        session.commit()
        print("❌ Duplicate should have failed!")
    except Exception as e:
        print(f"✅ Expected constraint error: {type(e).__name__}")
        # BUG: Not calling session.rollback() here
    
    # Different record - should fail because session is dirty
    try:
        session.add({'identifier': '4908141707.0', 'name': 'Student 2'})
        session.commit()
        print("❌ This should have failed due to dirty session!")
    except Exception as e:
        print(f"✅ Expected session dirty error: {type(e).__name__}")
    
    # Test WITH proper rollback (the fix)
    print("\nTesting WITH proper rollback (demonstrates the fix):")
    session = MockSession()
    
    # First record - should work
    try:
        session.add({'identifier': '4908141706.0', 'name': 'Student 1'})
        session.commit()
        print("✅ First record added")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    # Duplicate record - should fail with constraint error
    try:
        session.add({'identifier': '4908141706.0', 'name': 'Student 1 Duplicate'})
        session.commit()
        print("❌ Duplicate should have failed!")
    except Exception as e:
        print(f"✅ Expected constraint error: {type(e).__name__}")
        # FIX: Call session.rollback() to reset dirty state
        session.rollback()
    
    # Different record - should now work because session is clean
    try:
        session.add({'identifier': '4908141707.0', 'name': 'Student 2'})
        session.commit()
        print("✅ Different record added successfully after rollback!")
        return True
    except Exception as e:
        print(f"❌ Unexpected error after rollback: {e}")
        return False

def main():
    """Run all tests"""
    print("UNIQUE Constraint Session Rollback Issue Test")
    print("=" * 60)
    
    success1 = test_unique_constraint_issue()
    success2 = test_sqlalchemy_session_simulation()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("✅ All tests passed! The issue is reproduced and fix is demonstrated.")
    else:
        print("❌ Some tests failed.")
    
    print("\nThe fix needed in loader.py:")
    print("Add 'db.rollback()' in the exception handler at line 188")

if __name__ == '__main__':
    main()
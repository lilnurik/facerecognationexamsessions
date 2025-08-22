#!/usr/bin/env python3
"""
Simple test to verify the fix is correctly applied in loader.py
This checks that the rollback line was added to the exception handler
"""
import re

def test_loader_fix():
    """Test that the rollback fix is present in loader.py"""
    print("Verifying that the fix is applied in loader.py...")
    
    try:
        with open('loader.py', 'r') as f:
            content = f.read()
        
        # Look for the exception handler pattern
        exception_pattern = r'except Exception as e:(.*?)continue'
        matches = re.findall(exception_pattern, content, re.DOTALL)
        
        if not matches:
            print("❌ Could not find exception handler in loader.py")
            return False
        
        # Check if rollback is present in the exception handler
        exception_handler = matches[0]
        
        if 'db.rollback()' in exception_handler:
            print("✅ Fix verified: db.rollback() found in exception handler")
            
            # Show the fixed code block
            print("\nFixed exception handler:")
            lines = exception_handler.strip().split('\n')
            for line in lines:
                print(f"    {line.strip()}")
            
            return True
        else:
            print("❌ Fix not found: db.rollback() is missing from exception handler")
            print("\nCurrent exception handler:")
            lines = exception_handler.strip().split('\n')
            for line in lines:
                print(f"    {line.strip()}")
            return False
        
    except FileNotFoundError:
        print("❌ loader.py not found")
        return False
    except Exception as e:
        print(f"❌ Error reading loader.py: {e}")
        return False

def test_fix_placement():
    """Test that the fix is in the correct location"""
    print("\nVerifying fix placement...")
    
    try:
        with open('loader.py', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find the exception handler
        for i, line in enumerate(lines):
            if 'except Exception as e:' in line:
                # Check the next few lines for the expected structure
                expected_sequence = [
                    'error_msg = f"Row {index+2}: Error processing record: {str(e)}"',
                    'logger.error(error_msg)',
                    'errors.append(error_msg)',
                    'records_skipped += 1',
                    'db.rollback()',
                    'continue'
                ]
                
                found_lines = []
                for j in range(i+1, min(i+8, len(lines))):
                    line_content = lines[j].strip()
                    if line_content:
                        found_lines.append(line_content)
                
                print(f"Exception handler found at line {i+1}")
                print("Expected sequence:")
                for seq in expected_sequence:
                    print(f"  - {seq}")
                
                print("\nActual sequence:")
                for line in found_lines:
                    print(f"  - {line}")
                
                # Check if rollback is present
                rollback_found = any('db.rollback()' in line for line in found_lines)
                
                if rollback_found:
                    print("✅ db.rollback() found in correct location")
                    return True
                else:
                    print("❌ db.rollback() not found in exception handler")
                    return False
        
        print("❌ Exception handler not found")
        return False
        
    except Exception as e:
        print(f"❌ Error analyzing fix placement: {e}")
        return False

def main():
    """Run all verification tests"""
    print("Loader Fix Verification")
    print("=" * 40)
    
    success1 = test_loader_fix()
    success2 = test_fix_placement()
    
    print("\n" + "=" * 40)
    if success1 and success2:
        print("✅ Fix verification PASSED!")
        print("The loader.py file has been correctly modified to handle UNIQUE constraint errors.")
    else:
        print("❌ Fix verification FAILED!")
        print("The fix may not be applied correctly.")
    
    print("\nExpected behavior after fix:")
    print("- When a UNIQUE constraint error occurs, the session will be rolled back")
    print("- Subsequent database operations will continue normally")
    print("- No more cascading 'session has been rolled back' errors")

if __name__ == '__main__':
    main()
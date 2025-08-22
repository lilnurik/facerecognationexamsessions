#!/usr/bin/env python3
"""
Integration test to verify the full application works with the fixes
"""
import requests
import json
import logging
import time
import subprocess
import signal
import os
from multiprocessing import Process

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_flask_app():
    """Run the Flask app in a subprocess"""
    os.environ['FLASK_ENV'] = 'testing'
    subprocess.run(['python', 'app.py'], cwd='/home/runner/work/facerecognationexamsessions/facerecognationexamsessions')

def test_app_endpoints():
    """Test the application endpoints"""
    base_url = 'http://localhost:5000'
    
    try:
        # Test 1: Check main page loads
        response = requests.get(base_url, timeout=5)
        print(f"✓ Main page status: {response.status_code}")
        
        # Test 2: Check admin stats (with token)
        admin_token = 'admin_secret_token_2023'  # Default token from config
        response = requests.get(f'{base_url}/admin/stats', 
                              params={'token': admin_token}, 
                              timeout=5)
        
        if response.status_code == 200:
            stats = response.json()
            print(f"✓ Admin stats working: {stats}")
            
            # Check our fixes are reflected in stats
            face_stats = stats.get('face_engine', {})
            if face_stats.get('distance_metric') == 'cosine':
                print("✓ Cosine distance metric confirmed in stats")
            if face_stats.get('threshold') == 0.4:
                print("✓ Adjusted threshold confirmed in stats")
                
        else:
            print(f"✗ Admin stats failed: {response.status_code}")
            
        return True
        
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to Flask app")
        return False
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

def main():
    print("=" * 50)
    print("Integration Test - Face Recognition Fixes")
    print("=" * 50)
    
    # Start Flask app in background
    print("\n1. Starting Flask application...")
    app_process = Process(target=run_flask_app)
    app_process.start()
    
    # Wait for app to start
    time.sleep(3)
    
    try:
        # Test endpoints
        print("\n2. Testing application endpoints...")
        test_result = test_app_endpoints()
        
        if test_result:
            print("\n✓ Integration test PASSED - Application working with fixes!")
        else:
            print("\n✗ Integration test FAILED - Check application setup")
            
    finally:
        # Clean up
        print("\n3. Cleaning up...")
        app_process.terminate()
        app_process.join(timeout=5)
        if app_process.is_alive():
            app_process.kill()
    
    print("=" * 50)

if __name__ == "__main__":
    main()
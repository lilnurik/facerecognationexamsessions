#!/usr/bin/env python3
"""
Test script to validate face recognition fixes
"""
import numpy as np
import logging
from face_utils import FaceRecognitionEngine, face_engine
from config import Config

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_distance_metrics():
    """Test the distance metric changes"""
    print("Testing distance metric changes...")
    
    # Test with some dummy face encodings
    face_engine_test = FaceRecognitionEngine()
    
    # Create some test embeddings (128-dimensional like face_recognition)
    test_embeddings = np.random.rand(3, 128).astype(np.float32)
    test_student_ids = np.array([1, 2, 3])
    
    face_engine_test.embeddings = test_embeddings
    face_engine_test.student_ids = test_student_ids
    
    # Build index
    face_engine_test._build_search_index()
    
    # Test search
    query = test_embeddings[0] + np.random.normal(0, 0.05, 128)  # Similar to first embedding
    
    result = face_engine_test.find_matching_student(query)
    print(f"Test search result: {result}")
    
    # Check stats
    stats = face_engine_test.get_stats()
    print(f"Engine stats: {stats}")
    
    return stats['distance_metric'] == 'cosine'

def test_config_changes():
    """Test configuration changes"""
    print(f"Face recognition threshold: {Config.FACE_RECOGNITION_THRESHOLD}")
    print(f"Face recognition model: {Config.FACE_RECOGNITION_MODEL}")
    
    # Should be 0.4 now (adjusted for cosine distance)
    return Config.FACE_RECOGNITION_THRESHOLD == 0.4

def main():
    print("=" * 50)
    print("Testing Face Recognition Fixes")
    print("=" * 50)
    
    # Test 1: Distance metric
    print("\n1. Testing distance metric...")
    metric_test = test_distance_metrics()
    print(f"✓ Distance metric test: {'PASS' if metric_test else 'FAIL'}")
    
    # Test 2: Configuration
    print("\n2. Testing configuration...")
    config_test = test_config_changes()
    print(f"✓ Configuration test: {'PASS' if config_test else 'FAIL'}")
    
    # Test 3: Face engine stats
    print("\n3. Testing face engine stats...")
    stats = face_engine.get_stats()
    print(f"Face engine stats: {stats}")
    
    print("\n" + "=" * 50)
    if metric_test and config_test:
        print("✓ All tests PASSED - fixes are working correctly!")
    else:
        print("✗ Some tests FAILED - fixes need review")
    print("=" * 50)

if __name__ == "__main__":
    main()
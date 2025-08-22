import time
import numpy as np
import logging
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics.pairwise import euclidean_distances
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from models import Student
from db import get_db_session

logger = logging.getLogger(__name__)

def generate_random_embeddings(n_embeddings, embedding_dim=128):
    """Generate random face embeddings for testing"""
    return np.random.randn(n_embeddings, embedding_dim).astype(np.float32)

def test_bruteforce_search(embeddings, query_embeddings, threshold=0.5):
    """Test brute force search performance"""
    times = []
    
    for query in query_embeddings:
        start_time = time.time()
        
        # Calculate distances
        distances = euclidean_distances([query], embeddings)[0]
        
        # Find best match
        min_idx = np.argmin(distances)
        min_distance = distances[min_idx]
        
        # Check threshold
        match_found = min_distance <= threshold
        
        end_time = time.time()
        times.append(end_time - start_time)
    
    return times, np.mean(times), np.std(times)

def test_sklearn_search(embeddings, query_embeddings, threshold=0.4):
    """Test sklearn NearestNeighbors search performance"""
    # Build index with cosine distance (matching face_utils.py)
    start_build = time.time()
    nn_model = NearestNeighbors(n_neighbors=1, algorithm='auto', metric='cosine')
    nn_model.fit(embeddings)
    build_time = time.time() - start_build
    
    times = []
    
    for query in query_embeddings:
        start_time = time.time()
        
        # Find nearest neighbor
        distances, indices = nn_model.kneighbors([query])
        distance = distances[0][0]
        
        # Check threshold
        match_found = distance <= threshold
        
        end_time = time.time()
        times.append(end_time - start_time)
    
    return times, np.mean(times), np.std(times), build_time

def test_with_real_data():
    """Test with real data from database"""
    db = get_db_session()
    try:
        students = db.query(Student).filter(Student.face_encoding.isnot(None)).all()
        
        if len(students) < 10:
            print("Not enough real data for testing (need at least 10 students)")
            return None
        
        # Load real embeddings
        embeddings = []
        for student in students:
            try:
                import pickle
                encoding = pickle.loads(student.face_encoding)
                embeddings.append(encoding)
            except Exception as e:
                continue
        
        if len(embeddings) < 10:
            print("Not enough valid encodings for testing")
            return None
        
        embeddings = np.array(embeddings)
        
        # Use some real embeddings as queries
        n_queries = min(100, len(embeddings) // 2)
        query_indices = np.random.choice(len(embeddings), n_queries, replace=False)
        query_embeddings = embeddings[query_indices]
        
        print(f"Testing with {len(embeddings)} real embeddings, {len(query_embeddings)} queries")
        
        return embeddings, query_embeddings
        
    finally:
        db.close()

def run_benchmark():
    """Run comprehensive benchmark"""
    print("Face Recognition Search Benchmark")
    print("=" * 50)
    
    # Test configurations
    test_sizes = [100, 500, 1000, 2500, 5000]
    embedding_dim = 128
    n_queries = 100
    threshold = Config.FACE_RECOGNITION_THRESHOLD
    
    print(f"Threshold: {threshold}")
    print(f"Number of queries per test: {n_queries}")
    print(f"Embedding dimension: {embedding_dim}")
    print()
    
    # Test with real data first
    print("1. Testing with real data from database:")
    print("-" * 40)
    
    real_data = test_with_real_data()
    if real_data:
        embeddings, query_embeddings = real_data
        
        # Test brute force
        times, mean_time, std_time = test_bruteforce_search(embeddings, query_embeddings, threshold)
        print(f"Brute force search ({len(embeddings)} embeddings):")
        print(f"  Mean time: {mean_time*1000:.2f} ms")
        print(f"  Std time: {std_time*1000:.2f} ms")
        print(f"  Max time: {max(times)*1000:.2f} ms")
        
        # Test sklearn
        times, mean_time, std_time, build_time = test_sklearn_search(embeddings, query_embeddings, threshold)
        print(f"Sklearn NearestNeighbors ({len(embeddings)} embeddings):")
        print(f"  Build time: {build_time*1000:.2f} ms")
        print(f"  Mean query time: {mean_time*1000:.2f} ms")
        print(f"  Std time: {std_time*1000:.2f} ms")
        print(f"  Max time: {max(times)*1000:.2f} ms")
        print()
    
    # Test with synthetic data
    print("2. Testing with synthetic data:")
    print("-" * 40)
    
    for n_embeddings in test_sizes:
        print(f"\nTesting with {n_embeddings} embeddings:")
        
        # Generate test data
        embeddings = generate_random_embeddings(n_embeddings, embedding_dim)
        query_embeddings = generate_random_embeddings(n_queries, embedding_dim)
        
        # Test brute force search
        times, mean_time, std_time = test_bruteforce_search(embeddings, query_embeddings, threshold)
        
        print(f"  Brute force search:")
        print(f"    Mean: {mean_time*1000:.2f} ms")
        print(f"    Std:  {std_time*1000:.2f} ms")
        print(f"    Max:  {max(times)*1000:.2f} ms")
        
        # Test sklearn NearestNeighbors
        times, mean_time, std_time, build_time = test_sklearn_search(embeddings, query_embeddings, threshold)
        
        print(f"  Sklearn NearestNeighbors:")
        print(f"    Build: {build_time*1000:.2f} ms")
        print(f"    Mean:  {mean_time*1000:.2f} ms")
        print(f"    Std:   {std_time*1000:.2f} ms")
        print(f"    Max:   {max(times)*1000:.2f} ms")
        
        # Check if performance meets requirements
        if mean_time > 0.1:  # 100ms threshold
            print(f"    ⚠️  Performance warning: {mean_time*1000:.2f} ms > 100 ms")
        else:
            print(f"    ✅ Performance OK: {mean_time*1000:.2f} ms < 100 ms")
    
    print("\n" + "=" * 50)
    print("Benchmark Results Summary:")
    print()
    print("For 2500 embeddings (target size):")
    
    # Final test with target size
    n_embeddings = 2500
    embeddings = generate_random_embeddings(n_embeddings, embedding_dim)
    query_embeddings = generate_random_embeddings(n_queries, embedding_dim)
    
    # Brute force
    times, mean_time, std_time = test_bruteforce_search(embeddings, query_embeddings, threshold)
    print(f"Brute force: {mean_time*1000:.2f} ms average")
    
    # Sklearn
    times, mean_time, std_time, build_time = test_sklearn_search(embeddings, query_embeddings, threshold)
    print(f"Sklearn NN: {mean_time*1000:.2f} ms average")
    
    print()
    print("Recommendations:")
    if mean_time <= 0.1:
        print("✅ Current implementation should work well for 2500 students")
        print("   No need for additional optimizations like FAISS/Annoy")
    else:
        print("⚠️  Current implementation may be slow for 2500 students")
        print("   Consider using FAISS or Annoy for better performance:")
        print()
        print("   FAISS installation:")
        print("   pip install faiss-cpu  # or faiss-gpu for GPU support")
        print()
        print("   Annoy installation:")
        print("   pip install annoy")
        print()
        print("   Set USE_FAISS=true or USE_ANNOY=true in config to enable")

def suggest_faiss_implementation():
    """Suggest FAISS implementation for better performance"""
    print("\nOptional FAISS Implementation Example:")
    print("-" * 40)
    print("""
# Install FAISS
pip install faiss-cpu  # or faiss-gpu

# Add to face_utils.py:
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

class FAISSFaceEngine(FaceRecognitionEngine):
    def _build_search_index(self):
        if not FAISS_AVAILABLE or not Config.USE_FAISS:
            return super()._build_search_index()
        
        if self.embeddings is None or len(self.embeddings) == 0:
            return
        
        # Build FAISS index
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(self.embeddings.astype('float32'))
    
    def find_matching_student(self, query_encoding):
        if not hasattr(self, 'index') or query_encoding is None:
            return None, None
        
        # Search with FAISS
        distances, indices = self.index.search(
            query_encoding.reshape(1, -1).astype('float32'), 1
        )
        
        distance = distances[0][0]
        if distance <= self.threshold:
            student_id = self.student_ids[indices[0][0]]
            return student_id, distance
        
        return None, None

# To enable FAISS, set in config.py or environment:
# USE_FAISS = True
""")

if __name__ == '__main__':
    run_benchmark()
    suggest_faiss_implementation()
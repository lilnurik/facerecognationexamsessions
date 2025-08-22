import numpy as np
import face_recognition
import cv2
from PIL import Image
import io
import logging
import os
import json
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics.pairwise import cosine_similarity
from config import Config
from models import Student
import pickle

logger = logging.getLogger(__name__)

class FaceRecognitionEngine:
    def __init__(self):
        self.embeddings = None
        self.student_ids = None
        self.nn_model = None
        self.threshold = Config.FACE_RECOGNITION_THRESHOLD
        
    def extract_face_encoding(self, image_path_or_array):
        """
        Extract face encoding from image file or numpy array
        Returns: (encoding, num_faces_found) or (None, 0) if no face found
        """
        try:
            # Load image
            if isinstance(image_path_or_array, str):
                if not os.path.exists(image_path_or_array):
                    logger.error(f"Image file not found: {image_path_or_array}")
                    return None, 0
                image = face_recognition.load_image_file(image_path_or_array)
            else:
                image = image_path_or_array
            
            # Try multiple approaches for face detection
            face_locations = None
            num_faces = 0
            
            # First try with default model
            try:
                face_locations = face_recognition.face_locations(image, model=Config.FACE_RECOGNITION_MODEL)
                num_faces = len(face_locations)
                logger.debug(f"Face detection with {Config.FACE_RECOGNITION_MODEL} model: found {num_faces} faces")
            except Exception as e:
                logger.warning(f"Face detection with {Config.FACE_RECOGNITION_MODEL} model failed: {e}")
            
            # If no faces found and using 'large' model, try 'hog' model (faster, different approach)
            if num_faces == 0 and Config.FACE_RECOGNITION_MODEL == 'large':
                try:
                    face_locations = face_recognition.face_locations(image, model='hog')
                    num_faces = len(face_locations)
                    logger.debug(f"Face detection with hog model: found {num_faces} faces")
                except Exception as e:
                    logger.warning(f"Face detection with hog model failed: {e}")
            
            # If still no faces, try with upsampling
            if num_faces == 0:
                try:
                    face_locations = face_recognition.face_locations(image, number_of_times_to_upsample=1, model='hog')
                    num_faces = len(face_locations)
                    logger.debug(f"Face detection with upsampling: found {num_faces} faces")
                except Exception as e:
                    logger.warning(f"Face detection with upsampling failed: {e}")
            
            if num_faces == 0:
                logger.warning("No faces found in image after trying multiple detection methods")
                return None, 0
            
            if num_faces > 1:
                logger.warning(f"Multiple faces found ({num_faces}), using the first one")
            
            # Extract encodings
            face_encodings = face_recognition.face_encodings(image, face_locations, model=Config.FACE_RECOGNITION_MODEL)
            
            if len(face_encodings) == 0:
                logger.warning("No face encodings extracted")
                return None, 0
                
            # Return first encoding
            encoding = face_encodings[0]
            logger.debug(f"Successfully extracted face encoding with shape: {encoding.shape}")
            return encoding, num_faces
            
        except Exception as e:
            logger.error(f"Error extracting face encoding: {e}")
            return None, 0
    
    def process_uploaded_image(self, file_data):
        """
        Process uploaded image data (bytes)
        Returns: (encoding, num_faces_found) or (None, 0)
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(file_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to numpy array
            image_array = np.array(image)
            
            return self.extract_face_encoding(image_array)
            
        except Exception as e:
            logger.error(f"Error processing uploaded image: {e}")
            return None, 0
    
    def load_embeddings_cache(self):
        """Load embeddings cache from disk"""
        try:
            if os.path.exists(Config.EMBEDDINGS_CACHE_PATH) and os.path.exists(Config.EMBEDDINGS_METADATA_PATH):
                self.embeddings = np.load(Config.EMBEDDINGS_CACHE_PATH)
                with open(Config.EMBEDDINGS_METADATA_PATH, 'r') as f:
                    metadata = json.load(f)
                self.student_ids = np.array(metadata['student_ids'])
                
                logger.info(f"Loaded {len(self.embeddings)} embeddings from cache")
                self._build_search_index()
                return True
        except Exception as e:
            logger.error(f"Error loading embeddings cache: {e}")
        
        return False
    
    def save_embeddings_cache(self):
        """Save embeddings cache to disk"""
        try:
            if self.embeddings is not None and self.student_ids is not None:
                os.makedirs(os.path.dirname(Config.EMBEDDINGS_CACHE_PATH), exist_ok=True)
                
                np.save(Config.EMBEDDINGS_CACHE_PATH, self.embeddings)
                
                metadata = {
                    'student_ids': self.student_ids.tolist(),
                    'count': len(self.embeddings),
                    'threshold': self.threshold
                }
                
                with open(Config.EMBEDDINGS_METADATA_PATH, 'w') as f:
                    json.dump(metadata, f)
                
                logger.info(f"Saved {len(self.embeddings)} embeddings to cache")
                return True
        except Exception as e:
            logger.error(f"Error saving embeddings cache: {e}")
        
        return False
    
    def rebuild_index(self, db_session):
        """Rebuild embeddings index from database"""
        try:
            students = db_session.query(Student).filter(Student.face_encoding.isnot(None)).all()
            
            if not students:
                logger.warning("No students with face encodings found")
                self.embeddings = None
                self.student_ids = None
                self.nn_model = None
                return False
            
            embeddings_list = []
            student_ids_list = []
            
            for student in students:
                try:
                    # Deserialize face encoding
                    encoding = pickle.loads(student.face_encoding)
                    embeddings_list.append(encoding)
                    student_ids_list.append(student.id)
                except Exception as e:
                    logger.error(f"Error loading encoding for student {student.id}: {e}")
                    continue
            
            if not embeddings_list:
                logger.error("No valid encodings found")
                return False
            
            self.embeddings = np.array(embeddings_list)
            self.student_ids = np.array(student_ids_list)
            
            logger.info(f"Rebuilt index with {len(self.embeddings)} embeddings")
            
            self._build_search_index()
            self.save_embeddings_cache()
            
            return True
            
        except Exception as e:
            logger.error(f"Error rebuilding index: {e}")
            return False
    
    def _build_search_index(self):
        """Build search index for fast lookup"""
        if self.embeddings is None or len(self.embeddings) == 0:
            self.nn_model = None
            return
        
        try:
            # Use NearestNeighbors for fast search with cosine distance
            # face_recognition uses cosine similarity, so we should use cosine distance
            self.nn_model = NearestNeighbors(
                n_neighbors=1,
                algorithm='auto',
                metric='cosine'
            )
            self.nn_model.fit(self.embeddings)
            
            logger.info("Built search index successfully with cosine metric")
        except Exception as e:
            logger.error(f"Error building search index: {e}")
            self.nn_model = None
    
    def find_matching_student(self, query_encoding):
        """
        Find matching student for given face encoding
        Returns: (student_id, distance) or (None, None) if no match
        """
        if self.embeddings is None or self.nn_model is None or query_encoding is None:
            logger.warning("Cannot search: embeddings=%s, nn_model=%s, query_encoding=%s", 
                         self.embeddings is not None, self.nn_model is not None, query_encoding is not None)
            return None, None
        
        try:
            # Find nearest neighbor
            distances, indices = self.nn_model.kneighbors([query_encoding])
            
            distance = distances[0][0]
            index = indices[0][0]
            
            logger.info(f"Face search: distance={distance:.4f}, threshold={self.threshold}, index={index}")
            
            # Check if distance is within threshold
            if distance <= self.threshold:
                student_id = self.student_ids[index]
                logger.info(f"Match found: student_id={student_id}, distance={distance:.4f}")
                return student_id, distance
            else:
                logger.info(f"No match found: best distance={distance:.4f}, threshold={self.threshold}")
                return None, None
                
        except Exception as e:
            logger.error(f"Error finding matching student: {e}")
            return None, None
    
    def get_stats(self):
        """Get statistics about the recognition engine"""
        return {
            'total_embeddings': len(self.embeddings) if self.embeddings is not None else 0,
            'threshold': self.threshold,
            'index_ready': self.nn_model is not None,
            'cache_exists': os.path.exists(Config.EMBEDDINGS_CACHE_PATH),
            'distance_metric': 'cosine',  # Now using cosine distance
            'face_model': Config.FACE_RECOGNITION_MODEL
        }

# Global face recognition engine instance
face_engine = FaceRecognitionEngine()
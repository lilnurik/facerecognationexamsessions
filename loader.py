import pandas as pd
import os
import logging
import click
import json
import pickle
from datetime import datetime
from config import Config
from models import Student, LoadSession
from db import get_db_session
from face_utils import face_engine

logger = logging.getLogger(__name__)

class ExcelLoader:
    def __init__(self):
        self.required_columns = [
            'Matricula', 'Lastname', 'Firstname', 'Lotin', 'Short', 
            'Group', 'Идентификатор', 'Date of birth', 'Passport number', 'File path'
        ]
    
    def validate_excel_structure(self, df):
        """Validate that Excel has all required columns"""
        missing_columns = []
        for col in self.required_columns:
            if col not in df.columns:
                missing_columns.append(col)
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        return True
    
    def resolve_image_path(self, file_path):
        """Resolve image path (absolute or relative to project/photos)"""
        if os.path.isabs(file_path):
            return file_path if os.path.exists(file_path) else None
        
        # Try relative to project root
        project_path = os.path.join(os.getcwd(), file_path)
        if os.path.exists(project_path):
            return project_path
        
        # Try relative to Face ID docs/photos
        photos_path = os.path.join(Config.PHOTOS_PATH, file_path)
        if os.path.exists(photos_path):
            return photos_path
        
        # Try just the filename in photos directory
        filename = os.path.basename(file_path)
        photos_filename_path = os.path.join(Config.PHOTOS_PATH, filename)
        if os.path.exists(photos_filename_path):
            return photos_filename_path
        
        return None
    
    def load_from_excel(self, excel_path, force=False):
        """
        Load students from Excel file
        Returns: LoadSession object with results
        """
        db = get_db_session()
        
        # Create load session
        load_session = LoadSession(
            filename=excel_path,
            started_at=datetime.utcnow(),
            status='running'
        )
        db.add(load_session)
        db.commit()
        
        errors = []
        records_processed = 0
        records_added = 0
        records_skipped = 0
        
        try:
            # Read Excel file
            if not os.path.exists(excel_path):
                raise FileNotFoundError(f"Excel file not found: {excel_path}")
            
            df = pd.read_excel(excel_path)
            logger.info(f"Loaded Excel with {len(df)} rows")
            
            # Validate structure
            self.validate_excel_structure(df)
            
            # Process each row
            for index, row in df.iterrows():
                records_processed += 1
                
                try:
                    # Check for required fields
                    matricula = str(row['Matricula']).strip() if pd.notna(row['Matricula']) else ''
                    identifier = str(row['Идентификатор']).strip() if pd.notna(row['Идентификатор']) else ''
                    
                    if not matricula and not identifier:
                        error_msg = f"Row {index+2}: Missing both Matricula and Идентификатор"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        records_skipped += 1
                        continue
                    
                    # Check if student already exists
                    existing_student = None
                    if matricula:
                        existing_student = db.query(Student).filter_by(matricula=matricula).first()
                    if not existing_student and identifier:
                        existing_student = db.query(Student).filter_by(identifier=identifier).first()
                    
                    if existing_student and not force:
                        logger.info(f"Row {index+2}: Student already exists (matricula={matricula}, identifier={identifier})")
                        records_skipped += 1
                        continue
                    
                    # Resolve image path
                    file_path = str(row['File path']).strip() if pd.notna(row['File path']) else ''
                    if not file_path:
                        error_msg = f"Row {index+2}: Missing file path"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        records_skipped += 1
                        continue
                    
                    resolved_path = self.resolve_image_path(file_path)
                    if not resolved_path:
                        error_msg = f"Row {index+2}: Image file not found: {file_path}"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        records_skipped += 1
                        continue
                    
                    # Extract face encoding
                    encoding, num_faces = face_engine.extract_face_encoding(resolved_path)
                    if encoding is None:
                        error_msg = f"Row {index+2}: No face found in image: {resolved_path}"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        records_skipped += 1
                        continue
                    
                    if num_faces > 1:
                        warning_msg = f"Row {index+2}: Multiple faces found ({num_faces}), using first one"
                        logger.warning(warning_msg)
                        errors.append(warning_msg)
                    
                    # Prepare student data
                    student_data = {
                        'matricula': matricula or None,
                        'lastname': str(row['Lastname']).strip() if pd.notna(row['Lastname']) else '',
                        'firstname': str(row['Firstname']).strip() if pd.notna(row['Firstname']) else '',
                        'lotin': str(row['Lotin']).strip() if pd.notna(row['Lotin']) else None,
                        'short': str(row['Short']).strip() if pd.notna(row['Short']) else None,
                        'group_name': str(row['Group']).strip() if pd.notna(row['Group']) else None,
                        'identifier': identifier or None,
                        'date_of_birth': str(row['Date of birth']).strip() if pd.notna(row['Date of birth']) else None,
                        'passport_number': str(row['Passport number']).strip() if pd.notna(row['Passport number']) else None,
                        'file_path': resolved_path,
                        'face_encoding': pickle.dumps(encoding),
                        'updated_at': datetime.utcnow()
                    }
                    
                    # Create or update student
                    if existing_student and force:
                        # Update existing
                        for key, value in student_data.items():
                            setattr(existing_student, key, value)
                        logger.info(f"Row {index+2}: Updated student {matricula or identifier}")
                    else:
                        # Create new
                        student = Student(**student_data)
                        db.add(student)
                        logger.info(f"Row {index+2}: Added student {matricula or identifier}")
                    
                    records_added += 1
                    
                    # Commit every 50 records
                    if records_processed % 50 == 0:
                        db.commit()
                        logger.info(f"Processed {records_processed} records...")
                
                except Exception as e:
                    error_msg = f"Row {index+2}: Error processing record: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    records_skipped += 1
                    # Reset session state after database errors (e.g., UNIQUE constraint violations)
                    db.rollback()
                    continue
            
            # Final commit
            db.commit()
            
            # Update load session
            load_session.records_processed = records_processed
            load_session.records_added = records_added
            load_session.records_skipped = records_skipped
            load_session.errors = json.dumps(errors)
            load_session.completed_at = datetime.utcnow()
            load_session.status = 'completed'
            db.commit()
            
            # Rebuild face recognition index
            logger.info("Rebuilding face recognition index...")
            face_engine.rebuild_index(db)
            
            logger.info(f"Load completed: {records_added} added, {records_skipped} skipped, {len(errors)} errors")
            
            return load_session
            
        except Exception as e:
            # Update load session with error
            load_session.errors = json.dumps(errors + [f"Fatal error: {str(e)}"])
            load_session.completed_at = datetime.utcnow()
            load_session.status = 'failed'
            load_session.records_processed = records_processed
            load_session.records_added = records_added
            load_session.records_skipped = records_skipped
            db.commit()
            
            logger.error(f"Load failed: {str(e)}")
            raise
        
        finally:
            db.close()

# CLI interface
@click.command()
@click.option('--excel-path', default=Config.EXCEL_FILE_PATH, help='Path to Excel file')
@click.option('--force', is_flag=True, help='Overwrite existing records')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def load_excel_cli(excel_path, force, verbose):
    """Load students from Excel file via CLI"""
    if verbose:
        logging.basicConfig(level=logging.INFO)
    
    try:
        loader = ExcelLoader()
        load_session = loader.load_from_excel(excel_path, force=force)
        
        print(f"\nLoad Summary:")
        print(f"File: {excel_path}")
        print(f"Records processed: {load_session.records_processed}")
        print(f"Records added: {load_session.records_added}")
        print(f"Records skipped: {load_session.records_skipped}")
        print(f"Status: {load_session.status}")
        
        if load_session.errors:
            errors = json.loads(load_session.errors)
            print(f"\nErrors/Warnings ({len(errors)}):")
            for error in errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more")
    
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == '__main__':
    load_excel_cli()
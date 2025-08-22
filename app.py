from flask import Flask, request, jsonify, render_template, send_file, abort
from werkzeug.utils import secure_filename
import os
import logging
from datetime import datetime, date
import io
import tempfile
from config import Config
from models import Student, Pass, LoadSession
from db import get_db_session
from face_utils import face_engine
from loader import ExcelLoader
import xlsxwriter

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

# Create upload folder
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

def require_admin_token():
    """Decorator to require admin token for protected endpoints"""
    token = request.headers.get('Authorization') or request.args.get('token') or request.form.get('token')
    if not token or token != Config.ADMIN_TOKEN:
        abort(401, description="Invalid or missing admin token")

def init_face_engine():
    """Initialize face recognition engine"""
    db = get_db_session()
    try:
        # Try to load from cache first
        if not face_engine.load_embeddings_cache():
            logger.info("No embeddings cache found, building from database...")
            face_engine.rebuild_index(db)
    except Exception as e:
        logger.error(f"Error initializing face engine: {e}")
    finally:
        db.close()

@app.route('/')
def index():
    """Main page with camera interface"""
    return render_template('index.html')

@app.route('/api/recognize', methods=['POST'])
def recognize_face():
    """Recognize face from uploaded image"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No image file selected'}), 400
        
        # Read image data
        image_data = file.read()
        
        # Extract face encoding
        encoding, num_faces = face_engine.process_uploaded_image(image_data)
        
        if encoding is None:
            return jsonify({
                'status': 'not_found',
                'message': 'Лицо не найдено на изображении'
            })
        
        if num_faces > 1:
            return jsonify({
                'status': 'error',
                'message': f'Найдено несколько лиц ({num_faces}). Пожалуйста, сделайте фото с одним лицом.'
            }), 400
        
        # Find matching student
        student_id, distance = face_engine.find_matching_student(encoding)
        
        if student_id is None:
            return jsonify({
                'status': 'not_found',
                'message': 'Лицо не найдено в базе данных'
            })
        
        # Get student data
        db = get_db_session()
        try:
            student = db.query(Student).filter_by(id=student_id).first()
            if not student:
                return jsonify({
                    'status': 'error',
                    'message': 'Ошибка получения данных студента'
                }), 500
            
            # Check if student already passed today
            today = date.today()
            existing_pass = db.query(Pass).filter(
                Pass.student_id == student_id,
                Pass.timestamp >= datetime.combine(today, datetime.min.time()),
                Pass.timestamp < datetime.combine(today, datetime.max.time())
            ).first()
            
            if existing_pass:
                return jsonify({
                    'status': 'already_passed',
                    'message': f'Студент уже проходил сегодня в {existing_pass.timestamp.strftime("%H:%M:%S")}',
                    'student': student.to_dict(),
                    'first_pass_time': existing_pass.timestamp.isoformat(),
                    'confidence': f'{distance:.4f}'
                })
            
            # Record new pass
            new_pass = Pass(
                student_id=student_id,
                timestamp=datetime.utcnow(),
                source='camera',
                confidence=f'{distance:.4f}'
            )
            db.add(new_pass)
            db.commit()
            
            return jsonify({
                'status': 'ok',
                'message': 'Студент успешно идентифицирован',
                'student': student.to_dict(),
                'pass_time': new_pass.timestamp.isoformat(),
                'confidence': f'{distance:.4f}'
            })
            
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Error in recognize_face: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

@app.route('/admin/load_excel', methods=['POST'])
def load_excel_endpoint():
    """Load students from Excel file via HTTP endpoint"""
    require_admin_token()
    
    try:
        excel_path = request.form.get('excel_path', Config.EXCEL_FILE_PATH)
        force = request.form.get('force', 'false').lower() == 'true'
        
        # If file is uploaded
        if 'excel_file' in request.files:
            file = request.files['excel_file']
            if file.filename != '':
                filename = secure_filename(file.filename)
                excel_path = os.path.join(Config.UPLOAD_FOLDER, filename)
                file.save(excel_path)
        
        loader = ExcelLoader()
        load_session = loader.load_from_excel(excel_path, force=force)
        
        return jsonify({
            'status': 'success',
            'load_session': load_session.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Error in load_excel_endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/admin/export_report', methods=['GET'])
def export_report():
    """Export attendance report as Excel file"""
    require_admin_token()
    
    try:
        db = get_db_session()
        
        # Get all passes with student data
        query = db.query(Pass, Student).join(Student, Pass.student_id == Student.id)
        
        # Optional date filtering
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Pass.timestamp >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(Pass.timestamp <= end_dt)
            except ValueError:
                pass
        
        passes = query.order_by(Pass.timestamp.desc()).all()
        
        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Attendance Report')
        
        # Headers
        headers = [
            'Matricula', 'Lastname', 'Firstname', 'Group', 'Идентификатор',
            'DateTime of pass', 'Passport number', 'Date of birth', 'Source', 'Confidence'
        ]
        
        # Write headers
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)
        
        # Write data
        for row, (pass_record, student) in enumerate(passes, 1):
            worksheet.write(row, 0, student.matricula or '')
            worksheet.write(row, 1, student.lastname or '')
            worksheet.write(row, 2, student.firstname or '')
            worksheet.write(row, 3, student.group_name or '')
            worksheet.write(row, 4, student.identifier or '')
            worksheet.write(row, 5, pass_record.timestamp.strftime('%Y-%m-%d %H:%M:%S') if pass_record.timestamp else '')
            worksheet.write(row, 6, student.passport_number or '')
            worksheet.write(row, 7, student.date_of_birth or '')
            worksheet.write(row, 8, pass_record.source or '')
            worksheet.write(row, 9, pass_record.confidence or '')
        
        workbook.close()
        output.seek(0)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'attendance_report_{timestamp}.xlsx'
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        logger.error(f"Error in export_report: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    
    finally:
        db.close()

@app.route('/admin/stats', methods=['GET'])
def admin_stats():
    """Get system statistics"""
    require_admin_token()
    
    try:
        db = get_db_session()
        
        # Get counts
        total_students = db.query(Student).count()
        total_passes = db.query(Pass).count()
        today_passes = db.query(Pass).filter(
            Pass.timestamp >= datetime.combine(date.today(), datetime.min.time())
        ).count()
        
        # Get face engine stats
        face_stats = face_engine.get_stats()
        
        # Get recent load sessions
        recent_loads = db.query(LoadSession).order_by(LoadSession.started_at.desc()).limit(5).all()
        
        return jsonify({
            'students': {
                'total': total_students,
                'with_encodings': face_stats['total_embeddings']
            },
            'passes': {
                'total': total_passes,
                'today': today_passes
            },
            'face_engine': face_stats,
            'recent_loads': [load.to_dict() for load in recent_loads]
        })
    
    except Exception as e:
        logger.error(f"Error in admin_stats: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    
    finally:
        db.close()

@app.route('/admin/rebuild_index', methods=['POST'])
def rebuild_index():
    """Rebuild face recognition index"""
    require_admin_token()
    
    try:
        db = get_db_session()
        success = face_engine.rebuild_index(db)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Index rebuilt successfully',
                'stats': face_engine.get_stats()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to rebuild index'
            }), 500
    
    except Exception as e:
        logger.error(f"Error in rebuild_index: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    
    finally:
        db.close()

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized: Invalid or missing admin token'}), 401

@app.errorhandler(413)
def too_large(error):
    return jsonify({'error': 'File too large'}), 413

if __name__ == '__main__':
    # Initialize face recognition engine on startup
    init_face_engine()
    
    # Run Flask app
    app.run(
        debug=Config.DEBUG,
        host='0.0.0.0',
        port=5000
    )
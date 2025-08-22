class FaceRecognitionApp {
    constructor() {
        this.video = document.getElementById('video');
        this.canvas = document.getElementById('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.fileInput = document.getElementById('fileInput');
        this.imagePreview = document.getElementById('imagePreview');
        
        this.startCameraBtn = document.getElementById('startCamera');
        this.stopCameraBtn = document.getElementById('stopCamera');
        this.takePhotoBtn = document.getElementById('takePhoto');
        this.uploadPhotoBtn = document.getElementById('uploadPhoto');
        
        this.result = document.getElementById('result');
        this.resultContent = document.getElementById('resultContent');
        this.loading = document.querySelector('.loading');
        this.status = document.getElementById('status');
        
        this.stream = null;
        
        this.initEventListeners();
        this.checkServerStatus();
    }
    
    initEventListeners() {
        this.startCameraBtn.addEventListener('click', () => this.startCamera());
        this.stopCameraBtn.addEventListener('click', () => this.stopCamera());
        this.takePhotoBtn.addEventListener('click', () => this.takePhoto());
        this.uploadPhotoBtn.addEventListener('click', () => this.uploadPhoto());
        
        this.fileInput.addEventListener('change', (e) => this.previewFile(e));
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && this.takePhotoBtn.disabled === false) {
                e.preventDefault();
                this.takePhoto();
            }
        });
    }
    
    async checkServerStatus() {
        try {
            const response = await fetch('/admin/stats?token=admin_secret_token_2023');
            if (response.ok) {
                this.status.textContent = 'Сервер доступен';
                this.status.className = 'status online';
            } else {
                throw new Error('Server not available');
            }
        } catch (error) {
            this.status.textContent = 'Сервер недоступен';
            this.status.className = 'status offline';
        }
    }
    
    async startCamera() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 480, height: 360 }
            });
            
            this.video.srcObject = this.stream;
            
            this.startCameraBtn.disabled = true;
            this.stopCameraBtn.disabled = false;
            this.takePhotoBtn.disabled = false;
            
            this.showResult('Камера включена. Нажмите "Сделать фото" или пробел для фотографирования.', 'success');
            
        } catch (error) {
            console.error('Error starting camera:', error);
            this.showResult('Ошибка доступа к камере: ' + error.message, 'error');
        }
    }
    
    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        this.video.srcObject = null;
        
        this.startCameraBtn.disabled = false;
        this.stopCameraBtn.disabled = true;
        this.takePhotoBtn.disabled = true;
        
        this.showResult('Камера выключена.', 'warning');
    }
    
    takePhoto() {
        if (!this.stream) {
            this.showResult('Камера не включена.', 'error');
            return;
        }
        
        // Set canvas size to video size
        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        
        // Draw video frame to canvas
        this.ctx.drawImage(this.video, 0, 0);
        
        // Convert canvas to blob
        this.canvas.toBlob((blob) => {
            this.recognizeFace(blob);
        }, 'image/jpeg', 0.8);
    }
    
    previewFile(event) {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                this.imagePreview.src = e.target.result;
                this.imagePreview.style.display = 'block';
                this.uploadPhotoBtn.disabled = false;
            };
            reader.readAsDataURL(file);
        } else {
            this.imagePreview.style.display = 'none';
            this.uploadPhotoBtn.disabled = true;
        }
    }
    
    uploadPhoto() {
        const file = this.fileInput.files[0];
        if (!file) {
            this.showResult('Выберите файл изображения.', 'error');
            return;
        }
        
        this.recognizeFace(file);
    }
    
    async recognizeFace(imageBlob) {
        this.showLoading(true);
        this.hideResult();
        
        try {
            const formData = new FormData();
            formData.append('image', imageBlob);
            
            const response = await fetch('/api/recognize', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.handleRecognitionResult(data);
            } else {
                this.showResult('Ошибка: ' + (data.message || 'Неизвестная ошибка'), 'error');
            }
            
        } catch (error) {
            console.error('Recognition error:', error);
            this.showResult('Ошибка соединения с сервером: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    handleRecognitionResult(data) {
        let resultHtml = '';
        let resultClass = '';
        
        switch (data.status) {
            case 'ok':
                resultClass = 'success';
                resultHtml = `
                    <h3>✅ Студент успешно идентифицирован</h3>
                    <div class="student-info">
                        <h3>${data.student.firstname} ${data.student.lastname}</h3>
                        <p><strong>Матрикула:</strong> ${data.student.matricula || 'Не указана'}</p>
                        <p><strong>Группа:</strong> ${data.student.group_name || 'Не указана'}</p>
                        <p><strong>Идентификатор:</strong> ${data.student.identifier || 'Не указан'}</p>
                        <p><strong>Время прохода:</strong> ${new Date(data.pass_time).toLocaleString('ru-RU')}</p>
                        <p><strong>Точность:</strong> ${data.confidence}</p>
                    </div>
                `;
                break;
                
            case 'already_passed':
                resultClass = 'warning';
                resultHtml = `
                    <h3>⚠️ Студент уже проходил сегодня</h3>
                    <div class="student-info">
                        <h3>${data.student.firstname} ${data.student.lastname}</h3>
                        <p><strong>Матрикула:</strong> ${data.student.matricula || 'Не указана'}</p>
                        <p><strong>Группа:</strong> ${data.student.group_name || 'Не указана'}</p>
                        <p><strong>Время первого прохода:</strong> ${new Date(data.first_pass_time).toLocaleString('ru-RU')}</p>
                        <p><strong>Точность текущего распознавания:</strong> ${data.confidence}</p>
                    </div>
                `;
                break;
                
            case 'not_found':
                resultClass = 'error';
                resultHtml = `
                    <h3>❌ Лицо не найдено</h3>
                    <p>${data.message}</p>
                `;
                break;
                
            default:
                resultClass = 'error';
                resultHtml = `
                    <h3>❌ Ошибка</h3>
                    <p>${data.message || 'Неизвестная ошибка'}</p>
                `;
        }
        
        this.showResult(resultHtml, resultClass, true);
    }
    
    showResult(content, className, isHtml = false) {
        if (isHtml) {
            this.resultContent.innerHTML = content;
        } else {
            this.resultContent.textContent = content;
        }
        
        this.result.className = `result ${className}`;
        this.result.style.display = 'block';
        
        // Scroll to result
        this.result.scrollIntoView({ behavior: 'smooth' });
    }
    
    hideResult() {
        this.result.style.display = 'none';
    }
    
    showLoading(show) {
        this.loading.style.display = show ? 'block' : 'none';
        
        // Disable buttons during loading
        this.takePhotoBtn.disabled = show || !this.stream;
        this.uploadPhotoBtn.disabled = show || !this.fileInput.files[0];
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new FaceRecognitionApp();
});

// Add some global error handling
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
});
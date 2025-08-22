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
                // Show modal for successful recognition
                this.showStudentModal(data.student, 'first-time', data);
                resultClass = 'success';
                resultHtml = `
                    <h3>✅ Студент успешно идентифицирован</h3>
                    <p>Информация отображена в модальном окне</p>
                `;
                break;
                
            case 'already_passed':
                // Show modal for repeat visit
                this.showStudentModal(data.student, 'repeat', data);
                resultClass = 'warning';
                resultHtml = `
                    <h3>⚠️ Студент уже проходил сегодня</h3>
                    <p>Информация отображена в модальном окне</p>
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
    
    showStudentModal(student, visitType, data) {
        const modal = document.getElementById('studentModal');
        const modalContent = document.getElementById('modalContent');
        
        const isFirstTime = visitType === 'first-time';
        const passTime = isFirstTime ? data.pass_time : data.first_pass_time;
        const statusText = isFirstTime ? 
            'Первое посещение сегодня' : 
            `Повторное посещение (первый раз в ${new Date(data.first_pass_time).toLocaleTimeString('ru-RU')})`;
        
        modalContent.innerHTML = `
            <h2>${isFirstTime ? '✅' : '⚠️'} ${student.firstname} ${student.lastname}</h2>
            
            <div class="pass-status ${visitType}">
                <strong>${statusText}</strong><br>
                Текущее время: ${new Date(passTime).toLocaleString('ru-RU')}
            </div>
            
            <div class="student-details">
                <div class="student-detail">
                    <label>Матрикула:</label>
                    <value>${student.matricula || 'Не указана'}</value>
                </div>
                <div class="student-detail">
                    <label>Группа:</label>
                    <value>${student.group_name || 'Не указана'}</value>
                </div>
                <div class="student-detail">
                    <label>Идентификатор:</label>
                    <value>${student.identifier || 'Не указан'}</value>
                </div>
                <div class="student-detail">
                    <label>Дата рождения:</label>
                    <value>${student.date_of_birth || 'Не указана'}</value>
                </div>
                <div class="student-detail">
                    <label>Номер паспорта:</label>
                    <value>${student.passport_number || 'Не указан'}</value>
                </div>
                <div class="student-detail">
                    <label>Точность распознавания:</label>
                    <value>${data.confidence}</value>
                </div>
            </div>
        `;
        
        modal.style.display = 'block';
        
        // Auto-close after 10 seconds
        setTimeout(() => {
            modal.style.display = 'none';
        }, 10000);
    }
}

// Global function to close modal
function closeModal() {
    document.getElementById('studentModal').style.display = 'none';
}

// Close modal when clicking outside of it
window.onclick = function(event) {
    const modal = document.getElementById('studentModal');
    if (event.target === modal) {
        modal.style.display = 'none';
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
// Estado de la aplicación
class EmailApp {
    constructor() {
        this.currentFolder = 'inbox';
        this.selectedEmails = new Set();
        this.currentEmail = null;
        this.userCache = new Map();
        this.searchTimeout = null;
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadEmails();
    }

    bindEvents() {
        // Navegación de carpetas
        document.querySelectorAll('.folder-item').forEach(item => {
            item.addEventListener('click', (e) => {
                this.switchFolder(e.currentTarget.dataset.folder);
            });
        });

        // Botón redactar
        document.getElementById('composeBtn').addEventListener('click', () => {
            this.openComposeModal();
        });

        // Controles de lista
        document.getElementById('selectAll').addEventListener('change', (e) => {
            this.toggleSelectAll(e.target.checked);
        });

        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.loadEmails();
        });

        document.getElementById('deleteBtn').addEventListener('click', () => {
            this.deleteSelectedEmails();
        });

        // Búsqueda
        document.getElementById('searchInput').addEventListener('input', (e) => {
            this.handleSearch(e.target.value);
        });

        // Modal de redacción
        document.getElementById('closeCompose').addEventListener('click', () => {
            this.closeComposeModal();
        });

        document.getElementById('cancelCompose').addEventListener('click', () => {
            this.closeComposeModal();
        });

        document.getElementById('saveDraft').addEventListener('click', (e) => {
            e.preventDefault();
            this.saveDraft();
        });

        document.getElementById('composeForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendEmail();
        });

        // Autocompletar usuarios
        document.getElementById('composeTo').addEventListener('input', (e) => {
            this.searchUsers(e.target.value);
        });

        // Vista de email
        document.getElementById('backToList').addEventListener('click', () => {
            this.showEmailList();
        });

        document.getElementById('replyEmail').addEventListener('click', () => {
            this.replyToEmail();
        });

        document.getElementById('forwardEmail').addEventListener('click', () => {
            this.forwardEmail();
        });

        document.getElementById('deleteEmail').addEventListener('click', () => {
            this.deleteCurrentEmail();
        });

        // Menú responsive
        document.getElementById('menuToggle').addEventListener('click', () => {
            this.toggleSidebar();
        });

        // Cerrar sugerencias al hacer clic fuera
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.compose-field')) {
                this.hideSuggestions();
            }
        });
    }

    async loadEmails() {
        try {
            this.showLoading();
            
            console.log("DEBUG: Cargando emails para folder:", this.currentFolder);
            
            const response = await fetch(`/estudiante/api/comunicaciones?folder=${this.currentFolder}`);
            
            if (!response.ok) {
                throw new Error('Error al cargar los emails');
            }
            
            const emails = await response.json();
            console.log("DEBUG: Emails recibidos:", emails);
            
            if (emails.error) {
                throw new Error(emails.error);
            }
            
            this.renderEmailList(emails);
            
        } catch (error) {
            console.error('Error:', error);
            this.showNotification('Error al cargar los emails', 'error');
        } finally {
            this.hideLoading();
        }
    }

    renderEmailList(emails) {
        const emailList = document.getElementById('emailList');
        
        if (!emails || emails.length === 0) {
            emailList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <h3>No hay mensajes</h3>
                    <p>No hay emails en ${this.getFolderName(this.currentFolder)}</p>
                </div>
            `;
            return;
        }

        emailList.innerHTML = emails.map(email => `
            <div class="email-item" data-email-id="${email.id_comunicacion}">
                <div class="email-checkbox">
                    <input type="checkbox" id="email-${email.id_comunicacion}" 
                           onchange="emailApp.toggleEmailSelection(${email.id_comunicacion})">
                    <label for="email-${email.id_comunicacion}"></label>
                </div>
                
                <div class="email-sender" onclick="emailApp.viewEmail(${email.id_comunicacion})">
                    ${this.currentFolder === 'sent' ? email.destinatario_nombre : email.remitente_nombre}
                </div>
                
                <div class="email-preview" onclick="emailApp.viewEmail(${email.id_comunicacion})">
                    <div class="email-subject">
                        ${email.asunto || '(Sin asunto)'}
                    </div>
                    <div class="email-snippet">
                        ${this.truncateText(email.mensaje || '', 100)}
                    </div>
                </div>
                
                <div class="email-date" onclick="emailApp.viewEmail(${email.id_comunicacion})">
                    ${this.formatDate(email.fecha_envio)}
                </div>
            </div>
        `).join('');

        this.updateSelectionUI();
        this.updateEmailRange(emails.length);
        
        // Agregar event listeners para clic en emails
        document.querySelectorAll('.email-item').forEach(item => {
            // Remover listeners anteriores para evitar duplicados
            item.removeEventListener('click', this.handleEmailClick);
            // Agregar nuevo listener
            item.addEventListener('click', this.handleEmailClick.bind(this));
        });
    }

    handleEmailClick(e) {
        // Solo activar si no se hizo clic en el checkbox
        if (!e.target.closest('.form-check')) {
            const emailId = parseInt(e.currentTarget.dataset.emailId);
            this.viewEmail(emailId);
        }
    }

    async viewEmail(emailId) {
        try {
            const response = await fetch(`/estudiante/api/comunicaciones/${emailId}`);
            
            if (!response.ok) {
                throw new Error('Error al cargar el email');
            }
            
            const email = await response.json();
            
            if (email.error) {
                throw new Error(email.error);
            }
            
            this.currentEmail = email;
            this.renderEmailView(email);
            this.showEmailView();
            
        } catch (error) {
            console.error('Error:', error);
            this.showNotification('Error al cargar el email', 'error');
        }
    }

    renderEmailView(email) {
        const emailContent = document.getElementById('emailContent');
        
        // Mostrar botones diferentes según la carpeta
        const deleteButtonText = this.currentFolder === 'deleted' ? 'Recuperar' : 'Eliminar';
        const deleteButtonIcon = this.currentFolder === 'deleted' ? 'fa-undo' : 'fa-trash';
        const deleteButtonAction = this.currentFolder === 'deleted' ? 'restoreEmail' : 'deleteCurrentEmail';
        
        emailContent.innerHTML = `
            <div class="email-header">
                <div class="email-meta">
                    <h2 class="email-subject">${email.asunto || '(Sin asunto)'}</h2>
                    <div class="email-participants">
                        <div class="participant">
                            <strong>De:</strong> ${email.remitente_nombre}
                        </div>
                        <div class="participant">
                            <strong>Para:</strong> ${email.destinatario_nombre}
                        </div>
                    </div>
                    <div class="email-date">${this.formatDetailedDate(email.fecha_envio)}</div>
                </div>
            </div>
            
            <div class="email-body">
                <div class="email-content-text">
                    ${this.formatEmailBody(email.mensaje || '')}
                </div>
            </div>
            
            <div class="email-actions-footer">
                <button class="action-btn" onclick="emailApp.replyToEmail()">
                    <i class="fas fa-reply"></i> Responder
                </button>
                <button class="action-btn" onclick="emailApp.forwardEmail()">
                    <i class="fas fa-share"></i> Reenviar
                </button>
                <button class="action-btn ${this.currentFolder === 'deleted' ? 'restore' : 'delete'}" 
                        onclick="emailApp.${deleteButtonAction}()">
                    <i class="fas ${deleteButtonIcon}"></i> ${deleteButtonText}
                </button>
            </div>
        `;
    }

    async sendEmail() {
        const toInput = document.getElementById('composeTo');
        const subjectInput = document.getElementById('composeSubject');
        const bodyInput = document.getElementById('composeBody');
        
        // Extraer el email del campo "Para"
        const toValue = toInput.value.trim();
        let emailTo = toValue;
        
        // Si el formato es "Nombre (email@dominio.com)", extraer solo el email
        const emailMatch = toValue.match(/\(([^)]+)\)/);
        if (emailMatch) {
            emailTo = emailMatch[1].trim();
        }
        
        console.log("DEBUG: Intentando enviar email a:", emailTo);

        // Validación básica de email
        if (!this.isValidEmail(emailTo)) {
            this.showNotification('Por favor ingresa un email válido', 'error');
            return;
        }

        const emailData = {
            to: emailTo,
            asunto: subjectInput.value.trim(),
            mensaje: bodyInput.value.trim()
        };

        try {
            console.log("DEBUG: Enviando datos:", emailData);
            
            const response = await fetch('/estudiante/api/comunicaciones', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(emailData)
            });

            const result = await response.json();
            console.log("DEBUG: Respuesta del servidor:", result);

            if (response.ok && result.success) {
                this.showNotification('Email enviado correctamente', 'success');
                this.closeComposeModal();
                this.loadEmails();
            } else {
                throw new Error(result.error || 'Error al enviar el email');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showNotification('Error al enviar el email: ' + error.message, 'error');
        }
    }

    async saveDraft() {
        const toInput = document.getElementById('composeTo');
        const subjectInput = document.getElementById('composeSubject');
        const bodyInput = document.getElementById('composeBody');
        
        const toValue = toInput.value.trim();
        let emailTo = toValue;
        
        const emailMatch = toValue.match(/\(([^)]+)\)/);
        if (emailMatch) {
            emailTo = emailMatch[1].trim();
        }

        const emailData = {
            to: emailTo || '',
            asunto: subjectInput.value.trim() || '(Sin asunto)',
            mensaje: bodyInput.value.trim()
        };

        try {
            const response = await fetch('/estudiante/api/comunicaciones/draft', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(emailData)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showNotification('Borrador guardado', 'success');
                this.closeComposeModal();
                this.loadEmails();
            } else {
                throw new Error(result.error || 'Error al guardar el borrador');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showNotification('Error al guardar el borrador', 'error');
        }
    }

    async searchUsers(query) {
        if (query.length < 2) {
            this.hideSuggestions();
            return;
        }

        try {
            console.log("DEBUG: Buscando usuarios con query:", query);
            
            const response = await fetch(`/estudiante/api/usuarios/buscar?q=${encodeURIComponent(query)}`);
            
            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${response.statusText}`);
            }
            
            const users = await response.json();
            console.log("DEBUG: Respuesta de búsqueda:", users);
            
            // Verificar si la respuesta es un array
            if (!Array.isArray(users)) {
                console.error("DEBUG: La respuesta no es un array:", users);
                if (users && users.error) {
                    throw new Error(users.error);
                } else {
                    throw new Error('Formato de respuesta inválido');
                }
            }
            
            this.showUserSuggestions(users);
            
        } catch (error) {
            console.error('Error buscando usuarios:', error);
            this.hideSuggestions();
            // No mostrar notificación para evitar spam durante la escritura
        }
    }

    showUserSuggestions(users) {
        const suggestions = document.getElementById('userSuggestions');
        const toInput = document.getElementById('composeTo');
        
        // Limpiar cache
        this.userCache.clear();
        
        // Verificar que users sea un array
        if (!Array.isArray(users)) {
            console.error('Users no es un array:', users);
            suggestions.style.display = 'none';
            return;
        }
        
        suggestions.innerHTML = users.map(user => {
            const displayText = `${user.nombre} (${user.email})`;
            this.userCache.set(displayText, user);
            
            return `
                <div class="suggestion-item" onclick="emailApp.selectUser('${displayText.replace(/'/g, "\\'")}')">
                    <div class="suggestion-name">${user.nombre}</div>
                    <div class="suggestion-email">${user.email}</div>
                </div>
            `;
        }).join('');
        
        suggestions.style.display = users.length > 0 ? 'block' : 'none';
    }

    selectUser(displayText) {
        document.getElementById('composeTo').value = displayText;
        this.hideSuggestions();
    }

    hideSuggestions() {
        document.getElementById('userSuggestions').style.display = 'none';
    }

    // Métodos de selección
    toggleEmailSelection(emailId, event) {
        console.log('DEBUG: toggleEmailSelection called with emailId:', emailId);
        
        // Prevenir que el clic en el checkbox active el onclick del email-item
        if (event) {
            event.stopPropagation();
        }
        
        if (this.selectedEmails.has(emailId)) {
            this.selectedEmails.delete(emailId);
            console.log('DEBUG: Removed emailId from selection');
        } else {
            this.selectedEmails.add(emailId);
            console.log('DEBUG: Added emailId to selection');
        }
        
        console.log('DEBUG: Current selection:', Array.from(this.selectedEmails));
        this.updateSelectionUI();
    }

    toggleSelectAll(checked) {
        const checkboxes = document.querySelectorAll('.form-check input[type="checkbox"]');
        
        this.selectedEmails.clear();
        
        if (checked) {
            document.querySelectorAll('.email-item').forEach(item => {
                const emailId = parseInt(item.dataset.emailId);
                this.selectedEmails.add(emailId);
            });
        }
        
        checkboxes.forEach(checkbox => {
            checkbox.checked = checked;
        });
        
        this.updateSelectionUI();
    }

    async deleteSelectedEmails() {
        console.log('DEBUG: selectedEmails size:', this.selectedEmails.size);
        console.log('DEBUG: selectedEmails:', Array.from(this.selectedEmails));
        
        if (this.selectedEmails.size === 0) {
            this.showNotification('Selecciona al menos un email', 'warning');
            return;
        }

        const action = this.currentFolder === 'deleted' ? 'restaurar' : 'eliminar';
        const actionText = this.currentFolder === 'deleted' ? 'restaurar' : 'mover a papelera';

        if (!confirm(`¿${action.charAt(0).toUpperCase() + action.slice(1)} ${this.selectedEmails.size} email(s)?`)) {
            return;
        }

        try {
            for (const emailId of this.selectedEmails) {
                let url = `/estudiante/api/comunicaciones/${emailId}`;
                let method = 'DELETE';
                
                // Si estamos en papelera, restaurar el email
                if (this.currentFolder === 'deleted') {
                    url = `/estudiante/api/comunicaciones/${emailId}/restore`;
                    method = 'PUT';
                }

                const response = await fetch(url, {
                    method: method
                });

                if (!response.ok) {
                    throw new Error(`Error al ${actionText} el email`);
                }
            }

            const message = this.currentFolder === 'deleted' 
                ? `${this.selectedEmails.size} email(s) restaurados` 
                : `${this.selectedEmails.size} email(s) movidos a papelera`;
                
            this.showNotification(message, 'success');
            this.selectedEmails.clear();
            this.loadEmails();
        } catch (error) {
            console.error('Error:', error);
            this.showNotification(`Error al ${actionText} los emails`, 'error');
        }
    }

    // Navegación
    switchFolder(folder) {
        this.currentFolder = folder;
        this.selectedEmails.clear();
        
        // Actualizar UI
        document.querySelectorAll('.folder-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-folder="${folder}"]`).classList.add('active');
        
        document.getElementById('selectAll').checked = false;
        
        // Cambiar texto del botón eliminar según la carpeta
        const deleteBtn = document.getElementById('deleteBtn');
        if (folder === 'deleted') {
            deleteBtn.innerHTML = '<i class="fas fa-undo"></i>';
            deleteBtn.title = 'Restaurar';
        } else {
            deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
            deleteBtn.title = 'Eliminar';
        }
        
        this.loadEmails();
    }

    showEmailView() {
        document.getElementById('emailListView').style.display = 'none';
        document.getElementById('emailDetailView').style.display = 'block';
    }

    showEmailList() {
        document.getElementById('emailListView').style.display = 'block';
        document.getElementById('emailDetailView').style.display = 'none';
        this.currentEmail = null;
    }

    // Modal de redacción
    openComposeModal() {
        document.getElementById('composeModal').style.display = 'block';
        document.getElementById('composeTo').focus();
    }

    closeComposeModal() {
        document.getElementById('composeModal').style.display = 'none';
        document.getElementById('composeForm').reset();
        this.hideSuggestions();
        this.userCache.clear();
    }

    // Utilidades
    updateSelectionUI() {
        const selectedCount = this.selectedEmails.size;
        const totalCount = document.querySelectorAll('.email-item').length;
        
        const selectAllCheckbox = document.getElementById('selectAll');
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = selectedCount > 0 && selectedCount === totalCount;
            selectAllCheckbox.indeterminate = selectedCount > 0 && selectedCount < totalCount;
        }
        
        // Actualizar el estado visual de los checkboxes individuales
        document.querySelectorAll('.form-check input[type="checkbox"]').forEach(checkbox => {
            const emailId = parseInt(checkbox.id.replace('email-', ''));
            checkbox.checked = this.selectedEmails.has(emailId);
        });
    }

    updateEmailRange(total) {
        const rangeText = total > 0 ? `1-${total} de ${total}` : '0-0 de 0';
        document.getElementById('emailRange').textContent = rangeText;
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 1) {
            return 'Ayer';
        } else if (diffDays > 1) {
            return date.toLocaleDateString();
        } else {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
    }

    formatDetailedDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString('es-ES', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    formatEmailBody(body) {
        return body.replace(/\n/g, '<br>');
    }

    truncateText(text, length) {
        return text.length > length ? text.substring(0, length) + '...' : text;
    }

    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    getFolderName(folder) {
        const names = {
            'inbox': 'Bandeja de entrada',
            'sent': 'Enviados',
            'draft': 'Borradores',
            'deleted': 'Papelera'
        };
        return names[folder] || folder;
    }

    handleSearch(query) {
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            // Implementar búsqueda si es necesario
            console.log('Buscando:', query);
        }, 300);
    }

    showLoading() {
        document.getElementById('emailList').classList.add('loading');
    }

    hideLoading() {
        document.getElementById('emailList').classList.remove('loading');
    }

    toggleSidebar() {
        document.getElementById('sidebar').classList.toggle('collapsed');
    }

    showNotification(message, type = 'info') {
        const notifications = document.getElementById('notifications');
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check' : type === 'error' ? 'exclamation-triangle' : type === 'warning' ? 'exclamation' : 'info'}"></i>
            <span>${message}</span>
        `;
        
        notifications.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    // Métodos para replies y forwards
    replyToEmail() {
        this.openComposeModal();
        if (this.currentEmail) {
            document.getElementById('composeTo').value = this.currentEmail.remitente_nombre;
            document.getElementById('composeSubject').value = `Re: ${this.currentEmail.asunto}`;
            document.getElementById('composeBody').value = `\n\n--- Mensaje original ---\n${this.currentEmail.mensaje}`;
        }
    }

    forwardEmail() {
        this.openComposeModal();
        if (this.currentEmail) {
            document.getElementById('composeSubject').value = `Fw: ${this.currentEmail.asunto}`;
            document.getElementById('composeBody').value = `\n\n--- Mensaje original ---\n${this.currentEmail.mensaje}`;
        }
    }

    async deleteCurrentEmail() {
        if (!this.currentEmail) return;
        
        const action = this.currentFolder === 'deleted' ? 'restaurar' : 'eliminar';
        
        if (confirm(`¿${action.charAt(0).toUpperCase() + action.slice(1)} este email?`)) {
            try {
                let url = `/estudiante/api/comunicaciones/${this.currentEmail.id_comunicacion}`;
                let method = 'DELETE';
                
                if (this.currentFolder === 'deleted') {
                    url = `/estudiante/api/comunicaciones/${this.currentEmail.id_comunicacion}/restore`;
                    method = 'PUT';
                }

                const response = await fetch(url, {
                    method: method
                });

                if (response.ok) {
                    const message = this.currentFolder === 'deleted' 
                        ? 'Email restaurado' 
                        : 'Email movido a papelera';
                    this.showNotification(message, 'success');
                    this.showEmailList();
                    this.loadEmails();
                } else {
                    throw new Error(`Error al ${action} el email`);
                }
            } catch (error) {
                console.error('Error:', error);
                this.showNotification(`Error al ${action} el email`, 'error');
            }
        }
    }

    async restoreEmail() {
        if (!this.currentEmail) return;
        
        if (confirm('¿Restaurar este email?')) {
            try {
                const response = await fetch(`/estudiante/api/comunicaciones/${this.currentEmail.id_comunicacion}/restore`, {
                    method: 'PUT'
                });

                if (response.ok) {
                    this.showNotification('Email restaurado', 'success');
                    this.showEmailList();
                    this.loadEmails();
                } else {
                    throw new Error('Error al restaurar el email');
                }
            } catch (error) {
                console.error('Error:', error);
                this.showNotification('Error al restaurar el email', 'error');
            }
        }
    }
}

// Inicializar la aplicación cuando el DOM esté listo
let emailApp;
document.addEventListener('DOMContentLoaded', () => {
    emailApp = new EmailApp();
});
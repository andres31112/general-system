class EmailSystem {
    constructor() {
        this.currentFolder = 'inbox';
        this.selectedEmails = new Set();
        this.currentEmail = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadEmails();
    }

    bindEvents() {
        // Navegación entre carpetas
        document.querySelectorAll('.folder-item').forEach(item => {
            item.addEventListener('click', (e) => {
                this.switchFolder(e.currentTarget.dataset.folder);
            });
        });

        // Botón redactar
        document.getElementById('composeBtn').addEventListener('click', () => {
            this.openComposeModal();
        });

        // Botones de control
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.loadEmails();
        });

        document.getElementById('selectAll').addEventListener('change', (e) => {
            this.toggleSelectAll(e.target.checked);
        });

        document.getElementById('deleteBtn').addEventListener('click', () => {
            this.deleteSelectedEmails();
        });

        document.getElementById('markReadBtn').addEventListener('click', () => {
            this.markSelectedAsRead();
        });

        // Navegación entre páginas
        document.getElementById('prevPage').addEventListener('click', () => {
            this.previousPage();
        });

        document.getElementById('nextPage').addEventListener('click', () => {
            this.nextPage();
        });

        // Volver a la lista
        document.getElementById('backToList').addEventListener('click', () => {
            this.showEmailList();
        });

        // Modal de redacción
        document.getElementById('closeCompose').addEventListener('click', () => {
            this.closeComposeModal();
        });

        document.getElementById('cancelCompose').addEventListener('click', () => {
            this.closeComposeModal();
        });

        document.getElementById('composeForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendEmail();
        });

        document.getElementById('saveDraft').addEventListener('click', () => {
            this.saveDraft();
        });

        // Búsqueda
        document.getElementById('searchInput').addEventListener('input', (e) => {
            this.searchEmails(e.target.value);
        });

        // Menú responsive
        document.getElementById('menuToggle').addEventListener('click', () => {
            this.toggleSidebar();
        });
    }

    async loadEmails() {
        try {
            // Simular carga de emails (reemplazar con llamada real a tu API)
            const response = await fetch(`/api/emails?folder=${this.currentFolder}`);
            const emails = await response.json();
            
            this.renderEmailList(emails);
            this.updateEmailCounts();
        } catch (error) {
            console.error('Error loading emails:', error);
            this.showError('Error al cargar los correos');
        }
    }

    renderEmailList(emails) {
        const emailList = document.getElementById('emailList');
        
        if (emails.length === 0) {
            emailList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <h3>No hay mensajes</h3>
                    <p>Tu ${this.getFolderName(this.currentFolder)} está vacía</p>
                </div>
            `;
            return;
        }

        emailList.innerHTML = emails.map(email => `
            <div class="email-item ${email.read ? '' : 'unread'}" data-email-id="${email.id}">
                <div class="email-checkbox">
                    <input type="checkbox" id="email-${email.id}" class="email-select">
                    <label for="email-${email.id}"></label>
                </div>
                <div class="email-star ${email.starred ? 'starred' : ''}" data-email-id="${email.id}">
                    <i class="${email.starred ? 'fas' : 'far'} fa-star"></i>
                </div>
                <div class="email-sender">${email.from}</div>
                <div class="email-preview">
                    <div class="email-subject">${email.subject}</div>
                    <div class="email-body">- ${email.body.substring(0, 100)}...</div>
                </div>
                <div class="email-time">${this.formatTime(email.timestamp)}</div>
            </div>
        `).join('');

        // Agregar event listeners a los emails
        document.querySelectorAll('.email-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.email-checkbox') && !e.target.closest('.email-star')) {
                    this.viewEmail(item.dataset.emailId);
                }
            });
        });

        document.querySelectorAll('.email-star').forEach(star => {
            star.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleStar(star.dataset.emailId);
            });
        });

        document.querySelectorAll('.email-select').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                this.toggleEmailSelection(e.target.closest('.email-item').dataset.emailId, e.target.checked);
            });
        });
    }

    async viewEmail(emailId) {
        try {
            const response = await fetch(`/api/emails/${emailId}?folder=${this.currentFolder}`);
            const email = await response.json();
            
            this.currentEmail = email;
            this.showEmailView(email);
        } catch (error) {
            console.error('Error loading email:', error);
            this.showError('Error al cargar el correo');
        }
    }

    showEmailView(email) {
        document.getElementById('emailListContainer').style.display = 'none';
        document.getElementById('emailView').style.display = 'flex';

        const emailContent = document.getElementById('emailContent');
        emailContent.innerHTML = `
            <div class="email-header-info">
                <h1 class="email-subject-large">${email.subject}</h1>
                <div class="email-meta">
                    <div class="email-sender-large">${email.from}</div>
                    <div class="email-to">para ${email.to}</div>
                    <div class="email-time-large">${this.formatTime(email.timestamp)}</div>
                </div>
            </div>
            <div class="email-body-content">
                ${email.body.replace(/\n/g, '<br>')}
            </div>
        `;

        // Actualizar botón de favorito
        const starBtn = document.getElementById('starEmail');
        starBtn.innerHTML = `<i class="${email.starred ? 'fas' : 'far'} fa-star"></i>`;
        starBtn.onclick = () => this.toggleStar(email.id);
    }

    showEmailList() {
        document.getElementById('emailView').style.display = 'none';
        document.getElementById('emailListContainer').style.display = 'flex';
        this.currentEmail = null;
    }

    switchFolder(folder) {
        this.currentFolder = folder;
        
        // Actualizar navegación
        document.querySelectorAll('.folder-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-folder="${folder}"]`).classList.add('active');
        
        // Limpiar selecciones
        this.selectedEmails.clear();
        document.getElementById('selectAll').checked = false;
        
        // Cargar emails
        this.loadEmails();
        this.showEmailList();
    }

    openComposeModal() {
        document.getElementById('composeModal').style.display = 'flex';
        document.getElementById('composeTo').focus();
    }

    closeComposeModal() {
        document.getElementById('composeModal').style.display = 'none';
        document.getElementById('composeForm').reset();
    }

    async sendEmail() {
        const formData = {
            to: document.getElementById('composeTo').value,
            subject: document.getElementById('composeSubject').value,
            body: document.getElementById('composeBody').value
        };

        try {
            const response = await fetch('/api/emails', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                this.showSuccess('Correo enviado correctamente');
                this.closeComposeModal();
                // Si estamos en la carpeta "Enviados", recargar
                if (this.currentFolder === 'sent') {
                    this.loadEmails();
                }
            } else {
                throw new Error('Error al enviar el correo');
            }
        } catch (error) {
            console.error('Error sending email:', error);
            this.showError('Error al enviar el correo');
        }
    }

    saveDraft() {
        // Implementar guardado de borrador
        this.showSuccess('Borrador guardado');
        this.closeComposeModal();
    }

    toggleStar(emailId) {
        // Implementar toggle de favorito
        console.log('Toggle star for email:', emailId);
    }

    toggleSelectAll(selected) {
        document.querySelectorAll('.email-select').forEach(checkbox => {
            checkbox.checked = selected;
            const emailId = checkbox.closest('.email-item').dataset.emailId;
            this.toggleEmailSelection(emailId, selected);
        });
    }

    toggleEmailSelection(emailId, selected) {
        if (selected) {
            this.selectedEmails.add(emailId);
        } else {
            this.selectedEmails.delete(emailId);
        }
        this.updateSelectionUI();
    }

    updateSelectionUI() {
        const selectedCount = this.selectedEmails.size;
        document.querySelectorAll('.email-item').forEach(item => {
            if (this.selectedEmails.has(item.dataset.emailId)) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
    }

    async deleteSelectedEmails() {
        if (this.selectedEmails.size === 0) return;

        if (confirm(`¿Estás seguro de que quieres eliminar ${this.selectedEmails.size} correo(s)?`)) {
            try {
                // Implementar eliminación
                for (const emailId of this.selectedEmails) {
                    await fetch(`/api/emails/${emailId}`, {
                        method: 'DELETE'
                    });
                }
                
                this.showSuccess('Correos eliminados correctamente');
                this.selectedEmails.clear();
                this.loadEmails();
            } catch (error) {
                console.error('Error deleting emails:', error);
                this.showError('Error al eliminar los correos');
            }
        }
    }

    markSelectedAsRead() {
        // Implementar marcar como leído
        this.showSuccess('Correos marcados como leídos');
    }

    searchEmails(query) {
        // Implementar búsqueda
        console.log('Searching for:', query);
    }

    toggleSidebar() {
        document.getElementById('sidebar').classList.toggle('open');
    }

    getFolderName(folder) {
        const names = {
            'inbox': 'bandeja de entrada',
            'starred': 'carpeta de destacados',
            'sent': 'carpeta de enviados',
            'drafts': 'carpeta de borradores',
            'trash': 'papelera'
        };
        return names[folder] || 'carpeta';
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 86400000) { // Menos de 24 horas
            return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
        } else if (diff < 604800000) { // Menos de 7 días
            return date.toLocaleDateString('es-ES', { weekday: 'short' });
        } else {
            return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
        }
    }

    updateEmailCounts() {
        // Implementar actualización de contadores
        // Por ahora, valores de ejemplo
        document.getElementById('inboxCount').textContent = '5';
        document.getElementById('draftsCount').textContent = '2';
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type) {
        // Implementar notificaciones bonitas
        alert(message);
    }

    previousPage() {
        // Implementar paginación
        console.log('Previous page');
    }

    nextPage() {
        // Implementar paginación
        console.log('Next page');
    }
}

// Inicializar el sistema cuando se carga la página
document.addEventListener('DOMContentLoaded', () => {
    new EmailSystem();
});
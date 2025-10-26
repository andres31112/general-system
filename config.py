import os

class Config:
    # Configuración de la base de datos
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@127.0.0.1:3306/institucion_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Clave secreta para la seguridad de la aplicación
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-llave-secreta-para-proteger-las-sesiones'

    # -------------------------------------------------------------
    # ✅ CONFIGURACIÓN ACTUALIZADA PARA EL NUEVO CORREO
    # -------------------------------------------------------------
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'Gestion.Acentrax@gmail.com'
    MAIL_PASSWORD = 'bgycesijhhnoqhac'  
    MAIL_DEFAULT_SENDER = 'Gestion.Acentrax@gmail.com'
    
    # Configuración para URLs externas (necesario para envío de correos)
    SERVER_NAME = 'localhost:5000'  # Cambiar por tu dominio en producción
    APPLICATION_ROOT = '/'
    PREFERRED_URL_SCHEME = 'http'  # Cambiar a 'https' en producción
        
    # Configuración para subida de archivos
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'tareas')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Límite de 16MB para archivos
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'rar'}
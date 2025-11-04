import os

class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@127.0.0.1:3306/institucion_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-llave-secreta-para-proteger-las-sesiones'


    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'Gestion.Acentrax@gmail.com'
    MAIL_PASSWORD = 'bgycesijhhnoqhac'  
    MAIL_DEFAULT_SENDER = 'Gestion.Acentrax@gmail.com'
    
    SERVER_NAME = 'localhost:5000'  
    APPLICATION_ROOT = '/'
    PREFERRED_URL_SCHEME = 'http' 
        
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'tareas')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'rar'}
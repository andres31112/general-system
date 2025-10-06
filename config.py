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
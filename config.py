import os

class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:3112@127.0.0.1:3306/institucion_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-llave-secreta-para-proteger-las-sesiones'

    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'jsuarezhe04@gmail.com'
    MAIL_PASSWORD = 'qutjgxhnangevraz'
    MAIL_DEFAULT_SENDER = 'jsuarezhe04@gmail.com'
import os
import secrets
import string
import time
from flask_mail import Message
from flask import current_app, render_template, url_for
from extensions import mail
from itsdangerous import URLSafeTimedSerializer  


def generate_verification_code():
    """Genera un código de verificación de 8 caracteres alfanuméricos"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(8))

def get_serializer():
    """ FUNCIÓN CORREGIDA: Obtiene el serializador de forma consistente"""
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

def generate_verification_token(user_id, code, email):
    """FUNCIÓN CORREGIDA: Genera token de verificación consistente"""
    s = get_serializer() 
    return s.dumps({
        'user_id': user_id,
        'code': code,
        'email': email
    }, salt='email-verification')

def send_welcome_email(usuario, verification_code):
    """Envía correo de bienvenida con código de verificación y link directo"""
    try:
        verification_token = generate_verification_token(
            usuario.id_usuario, 
            verification_code, 
            usuario.correo
        )
        
        verification_url = url_for('auth.verify_email_with_token', token=verification_token, _external=True)
        
        # DEBUG: Mostrar información del token
        print(f"DEBUG: Token generado para {usuario.correo}: {verification_token}")
        print(f"DEBUG: URL de verificación: {verification_url}")
        
        subject = "¡Bienvenido al Sistema Académico - Verifica tu Email!"
        
        html_body = render_template(
            'emails/welcome_verification.html',
            usuario=usuario,
            verification_code=verification_code,
            verification_url=verification_url
        )
        
        msg = Message(
            subject=subject,
            recipients=[usuario.correo],
            html=html_body,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        mail.send(msg)
        print(f"DEBUG: Email enviado exitosamente a {usuario.correo}")
        return True
    except Exception as e:
        error_msg = str(e)
        print(f"Error enviando correo de bienvenida: {error_msg}")
        
        # Manejo específico de errores comunes
        if "Daily user sending limit exceeded" in error_msg:
            print("⚠️  LÍMITE DIARIO DE GMAIL EXCEDIDO")
            print("💡 SOLUCIÓN: El usuario puede verificar manualmente con el código de verificación")
            print(f"📧 Código de verificación para {usuario.correo}: {verification_code}")
            return "limit_exceeded"
        elif "Authentication failed" in error_msg:
            print("❌ ERROR DE AUTENTICACIÓN - Verificar credenciales de Gmail")
            return False
        elif "Connection refused" in error_msg:
            print("❌ ERROR DE CONEXIÓN - Verificar conexión a internet")
            return False
        else:
            print(f"❌ ERROR DESCONOCIDO: {error_msg}")
            return False

def send_verification_success_email(usuario, password=None):
    """Envía correo con credenciales después de verificación exitosa"""
    try:
        subject = "✅ Verificación Exitosa - Tus Credenciales de Acceso"
        
        html_body = render_template(
            'emails/verification_success.html',
            usuario=usuario,
            password=password,
            login_url=url_for('auth.login', _external=True)
        )
        
        msg = Message(
            subject=subject,
            recipients=[usuario.correo],
            html=html_body,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        mail.send(msg)
        print(f"DEBUG: Correo de verificación exitosa enviado a {usuario.correo}")
        return True
    except Exception as e:
        print(f"Error enviando correo de verificación exitosa: {str(e)}")
        return False

def send_password_reset_email(usuario, token):
    """Envía correo para restablecer contraseña"""
    try:
        reset_url = url_for('auth.restablecer_password', token=token, _external=True)
        
        subject = "Restablecimiento de Contraseña - Sistema Académico"
        
        html_body = render_template(
            'emails/password_reset.html',
            usuario=usuario,
            reset_url=reset_url
        )
        
        msg = Message(
            subject=subject,
            recipients=[usuario.correo],
            html=html_body,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error enviando correo de restablecimiento: {str(e)}")
        return False

def send_welcome_email_with_retry(usuario, verification_code, max_retries=2):
    """Envía correo de bienvenida con reintentos en caso de fallo temporal"""
    for attempt in range(max_retries + 1):
        try:
            result = send_welcome_email(usuario, verification_code)
            if result == True or result == "limit_exceeded":
                return result
            
            if attempt < max_retries:
                print(f"Intento {attempt + 1} falló, reintentando en 5 segundos...")
                time.sleep(5)
            else:
                print(f"Todos los intentos fallaron para {usuario.correo}")
                return False
                
        except Exception as e:
            print(f"Error en intento {attempt + 1}: {str(e)}")
            if attempt < max_retries:
                time.sleep(5)
            else:
                return False
    
    return False

def get_verification_info(usuario):
    """Obtiene información de verificación para mostrar al usuario cuando falla el correo"""
    verification_token = generate_verification_token(
        usuario.id_usuario, 
        usuario.verification_code, 
        usuario.correo
    )
    
    verification_url = url_for('auth.verify_email_with_token', token=verification_token, _external=True)
    
    return {
        'code': usuario.verification_code,
        'url': verification_url,
        'expires': usuario.verification_code_expires
    }
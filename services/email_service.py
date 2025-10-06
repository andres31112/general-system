import os
import secrets
import string
from flask_mail import Message
from flask import current_app, render_template, url_for
from extensions import mail


def generate_verification_code():
    """Genera un código de verificación de 8 caracteres alfanuméricos"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(8))

def get_serializer():
    
    from itsdangerous import URLSafeTimedSerializer
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

def generate_verification_token(user_id, code, email):
    """Genera token de verificación consistente"""
    s = get_serializer() 
    return s.dumps({
        'user_id': user_id,
        'code': code,
        'email': email
    }, salt='email-verification')

def send_welcome_email(usuario, verification_code):
    """Envía correo de bienvenida con código de verificación y link directo"""
    try:
        # Usar el mismo serializador consistente
        verification_token = generate_verification_token(
            usuario.id_usuario, 
            verification_code, 
            usuario.correo
        )
        
        verification_url = url_for('auth.verify_email_with_token', token=verification_token, _external=True)
        
        # ✅ DEBUG: Mostrar información del token
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
        print(f"Error enviando correo de bienvenida: {str(e)}")
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
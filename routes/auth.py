# proyecto_sena/routes/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask import current_app
from controllers.models import Usuario
from extensions import db, mail
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message
import os
from datetime import datetime, timedelta
from controllers.forms import LoginForm, ForgotPasswordForm, ResetPasswordForm
from services.email_service import send_welcome_email, send_verification_success_email, generate_verification_code, generate_verification_token

# --- Configuración del Serializador para tokens ---
def get_serializer():
    """✅ CORREGIDO: Serializador unificado que usa la configuración de Flask"""
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

auth_bp = Blueprint('auth', __name__)

ROL_REDIRECTS = {
    1: 'admin.admin_panel',
    2: 'profesor.dashboard',
    3: 'estudiante.estudiante_panel',
    4: 'padre.dashboard'
}

# --- Rutas de Autenticación Principal ---

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        correo = form.correo.data
        password = form.password.data
        user = Usuario.query.filter_by(correo=correo).first()
        
        if user and user.check_password(password):
            # Verificar si el usuario tiene el correo verificado
            if not user.email_verified:
                flash('Por favor verifica tu correo electrónico antes de iniciar sesión.', 'warning')
                return redirect(url_for('auth.verify_email_page', email=correo))
            
            login_user(user)
            flash('Inicio de sesión exitoso.', 'success')
            print(f"Usuario: {user.nombre} {user.apellido}, Rol ID: {user.id_rol_fk}")
            ruta = ROL_REDIRECTS.get(user.id_rol_fk, 'main.index')
            return redirect(url_for(ruta))
        else:
            flash('Inicio de sesión fallido. Por favor, revisa tu correo electrónico y contraseña.', 'danger')
    
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """Cierra la sesión del usuario"""
    logout_user()
    flash('¡Has cerrado sesión!', 'info')
    return redirect(url_for('main.index'))

# --- Rutas de Recuperación de Contraseña ---

def enviar_correo_restablecimiento(usuario):
    """Envía el correo de restablecimiento de contraseña"""
    s = get_serializer()  # ✅ CORREGIDO: Usar serializador unificado
    token = s.dumps(str(usuario.id_usuario), salt='recuperacion-password-salt')
    msg = Message(
        'Restablecimiento de Contraseña',
        sender=os.getenv('MAIL_USERNAME', 'noreply@tudominio.com'),
        recipients=[usuario.correo]
    )
    
    link = url_for('auth.restablecer_password', token=token, _external=True)
    
    # Template HTML mejorado para el correo
    msg.html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #0D3B66; color: white; padding: 20px; text-align: center; }}
            .content {{ background: #f9f9f9; padding: 20px; }}
            .button {{ background: #F95738; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; }}
            .footer {{ background: #ddd; padding: 10px; text-align: center; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Restablecimiento de Contraseña</h1>
            </div>
            <div class="content">
                <p>Hola <strong>{usuario.nombre_completo}</strong>,</p>
                <p>Recibimos una solicitud para restablecer tu contraseña. Haz clic en el siguiente botón para continuar:</p>
                <p style="text-align: center;">
                    <a href="{link}" class="button">Restablecer Contraseña</a>
                </p>
                <p>Si el botón no funciona, copia y pega este enlace en tu navegador:</p>
                <p><code>{link}</code></p>
                <p><strong>Este enlace expirará en 1 hora.</strong></p>
                <p>Si no solicitaste este restablecimiento, ignora este correo.</p>
            </div>
            <div class="footer">
                <p>Este es un mensaje automático, por favor no respondas a este correo.</p>
            </div>
        </div>
    </body>
    </html>
    '''
    
    mail.send(msg)

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Maneja la solicitud de recuperación de contraseña"""
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        correo = form.correo.data
        usuario = Usuario.query.filter_by(correo=correo).first()
        
        if usuario:
            enviar_correo_restablecimiento(usuario)
        
        # Mensaje genérico para evitar la enumeración de correos
        flash('Si la cuenta existe, se ha enviado un correo con las instrucciones para restablecer tu contraseña.', 'info')
        return redirect(url_for('auth.login'))
        
    return render_template('forgot_password.html', form=form)

@auth_bp.route('/restablecer_password/<token>', methods=['GET', 'POST'])
def restablecer_password(token):
    """Maneja el restablecimiento de contraseña con token"""
    try:
        s = get_serializer()  # ✅ CORREGIDO: Usar serializador unificado
        id_usuario = s.loads(token, salt='recuperacion-password-salt', max_age=3600)
    except Exception as e:
        print(f"Error cargando token de restablecimiento: {str(e)}")
        flash('El enlace de restablecimiento es inválido o ha expirado.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    usuario = Usuario.query.get(id_usuario)
    if not usuario:
        flash('El usuario asociado al enlace no existe.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        nueva_password = form.password.data
        usuario.set_password(nueva_password)
        db.session.commit()
        
        # Enviar correo de confirmación
        try:
            msg = Message(
                'Contraseña Actualizada Exitosamente',
                sender=os.getenv('MAIL_USERNAME', 'noreply@tudominio.com'),
                recipients=[usuario.correo]
            )
            msg.html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #28A745; color: white; padding: 20px; text-align: center; }}
                    .content {{ background: #f9f9f9; padding: 20px; }}
                    .footer {{ background: #ddd; padding: 10px; text-align: center; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Contraseña Actualizada</h1>
                    </div>
                    <div class="content">
                        <p>Hola <strong>{usuario.nombre_completo}</strong>,</p>
                        <p>Tu contraseña ha sido actualizada exitosamente.</p>
                        <p>Si no realizaste este cambio, por favor contacta inmediatamente al administrador del sistema.</p>
                    </div>
                    <div class="footer">
                        <p>Este es un mensaje automático, por favor no respondas a este correo.</p>
                    </div>
                </div>
            </body>
            </html>
            '''
            mail.send(msg)
        except Exception as e:
            print(f"Error enviando correo de confirmación: {str(e)}")
        
        flash('Tu contraseña ha sido restablecida con éxito. Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))
            
    return render_template('restablecer_password.html', form=form)

# --- Rutas de Verificación de Email ---

@auth_bp.route('/verify-email/<token>')
def verify_email_with_token(token):
    """✅ CORREGIDO: Solo una función con este nombre - Verificación automática con token desde el correo"""
    try:
        print(f"DEBUG: Token recibido: {token}")
        
        s = get_serializer()
        data = s.loads(token, salt='email-verification', max_age=86400)  # 24 horas
        
        print(f"DEBUG: Datos decodificados: {data}")
        
        user_id = data['user_id']
        code = data['code']
        email = data['email']
        
        usuario = Usuario.query.get(user_id)
        
        if not usuario:
            flash('Usuario no encontrado', 'danger')
            return redirect(url_for('auth.verify_email_page', email=email))
        
        if usuario.email_verified:
            flash('El correo ya ha sido verificado anteriormente', 'success')
            return render_template('auth/verification_success.html', email=email, usuario=usuario)
        
        # Verificar que el código coincida y no haya expirado
        if (usuario.verification_code == code and 
            usuario.verification_code_expires and 
            usuario.verification_code_expires > datetime.utcnow()):
            
            # ✅ OBTENER LA CONTRASEÑA TEMPORAL REAL
            real_password = usuario.temp_password
            
            # Verificación exitosa
            usuario.email_verified = True
            usuario.verification_code = None
            usuario.verification_code_expires = None
            usuario.verification_attempts = 0
            usuario.temp_password = None  # ✅ LIMPIAR CONTRASEÑA TEMPORAL
            db.session.commit()
            
            # Enviar correo de éxito CON LA CONTRASEÑA REAL
            send_verification_success_email(usuario, real_password)
            
            flash('¡Correo verificado exitosamente! Se ha enviado un correo con tus credenciales.', 'success')
            return render_template('auth/verification_success.html', email=email, usuario=usuario)
        else:
            print(f"DEBUG: Código no coincide o expiró. Código en DB: {usuario.verification_code}, Código recibido: {code}")
            flash('El enlace de verificación ha expirado o es inválido', 'danger')
            return redirect(url_for('auth.resend_verification', email=email))
            
    except Exception as e:
        print(f"ERROR en verificación por token: {str(e)}")
        flash('El enlace de verificación es inválido o ha expirado', 'danger')
        return redirect(url_for('auth.login'))

@auth_bp.route('/verify-email', methods=['GET', 'POST'])
def verify_email_page():
    """Página para verificar el código de verificación con límite de intentos"""
    if request.method == 'GET':
        email = request.args.get('email', '')
        return render_template('auth/verify_email.html', email=email, verified=False)
    
    if request.method == 'POST':
        email = request.form.get('email')
        code = request.form.get('verification_code')
        
        if not email or not code:
            flash('Email y código son requeridos', 'danger')
            return render_template('auth/verify_email.html', email=email, verified=False)
        
        usuario = Usuario.query.filter_by(correo=email).first()
        
        if not usuario:
            flash('Usuario no encontrado', 'danger')
            return render_template('auth/verify_email.html', email=email, verified=False)
        
        if usuario.email_verified:
            flash('El correo ya ha sido verificado', 'success')
            return render_template('auth/verify_email.html', email=email, verified=True)
        
        # Verificar límite de intentos
        if usuario.verification_attempts >= 5:
            flash('Has excedido el número máximo de intentos. Por favor solicita un nuevo código.', 'danger')
            return redirect(url_for('auth.resend_verification', email=email))
        
        # Verificar expiración
        if usuario.verification_code_expires and usuario.verification_code_expires < datetime.utcnow():
            flash('El código ha expirado. Por favor solicita uno nuevo.', 'danger')
            return redirect(url_for('auth.resend_verification', email=email))
        
        if usuario.verification_code == code:
            # ✅ OBTENER LA CONTRASEÑA TEMPORAL REAL
            real_password = usuario.temp_password
            
            # Verificación exitosa
            usuario.email_verified = True
            usuario.verification_code = None
            usuario.verification_code_expires = None
            usuario.verification_attempts = 0
            usuario.temp_password = None  # ✅ LIMPIAR CONTRASEÑA TEMPORAL
            db.session.commit()
            
            # Enviar correo de éxito CON LA CONTRASEÑA REAL
            send_verification_success_email(usuario, real_password)
            
            flash('¡Correo verificado exitosamente! Se ha enviado un correo con tus credenciales.', 'success')
            return render_template('auth/verification_success.html', email=email, usuario=usuario)
        else:
            # Incrementar intentos fallidos
            usuario.verification_attempts += 1
            usuario.last_verification_attempt = datetime.utcnow()
            db.session.commit()
            
            intentos_restantes = 5 - usuario.verification_attempts
            flash(f'Código de verificación incorrecto. Te quedan {intentos_restantes} intentos.', 'danger')
            return render_template('auth/verify_email.html', email=email, verified=False)

@auth_bp.route('/resend-verification', methods=['GET', 'POST'])
def resend_verification():
    """Reenvía el código de verificación"""
    if request.method == 'GET':
        email = request.args.get('email', '')
        return render_template('auth/resend_verification.html', email=email)
    
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('El email es requerido', 'danger')
            return render_template('auth/resend_verification.html', email=email)
        
        usuario = Usuario.query.filter_by(correo=email).first()
        
        if not usuario:
            # Por seguridad, no revelar si el email existe
            flash('Si el email existe, se ha enviado un nuevo código de verificación.', 'info')
            return redirect(url_for('auth.verify_email_page', email=email))
        
        if usuario.email_verified:
            flash('Este correo ya ha sido verificado. Puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))
        
        # Generar nuevo código
        new_code = generate_verification_code()
        usuario.verification_code = new_code
        usuario.verification_code_expires = datetime.utcnow() + timedelta(hours=24)
        usuario.verification_attempts = 0
        db.session.commit()
        
        # Reenviar email
        send_welcome_email(usuario, new_code)
        
        flash('Se ha enviado un nuevo código de verificación a tu correo.', 'success')
        return redirect(url_for('auth.verify_email_page', email=email))

@auth_bp.route('/verification-success')
def verification_success():
    """Página de confirmación de verificación exitosa"""
    email = request.args.get('email', '')
    usuario = Usuario.query.filter_by(correo=email).first()
    return render_template('auth/verification_success.html', email=email, usuario=usuario)

@auth_bp.route('/verification-required')
def verification_required():
    """Página que informa al usuario que debe verificar su correo"""
    return render_template('auth/verification_required.html')

# --- Manejo de Errores ---

@auth_bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@auth_bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500
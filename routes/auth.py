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

def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

auth_bp = Blueprint('auth', __name__)

ROL_REDIRECTS = {
    1: 'admin.admin_panel',
    2: 'profesor.dashboard',
    3: 'estudiante.estudiante_panel',
    4: 'padre.dashboard'
}

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        correo = form.correo.data
        password = form.password.data
        user = Usuario.query.filter_by(correo=correo).first()
        
        if user and user.check_password(password):
            
            if hasattr(user, 'activo') and user.activo is False:
                flash('Tu cuenta se encuentra inactiva. Por favor, contacta al administrador del sistema.', 'danger')
                return redirect(url_for('auth.login'))
            
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
    logout_user()
    flash('¡Has cerrado sesión!', 'info')
    return redirect(url_for('main.index'))

def enviar_correo_restablecimiento(usuario):
    s = get_serializer()
    token = s.dumps(str(usuario.id_usuario), salt='recuperacion-password-salt')
    msg = Message(
        'Restablecimiento de Contraseña',
        sender=os.getenv('MAIL_USERNAME', 'noreply@tudominio.com'),
        recipients=[usuario.correo]
    )
    
    link = url_for('auth.restablecer_password', token=token, _external=True)
    
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
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        correo = form.correo.data
        usuario = Usuario.query.filter_by(correo=correo).first()
        
        if usuario:
            enviar_correo_restablecimiento(usuario)
        
        flash('Si la cuenta existe, se ha enviado un correo con las instrucciones para restablecer tu contraseña.', 'info')
        return redirect(url_for('auth.login'))
        
    return render_template('forgot_password.html', form=form)

@auth_bp.route('/restablecer_password/<token>', methods=['GET', 'POST'])
def restablecer_password(token):
    try:
        s = get_serializer()
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

@auth_bp.route('/verify-email/<token>')
def verify_email_with_token(token):
    """El enlace del correo ahora muestra un formulario para verificar por correo + identificación."""
    try:
        s = get_serializer()
        data = s.loads(token, salt='email-verification', max_age=86400)
        email = data.get('email', '')
        return render_template('emails/verify_email.html', email=email, verified=False)
    except Exception as e:
        print(f"ERROR en verificación por token: {str(e)}")
        flash('El enlace de verificación es inválido o ha expirado', 'danger')
        return redirect(url_for('auth.login'))

@auth_bp.route('/verify-email', methods=['GET', 'POST'])
def verify_email_page():
    """Nueva verificación: formulario con email y número de identificación."""
    if request.method == 'GET':
        email = request.args.get('email', '')
        return render_template('emails/verify_email.html', email=email, verified=False)

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        numero_id = request.form.get('no_identidad', '').strip()

        if not email or not numero_id:
            flash('Email y número de identificación son requeridos', 'danger')
            return render_template('emails/verify_email.html', email=email, verified=False)

        user_by_email = Usuario.query.filter_by(correo=email).first()
        if not user_by_email:
            flash('No existe una cuenta con este correo electrónico.', 'danger')
            return render_template('emails/verify_email.html', email=email, verified=False)

        if user_by_email.email_verified:
            flash('El correo ya ha sido verificado', 'success')
            return render_template('emails/verification_success.html', email=email, usuario=user_by_email, password=None, login_url=url_for('auth.login'))

        if str(user_by_email.no_identidad).strip() != numero_id:
            flash('El número de identificación no coincide con este correo.', 'danger')
            return render_template('emails/verify_email.html', email=email, verified=False)

        real_password = getattr(user_by_email, 'temp_password', None)
        if not real_password:
            # Si no hay contraseña temporal, generar una nueva para el usuario
            # y establecerla como contraseña actual
            real_password = generate_verification_code()
            user_by_email.set_password(real_password)
        user_by_email.email_verified = True
        user_by_email.verification_code = None
        user_by_email.verification_code_expires = None
        user_by_email.verification_attempts = 0
        user_by_email.temp_password = None
        db.session.commit()

        send_verification_success_email(user_by_email, real_password)

        flash('¡Correo verificado exitosamente! Se han enviado tus credenciales al correo.', 'success')
        return render_template('emails/verification_success.html', email=email, usuario=user_by_email, password=real_password, login_url=url_for('auth.login'))

@auth_bp.route('/verify-email/check', methods=['POST'])
def verify_email_check():
    """Validación rápida para el formulario (AJAX)."""
    try:
        data = request.get_json() or {}
        email = (data.get('email') or '').strip()
        numero_id = (data.get('no_identidad') or '').strip()
        if not email or not numero_id:
            return jsonify({'ok': False, 'code': 'missing', 'message': 'Email y número de identificación son requeridos'}), 400

        user_by_email = Usuario.query.filter_by(correo=email).first()
        if not user_by_email:
            return jsonify({'ok': False, 'code': 'email_not_found', 'message': 'Correo no encontrado'}), 404
        if user_by_email.email_verified:
            return jsonify({'ok': False, 'code': 'already_verified', 'message': 'Este correo ya fue verificado'}), 409
        if str(user_by_email.no_identidad).strip() != numero_id:
            return jsonify({'ok': False, 'code': 'id_mismatch', 'message': 'Número de identificación incorrecto'}), 422
        return jsonify({'ok': True}), 200
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)}), 500

@auth_bp.route('/resend-verification', methods=['GET', 'POST'])
def resend_verification():
    if request.method == 'GET':
        email = request.args.get('email', '')
        return render_template('emails/resend_verification.html', email=email)

    
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('El email es requerido', 'danger')
            return render_template('emails/resend_verification.html', email=email)
        
        usuario = Usuario.query.filter_by(correo=email).first()
        
        if not usuario:
            flash('Si el email existe, se ha enviado un nuevo código de verificación.', 'info')
            return redirect(url_for('auth.verify_email_page', email=email))
        
        if usuario.email_verified:
            flash('Este correo ya ha sido verificado. Puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))
        
        new_code = generate_verification_code()
        usuario.verification_code = new_code
        usuario.verification_code_expires = datetime.utcnow() + timedelta(hours=24)
        usuario.verification_attempts = 0
        db.session.commit()
        
        send_welcome_email(usuario, new_code)
        
        flash('Se ha enviado un nuevo código de verificación a tu correo.', 'success')
        return redirect(url_for('auth.verify_email_page', email=email))

@auth_bp.route('/verification-success')
def verification_success():
    email = request.args.get('email', '')
    usuario = Usuario.query.filter_by(correo=email).first()
    return render_template('emails/verification_success.html', email=email, usuario=usuario)

@auth_bp.route('/verification-required')
def verification_required():
    return render_template('emails/verification_required.html')

@auth_bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@auth_bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500
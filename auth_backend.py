"""Autenticación de RiTech (PostgreSQL + PBKDF2). No almacena contraseñas en texto plano."""

import hashlib
import hmac
import os
import re
import secrets
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage

from db import conectar
from dotenv import load_dotenv

load_dotenv()

ITERACIONES = 600_000
USUARIO_RE = re.compile(r"^[a-z][a-z0-9_.-]{2,29}$")
CORREO_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def preparar_tablas():
    """Crea únicamente la tabla de cuentas, sin alterar las tablas del simulador."""
    conn = conectar()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS ritech_usuarios (
                        id BIGSERIAL PRIMARY KEY,
                        usuario VARCHAR(30) NOT NULL UNIQUE,
                        correo VARCHAR(254) NOT NULL UNIQUE,
                        contrasena_hash TEXT NOT NULL,
                        recuperacion_hash CHAR(64) NOT NULL,
                        intentos_login INTEGER NOT NULL DEFAULT 0,
                        bloqueo_login_hasta TIMESTAMPTZ,
                        intentos_recuperacion INTEGER NOT NULL DEFAULT 0,
                        bloqueo_recuperacion_hasta TIMESTAMPTZ,
                        codigo_email_hash CHAR(64),
                        codigo_email_expira TIMESTAMPTZ,
                        codigo_email_enviado TIMESTAMPTZ,
                        intentos_email INTEGER NOT NULL DEFAULT 0,
                        creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
    finally:
        conn.close()


def _hash_contrasena(contrasena):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', contrasena.encode('utf-8'), salt, ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${salt.hex()}${digest.hex()}"


def _verificar_contrasena(contrasena, valor):
    try:
        nombre, veces, salt, resultado = valor.split('$')
        if nombre != 'pbkdf2_sha256' or not (100_000 <= int(veces) <= 2_000_000):
            return False
        obtenido = hashlib.pbkdf2_hmac('sha256', contrasena.encode('utf-8'), bytes.fromhex(salt), int(veces))
        return hmac.compare_digest(obtenido, bytes.fromhex(resultado))
    except (ValueError, AttributeError, TypeError):
        return False


def _nuevo_codigo_recuperacion():
    caracteres = secrets.token_hex(12).upper()
    return 'RIT-' + '-'.join(caracteres[i:i+6] for i in range(0, 24, 6))


def _normalizar_codigo(codigo):
    return re.sub(r"[\s-]", "", codigo or "").upper()


def _digest_codigo(codigo):
    return hashlib.sha256(_normalizar_codigo(codigo).encode('utf-8')).hexdigest()


def _validar_contrasena(contrasena):
    if not (8 <= len(contrasena) <= 128):
        return "La contraseña debe tener entre 8 y 128 caracteres."
    if not any(c.isalpha() for c in contrasena) or not any(c.isdigit() for c in contrasena):
        return "La contraseña debe incluir letras y números."
    return None


def registrar(usuario, correo, contrasena, confirmacion):
    usuario = usuario.strip().lower()
    correo = correo.strip().lower()
    if not USUARIO_RE.fullmatch(usuario):
        return False, "El usuario debe tener de 3 a 30 caracteres (letras, números, punto, guion o guion bajo).", None
    if len(correo) > 254 or not CORREO_RE.fullmatch(correo):
        return False, "Escribe un correo electrónico válido.", None
    error = _validar_contrasena(contrasena)
    if error:
        return False, error, None
    if contrasena != confirmacion:
        return False, "Las contraseñas no coinciden.", None

    codigo = _nuevo_codigo_recuperacion()
    clave_hash = _hash_contrasena(contrasena)
    conn = conectar()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ritech_usuarios (usuario, correo, contrasena_hash, recuperacion_hash)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING RETURNING id
                """, (usuario, correo, clave_hash, _digest_codigo(codigo)))
                creado = cur.fetchone()
        if creado is None:
            return False, "Ese usuario o correo ya se encuentra registrado.", None
        return True, "Tu cuenta se creó correctamente.", codigo
    finally:
        conn.close()


def _identidad(identificador):
    return (identificador or '').strip().lower()


def iniciar_sesion(identificador, contrasena):
    identificador = _identidad(identificador)
    mensaje_error = "Datos incorrectos o acceso temporalmente bloqueado. Inténtalo de nuevo."
    if not identificador or not contrasena:
        return False, "Ingresa el usuario/correo y la contraseña."

    conn = conectar()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, usuario, contrasena_hash,
                           bloqueo_login_hasta IS NOT NULL AND bloqueo_login_hasta > NOW()
                    FROM ritech_usuarios
                    WHERE usuario = %s OR correo = %s
                    FOR UPDATE
                """, (identificador, identificador))
                fila = cur.fetchone()
                if fila is None:
                    return False, mensaje_error
                id_usuario, usuario, clave_hash, bloqueada = fila
                if bloqueada:
                    return False, mensaje_error
                if not _verificar_contrasena(contrasena, clave_hash):
                    cur.execute("""
                        UPDATE ritech_usuarios SET
                            intentos_login = CASE WHEN intentos_login >= 4 THEN 0 ELSE intentos_login + 1 END,
                            bloqueo_login_hasta = CASE
                                WHEN intentos_login >= 4 THEN NOW() + INTERVAL '15 minutes'
                                ELSE NULL END
                        WHERE id = %s
                    """, (id_usuario,))
                    return False, mensaje_error
                cur.execute("""
                    UPDATE ritech_usuarios
                    SET intentos_login = 0, bloqueo_login_hasta = NULL
                    WHERE id = %s
                """, (id_usuario,))
                return True, (id_usuario, usuario)
    finally:
        conn.close()


def restablecer_con_codigo(identificador, codigo, nueva, confirmar):
    error = _validar_contrasena(nueva)
    if error:
        return False, error, None
    if nueva != confirmar:
        return False, "Las contraseñas no coinciden.", None
    if not identificador.strip() or not codigo.strip():
        return False, "Completa el usuario/correo y el código de recuperación.", None

    conn = conectar()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, recuperacion_hash,
                           bloqueo_recuperacion_hasta IS NOT NULL AND bloqueo_recuperacion_hasta > NOW()
                    FROM ritech_usuarios WHERE usuario = %s OR correo = %s
                    FOR UPDATE
                """, (_identidad(identificador), _identidad(identificador)))
                fila = cur.fetchone()
                if fila is None:
                    return False, "Identidad o código inválido, o recuperación temporalmente bloqueada.", None
                id_usuario, hash_guardado, bloqueada = fila
                if bloqueada:
                    return False, "Identidad o código inválido, o recuperación temporalmente bloqueada.", None
                if not hmac.compare_digest(_digest_codigo(codigo), hash_guardado.strip()):
                    cur.execute("""
                        UPDATE ritech_usuarios SET
                            intentos_recuperacion = CASE WHEN intentos_recuperacion >= 4 THEN 0 ELSE intentos_recuperacion + 1 END,
                            bloqueo_recuperacion_hasta = CASE
                                WHEN intentos_recuperacion >= 4 THEN NOW() + INTERVAL '15 minutes'
                                ELSE NULL END
                        WHERE id = %s
                    """, (id_usuario,))
                    return False, "Identidad o código inválido, o recuperación temporalmente bloqueada.", None
                nuevo_codigo = _nuevo_codigo_recuperacion()
                cur.execute("""
                    UPDATE ritech_usuarios SET contrasena_hash = %s,
                        recuperacion_hash = %s,
                        intentos_login = 0, bloqueo_login_hasta = NULL,
                        intentos_recuperacion = 0, bloqueo_recuperacion_hasta = NULL,
                        codigo_email_hash = NULL, codigo_email_expira = NULL,
                        intentos_email = 0
                    WHERE id = %s
                """, (_hash_contrasena(nueva), _digest_codigo(nuevo_codigo), id_usuario))
                return True, "Contraseña actualizada correctamente.", nuevo_codigo
    finally:
        conn.close()


def correo_configurado():
    return all(os.getenv(nombre, '').strip() for nombre in ('SMTP_HOST', 'SMTP_FROM'))


def _enviar_correo(destinatario, codigo):
    mensaje = EmailMessage()
    mensaje['Subject'] = 'RiTech | Recuperación de contraseña'
    mensaje['From'] = os.getenv('SMTP_FROM')
    mensaje['To'] = destinatario
    mensaje.set_content(
        'Recibimos una solicitud para recuperar tu contraseña de RiTech.\n\n'
        f'Código de verificación: {codigo}\n\n'
        'Este código vence en 15 minutos. Si no solicitaste el cambio, ignora este correo.\n'
    )
    host = os.environ['SMTP_HOST']
    usar_ssl = os.getenv('SMTP_SSL', 'false').lower() == 'true'
    puerto = int(os.getenv('SMTP_PORT', '465' if usar_ssl else '587'))
    cliente = smtplib.SMTP_SSL(host, puerto, timeout=15) if usar_ssl else smtplib.SMTP(host, puerto, timeout=15)
    with cliente as smtp:
        if not usar_ssl and os.getenv('SMTP_TLS', 'true').lower() == 'true':
            smtp.starttls()
        if os.getenv('SMTP_USER') and os.getenv('SMTP_PASSWORD'):
            smtp.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
        smtp.send_message(mensaje)


def solicitar_codigo_email(identificador):
    """Respuesta genérica para evitar revelar si una cuenta existe."""
    identificador = _identidad(identificador)
    mensaje = 'Si los datos corresponden a una cuenta, recibirás un código en su correo registrado.'
    if not correo_configurado() or not identificador:
        return mensaje

    conn = conectar()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, correo, codigo_email_enviado IS NOT NULL
                        AND codigo_email_enviado > NOW() - INTERVAL '60 seconds'
                    FROM ritech_usuarios WHERE usuario = %s OR correo = %s
                    FOR UPDATE
                """, (identificador, identificador))
                fila = cur.fetchone()
                if fila is None or fila[2]:
                    return mensaje
                id_usuario, correo, _ = fila
                codigo = secrets.token_urlsafe(18)
                # Se envía primero; si el SMTP falla, no se altera el código anterior.
                try:
                    _enviar_correo(correo, codigo)
                except (OSError, smtplib.SMTPException, ValueError):
                    return mensaje
                cur.execute("""
                    UPDATE ritech_usuarios
                    SET codigo_email_hash = %s,
                        codigo_email_expira = NOW() + INTERVAL '15 minutes',
                        codigo_email_enviado = NOW(), intentos_email = 0
                    WHERE id = %s
                """, (_digest_codigo(codigo), id_usuario))
        return mensaje
    finally:
        conn.close()


def restablecer_con_email(identificador, codigo, nueva, confirmar):
    error = _validar_contrasena(nueva)
    if error:
        return False, error, None
    if nueva != confirmar:
        return False, "Las contraseñas no coinciden.", None
    if not identificador.strip() or not codigo.strip():
        return False, "Completa todos los campos.", None

    conn = conectar()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, codigo_email_hash,
                           codigo_email_expira IS NOT NULL AND codigo_email_expira > NOW(),
                           intentos_email
                    FROM ritech_usuarios WHERE usuario = %s OR correo = %s
                    FOR UPDATE
                """, (_identidad(identificador), _identidad(identificador)))
                fila = cur.fetchone()
                mensaje = "Código inválido o vencido. Solicita uno nuevo."
                if fila is None:
                    return False, mensaje, None
                id_usuario, codigo_hash, vigente, intentos = fila
                if not vigente or not codigo_hash or intentos >= 5:
                    return False, mensaje, None
                if not hmac.compare_digest(_digest_codigo(codigo), codigo_hash.strip()):
                    cur.execute("UPDATE ritech_usuarios SET intentos_email = intentos_email + 1 WHERE id = %s", (id_usuario,))
                    return False, mensaje, None
                respaldo_nuevo = _nuevo_codigo_recuperacion()
                cur.execute("""
                    UPDATE ritech_usuarios SET contrasena_hash = %s,
                        recuperacion_hash = %s,
                        codigo_email_hash = NULL, codigo_email_expira = NULL,
                        intentos_email = 0,
                        intentos_login = 0, bloqueo_login_hasta = NULL,
                        intentos_recuperacion = 0, bloqueo_recuperacion_hasta = NULL
                    WHERE id = %s
                """, (_hash_contrasena(nueva), _digest_codigo(respaldo_nuevo), id_usuario))
                return True, "Contraseña actualizada correctamente.", respaldo_nuevo
    finally:
        conn.close()

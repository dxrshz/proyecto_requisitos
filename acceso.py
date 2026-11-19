"""Pantallas de acceso RiTech. Reutiliza el estado de idioma y tema del panel."""

from html import escape

import streamlit as st

from auth_backend import (
    correo_configurado, iniciar_sesion, preparar_tablas, registrar,
    restablecer_con_codigo, restablecer_con_email, solicitar_codigo_email,
)
from idiomas import traducir


def _tr(clave, **variables):
    return traducir(clave, st.session_state.get("idioma", "es"), **variables)


# Backend existente conserva mensajes originales para compatibilidad con pruebas.
ERRORES_BACKEND = {
    "La contraseña debe tener entre 8 y 128 caracteres.": "auth_pw_length",
    "La contraseña debe incluir letras y números.": "auth_pw_mix",
    "El usuario debe tener de 3 a 30 caracteres (letras, números, punto, guion o guion bajo).": "auth_invalid_username",
    "Escribe un correo electrónico válido.": "auth_invalid_email",
    "Las contraseñas no coinciden.": "auth_pw_mismatch",
    "Ese usuario o correo ya se encuentra registrado.": "auth_already_exists",
    "Tu cuenta se creó correctamente.": "auth_register_success",
    "Datos incorrectos o acceso temporalmente bloqueado. Inténtalo de nuevo.": "auth_login_failed",
    "Ingresa el usuario/correo y la contraseña.": "auth_missing_login",
    "Completa el usuario/correo y el código de recuperación.": "auth_backup_missing",
    "Identidad o código inválido, o recuperación temporalmente bloqueada.": "auth_backup_invalid",
    "Contraseña actualizada correctamente.": "auth_reset_success",
    "Si los datos corresponden a una cuenta, recibirás un código en su correo registrado.": "auth_email_generic",
    "Completa todos los campos.": "auth_all_fields",
    "Código inválido o vencido. Solicita uno nuevo.": "auth_email_invalid",
}


def _traducir_mensaje(mensaje):
    return _tr(ERRORES_BACKEND.get(mensaje, mensaje))


def guardar_preferencias():
    """Persiste los ajustes aunque el widget se destruya al cambiar de vista."""
    if "idioma" in st.session_state:
        st.session_state["ritech_pref_idioma"] = st.session_state["idioma"]
    if "tema_oscuro" in st.session_state:
        st.session_state["ritech_pref_tema"] = bool(st.session_state["tema_oscuro"])


ESTILOS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');
.stApp {
  color: #ecf5ff;
  background:
    radial-gradient(ellipse 45% 48% at 12% 22%, rgba(2,178,226,.18), transparent 76%),
    radial-gradient(ellipse 43% 57% at 88% 84%, rgba(113,61,220,.17), transparent 72%),
    linear-gradient(145deg, #050b18 0%, #071426 51%, #070b19 100%);
}
.stApp::before {
  content:""; position:fixed; inset:0; pointer-events:none; opacity:.15;
  background-image:linear-gradient(rgba(132,181,215,.17) 1px, transparent 1px),
                   linear-gradient(90deg,rgba(132,181,215,.17) 1px, transparent 1px);
  background-size:48px 48px; mask-image:linear-gradient(to bottom, black 30%, transparent 100%);
}
header[data-testid="stHeader"] { background:transparent; }
section[data-testid="stSidebar"] { display:none; }
div[data-testid="stDecoration"] {display:none;}
.block-container {max-width:1200px; padding-top:5.3rem; padding-bottom:3rem;}
html, body, div[data-testid="stAppViewContainer"] {font-family:'DM Sans', sans-serif;}
h1, h2, h3 {font-family:'Space Grotesk', sans-serif;}
.rit-topline {color:#8eb9d4;letter-spacing:.24em;font-size:.7rem;font-weight:800;margin-bottom:1.9rem;}
.rit-logo {display:inline-flex;align-items:center;gap:.9rem;margin-bottom:1.5rem;}
.rit-logo-icon {display:inline-grid;place-items:center;width:57px;height:57px;
 border:1px solid rgba(78,240,255,.48);border-radius:18px;color:#59f3fa;font-weight:800;font-size:1.7rem;
 box-shadow:0 0 28px #01d8fb24, inset 0 0 20px #00d4ec12;background:#13bdda0d;}
.rit-logo-word {font:700 2.15rem 'Space Grotesk',sans-serif;letter-spacing:-.065em;color:#f5fbff;}
.rit-logo-word span {color:#4bedfa;}
.rit-hero-h {font:700 clamp(2.9rem,5.2vw,4.6rem)/1.08 'Space Grotesk',sans-serif;
 letter-spacing:-.065em;max-width:650px;color:white;margin:.4rem 0 1.25rem;}
.rit-hero-h em {font-style:normal;color:#50ecf5;}
.rit-hero-sub {font-size:1.02rem;line-height:1.85;color:#9bb1c8;max-width:455px;margin-bottom:2.2rem;}
.rit-hero-tags {display:flex;flex-wrap:wrap;gap:.6rem;margin:0 0 2.5rem;}
.rit-tag {font-weight:700;font-size:.75rem;color:#b1e3ed;border:1px solid #2a5363;
 padding:.5rem .78rem;border-radius:40px;background:#0a2636;letter-spacing:.05em;}
.rit-chart {padding:1rem 1.2rem .4rem; border:1px solid rgba(95,188,218,.24);border-radius:18px;
 background:linear-gradient(135deg,rgba(16,42,67,.76),rgba(10,18,40,.65));max-width:495px;
 box-shadow:0 18px 70px rgba(0,0,0,.21);}
.rit-chart .smallcap {font-size:.69rem;letter-spacing:.2em;color:#76a7bd;font-weight:800;}
.rit-chart .stat {font:700 1.7rem 'Space Grotesk',sans-serif;color:#f2fbff;margin:.45rem 0 .3rem;}
.rit-chart .stat span {font:700 .8rem 'DM Sans',sans-serif;color:#4ee4b2;margin-left:.5rem;}
.rit-form-title {font:700 1.85rem 'Space Grotesk',sans-serif;color:#f9fcff;letter-spacing:-.045em;margin:.9rem 0 .35rem;}
.rit-form-sub {color:#9eb0c6;font-size:.89rem;margin:0 0 1.2rem;}
.rit-security {color:#62e1d9;font-weight:800;font-size:.7rem;letter-spacing:.2em;margin:0 0 .7rem;}
.rit-bottom {font-size:.75rem;color:#698ba1;margin-top:1.2rem;}
div[data-testid="stForm"] {background:rgba(11,25,46,.88);border:1px solid rgba(101,163,199,.26);
 border-radius:22px;padding:1.5rem 1.65rem 1.35rem;box-shadow:0 20px 85px rgba(0,0,0,.30), inset 0 1px 0 #ffffff0b;}
div[data-testid="stForm"] label {color:#d7e7f4!important;font-size:.85rem;font-weight:600;}
div[data-testid="stTextInput"] input {background:#09172b!important;color:#f4fbff!important;
 border:1px solid #2d4662!important;border-radius:11px!important;min-height:47px!important;}
div[data-testid="stTextInput"] input:focus {border-color:#40deeb!important;box-shadow:0 0 0 1px #40deeb44!important;}
button[kind="primaryFormSubmit"], div[data-testid="stFormSubmitButton"] button[kind="primary"] {
 background:linear-gradient(100deg,#16c9dc,#338af1)!important;color:#031126!important;
 font-weight:800!important;border:none!important;border-radius:11px!important;min-height:46px!important;
 box-shadow:0 8px 28px #10bdde38!important;}
button[kind="secondary"] {background:rgba(15,37,59,.75)!important;color:#bfe6f2!important;
 border:1px solid #2e5367!important;border-radius:10px!important;}
button[kind="secondary"]:hover {border-color:#46dee8!important;color:#fff!important;}
[data-testid="stAlert"] {border-radius:12px;}
@media (max-width:750px) {.block-container{padding-top:2rem;} .rit-hero-h{font-size:2.6rem;}
.rit-chart{display:none;} .rit-hero-sub{margin-bottom:.8rem;} .rit-hero-tags{margin-bottom:1rem;}}
</style>
"""

ESTILOS_CLAROS = """
<style>
.stApp {
 color:#132e49!important;
 background:radial-gradient(ellipse 48% 60% at 15% 15%, #d2f5ff 0%, transparent 80%),
            radial-gradient(ellipse 48% 55% at 90% 90%, #e9dcff 0%, transparent 79%),
            linear-gradient(145deg,#f9fcff 0%,#edf5fc 56%,#f8faff 100%)!important;
}
.stApp::before {opacity:.45; background-image:linear-gradient(#b9d5e8 1px, transparent 1px),linear-gradient(90deg,#b9d5e8 1px,transparent 1px);}
.rit-topline,.rit-security {color:#096d83!important;}
.rit-logo-word,.rit-hero-h,.rit-form-title {color:#0b2541!important;}
.rit-logo-word span,.rit-hero-h em {color:#047c9e!important;}
.rit-hero-sub,.rit-form-sub,.rit-bottom {color:#496784!important;}
.rit-tag {color:#14627c;background:#e4f7fc;border-color:#a7dce8;}
.rit-chart {background:linear-gradient(130deg,#f8feff,#e3eefb);border-color:#b7d6e6;box-shadow:0 18px 50px #315b8214;}
.rit-chart .smallcap {color:#497996!important;}
.rit-chart .stat {color:#183e59!important;}
.rit-chart .stat span {color:#087c65!important;}
.rit-logo-icon {background:#e0faff;border-color:#3ea8d0;color:#057a9b;}
div[data-testid="stForm"] {background:rgba(255,255,255,.85);border-color:#bfd7e8;box-shadow:0 18px 55px #315b821b;}
div[data-testid="stForm"] label {color:#173f60!important;}
div[data-testid="stTextInput"] input {background:#fff!important;color:#193c56!important;border-color:#b7d3e5!important;}
div[data-testid="stTextInput"] input:focus {border-color:#1498ba!important;box-shadow:0 0 0 1px #16a5cf44!important;}
[data-testid="stTextInput"] input::placeholder {color: #64748B !important;-webkit-text-fill-color: #64748B !important;opacity: 1 !important;}
button[kind="secondary"] {background:#f3fafd!important;color:#17506e!important;border-color:#b2d9e6!important;}
button[kind="secondary"]:hover {color:#053652!important;border-color:#1d91ae!important;}
[data-testid="stRadio"] label,[data-testid="stToggle"] label {color:#173f60!important;}
[data-baseweb="select"] > div {background:#fff!important; color:#123d5c!important; border:1px solid #b7d3e5!important;}
[data-testid="stCaptionContainer"] p {color:#45627b!important;}
[data-testid="stCheckbox"] label p,
[data-testid="stCheckbox"] label span,
[data-testid="stWidgetLabel"] p {color: #1F2328 !important;font-weight: 500;}
[data-testid="stCheckbox"] label > div:first-of-type{background-color: #94A3B8 !important;border: 1.5px solid #475569 !important;opacity: 1 !important;}
[data-testid="stCheckbox"] label > div:first-of-type > div{background-color: #FFFFFF !important;box-shadow: 0 1px 3px rgba(0, 0, 0, 0.35) !important;}
[data-testid="stAlert"],[data-testid="stAlert"] p,[data-testid="stAlert"] span,[data-testid="stAlert"] div {color: #1F2328 !important;font-weight: 500 !important;opacity: 1 !important;}
[data-testid="stAlert"] [data-baseweb="notification"][kind="negative"] {background-color: #FEE2E2 !important;border: 1px solid #EF4444 !important;}
</style>
"""


def _hero():
    return f"""
<div class="rit-topline">◉&nbsp; {escape(_tr('auth_brandline'))}</div>
<div class="rit-logo"><div class="rit-logo-icon">R</div>
 <div class="rit-logo-word">Ri<span>Tech</span><span style="color:#91a6b9;font-size:.7rem;vertical-align:top;letter-spacing:0">&nbsp; / 01</span></div>
</div>
<div class="rit-hero-h">{escape(_tr('auth_hero_line1'))}<br><em>{escape(_tr('auth_hero_line2'))}</em></div>
<div class="rit-hero-sub">{escape(_tr('auth_hero_desc'))}</div>
<div class="rit-hero-tags"><span class="rit-tag">✦ {escape(_tr('auth_tag_analytics'))}</span><span class="rit-tag">⌁ NASDAQ</span><span class="rit-tag">⬡ {escape(_tr('auth_tag_security'))}</span></div>
<div class="rit-chart">
  <div class="smallcap">● {escape(_tr('auth_chart_label'))}</div>
  <div class="stat">{escape(_tr('auth_chart_main'))} <span>↗ {escape(_tr('auth_chart_status'))}</span></div>
  <svg width="100%" height="126" viewBox="0 0 480 126" role="img" aria-label="Market illustration / Ilustración del mercado">
    <defs><linearGradient id="ritGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#21e5ec" stop-opacity=".33"/><stop offset="1" stop-color="#21e5ec" stop-opacity="0"/></linearGradient></defs>
    <path d="M0 99 H480 M0 66 H480 M0 33 H480" stroke="#54829c" stroke-width="1" stroke-dasharray="3 6"/>
    <path d="M0 103 L37 91 74 97 111 60 148 69 185 76 222 51 259 64 296 34 333 47 370 29 407 40 444 16 480 8 L480 126 L0 126Z" fill="url(#ritGrad)"/>
    <path d="M0 103 L37 91 74 97 111 60 148 69 185 76 222 51 259 64 296 34 333 47 370 29 407 40 444 16 480 8" fill="none" stroke="#159fad" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>
    <circle cx="480" cy="8" r="4.5" fill="#10bdbc"/>
  </svg>
</div>
"""


def _encabezado_form(etiqueta, titulo, subtitulo):
    st.markdown(
        f'<div class="rit-security">⟡ &nbsp; {escape(_tr(etiqueta))}</div>'
        f'<div class="rit-form-title">{escape(_tr(titulo))}</div>'
        f'<p class="rit-form-sub">{escape(_tr(subtitulo))}</p>',
        unsafe_allow_html=True,
    )


def _cambiar(pantalla):
    st.session_state["ritech_pantalla"] = pantalla
    st.rerun()


def _mostrar_codigo_final():
    st.success(_tr(st.session_state.get("ritech_mensaje_final", "auth_done")))
    st.warning(_tr("auth_keep_code"))
    st.code(st.session_state.get("ritech_codigo_temporal", ""), language=None)
    if st.button(_tr("auth_understood"), type="primary", use_container_width=True):
        st.session_state.pop("ritech_codigo_temporal", None)
        st.session_state.pop("ritech_mensaje_final", None)
        _cambiar("login")


def _vista_login():
    _encabezado_form("auth_login_caption", "auth_welcome", "auth_welcome_sub")
    with st.form("ritech_login_form"):
        identidad = st.text_input(_tr("auth_identity"), placeholder="usuario / email@example.com")
        clave = st.text_input(_tr("auth_password"), type="password", placeholder="••••••••")
        enviar = st.form_submit_button(_tr("auth_login"), type="primary", use_container_width=True)
    if enviar:
        try:
            ok, respuesta = iniciar_sesion(identidad, clave)
            if ok:
                st.session_state["ritech_usuario_id"] = respuesta[0]
                st.session_state["ritech_usuario"] = respuesta[1]
                st.session_state["ritech_autenticado"] = True
                st.rerun()
            else:
                st.error(_traducir_mensaje(respuesta))
        except Exception:
            st.error(_tr("auth_generic_fail"))

    if st.button(_tr("auth_forgot"), key="ritech_go_reset", use_container_width=True):
        _cambiar("recuperar")
    st.markdown(f'<div class="rit-bottom">{escape(_tr("auth_no_account"))}</div>', unsafe_allow_html=True)
    if st.button(_tr("auth_create_account"), key="ritech_go_register", use_container_width=True):
        _cambiar("registro")


def _vista_registro():
    _encabezado_form("auth_new_caption", "auth_join", "auth_join_sub")
    with st.form("ritech_registro_form"):
        usuario = st.text_input(_tr("auth_username"), placeholder="francisco_01")
        correo = st.text_input(_tr("auth_email"), placeholder="email@example.com")
        clave = st.text_input(_tr("auth_password"), type="password", placeholder=_tr("auth_password_hint"))
        confirmar = st.text_input(_tr("auth_confirm_password"), type="password")
        enviar = st.form_submit_button(_tr("auth_create"), type="primary", use_container_width=True)
    if enviar:
        try:
            ok, mensaje, codigo = registrar(usuario, correo, clave, confirmar)
            if ok:
                st.session_state["ritech_codigo_temporal"] = codigo
                st.session_state["ritech_mensaje_final"] = ERRORES_BACKEND.get(mensaje, mensaje)
                _cambiar("codigo_final")
            else:
                st.error(_traducir_mensaje(mensaje))
        except Exception:
            st.error(_tr("auth_generic_fail"))
    if st.button(_tr("auth_have_account"), use_container_width=True):
        _cambiar("login")


def _vista_recuperar():
    _encabezado_form("auth_recover_caption", "auth_recover_title", "auth_recover_sub")
    # Stable values 'respaldo'/'correo' avoid resetting selection on translation changes.
    metodo = st.radio(
        _tr("auth_recover_method"), ["respaldo", "correo"],
        format_func=lambda codigo: _tr("auth_backup_method" if codigo == "respaldo" else "auth_email_method"),
        horizontal=True, key="ritech_metodo",
    )
    if metodo == "respaldo":
        st.caption(_tr("auth_backup_hint"))
        with st.form("ritech_reset_respaldo"):
            identidad = st.text_input(_tr("auth_identity"))
            codigo = st.text_input(_tr("auth_recovery_code"), placeholder="RIT-XXXXXX-XXXXXX-XXXXXX-XXXXXX")
            nueva = st.text_input(_tr("auth_new_password"), type="password")
            confirmar = st.text_input(_tr("auth_confirm_new_password"), type="password")
            enviar = st.form_submit_button(_tr("auth_reset"), type="primary", use_container_width=True)
        if enviar:
            try:
                ok, mensaje, respaldo = restablecer_con_codigo(identidad, codigo, nueva, confirmar)
                if ok:
                    st.session_state["ritech_codigo_temporal"] = respaldo
                    st.session_state["ritech_mensaje_final"] = ERRORES_BACKEND.get(mensaje, mensaje)
                    _cambiar("codigo_final")
                else:
                    st.error(_traducir_mensaje(mensaje))
            except Exception:
                st.error(_tr("auth_generic_fail"))
    else:
        if not correo_configurado():
            st.info(_tr("auth_email_not_configured"))
        else:
            with st.form("ritech_pedir_codigo_correo"):
                identidad = st.text_input(_tr("auth_identity"), key="ritech_identidad_pedir")
                enviar_codigo = st.form_submit_button(_tr("auth_email_send"), use_container_width=True)
            if enviar_codigo:
                try:
                    st.info(_traducir_mensaje(solicitar_codigo_email(identidad)))
                except Exception:
                    st.error(_tr("auth_email_fail"))
            with st.form("ritech_reset_correo"):
                identidad = st.text_input(_tr("auth_identity"), key="ritech_identidad_recibir")
                codigo = st.text_input(_tr("auth_email_code"))
                nueva = st.text_input(_tr("auth_new_password"), type="password", key="ritech_nueva_correo")
                confirmar = st.text_input(_tr("auth_confirm_new_password"), type="password", key="ritech_confirmar_correo")
                enviar = st.form_submit_button(_tr("auth_confirm_reset"), type="primary", use_container_width=True)
            if enviar:
                try:
                    ok, mensaje, respaldo = restablecer_con_email(identidad, codigo, nueva, confirmar)
                    if ok:
                        st.session_state["ritech_codigo_temporal"] = respaldo
                        st.session_state["ritech_mensaje_final"] = ERRORES_BACKEND.get(mensaje, mensaje)
                        _cambiar("codigo_final")
                    else:
                        st.error(_traducir_mensaje(mensaje))
                except Exception:
                    st.error(_tr("auth_generic_fail"))
    if st.button(_tr("auth_back_to_login"), use_container_width=True):
        _cambiar("login")


def requerir_acceso():
    """No renderiza el simulador si no hay sesión autenticada."""
    if (st.session_state.get("ritech_autenticado")
            and st.session_state.get("ritech_usuario")
            and isinstance(st.session_state.get("ritech_usuario_id"), int)
            and not isinstance(st.session_state["ritech_usuario_id"], bool)
            and st.session_state["ritech_usuario_id"] > 0):
        return

    st.session_state.setdefault("idioma", st.session_state.get("ritech_pref_idioma", "es"))
    st.session_state.setdefault("tema_oscuro", st.session_state.get("ritech_pref_tema", True))
    st.markdown(ESTILOS, unsafe_allow_html=True)
    if not st.session_state["tema_oscuro"]:
        st.markdown(ESTILOS_CLAROS, unsafe_allow_html=True)

    _, c_idioma, c_tema = st.columns([2.9, 1.15, 1.0], gap="medium")
    with c_idioma:
        st.selectbox(
            "Idioma / Language", options=["es", "en"],
            format_func=lambda codigo: "🇪🇸 Español" if codigo == "es" else "🇺🇸 English",
            label_visibility="collapsed", key="idioma", on_change=guardar_preferencias,
            )
    with c_tema:
        st.toggle(_tr("dark_mode"),
                  key="tema_oscuro", on_change=guardar_preferencias)

    try:
        if not st.session_state.get("ritech_auth_tablas_listas"):
            preparar_tablas()
            st.session_state["ritech_auth_tablas_listas"] = True
    except Exception:
        st.error(_tr("auth_db_fail"))
        st.stop()

    st.session_state.setdefault("ritech_pantalla", "login")
    izquierda, derecha = st.columns([1.08, .92], gap="large")
    with izquierda:
        st.markdown(_hero(), unsafe_allow_html=True)
    with derecha:
        modo = st.session_state["ritech_pantalla"]
        if modo == "registro":
            _vista_registro()
        elif modo == "recuperar":
            _vista_recuperar()
        elif modo == "codigo_final":
            _mostrar_codigo_final()
        else:
            _vista_login()
    st.stop()


def cerrar_sesion():
    """Cierra sesión sin eliminar preferencias de tema o idioma."""
    guardar_preferencias()
    # Se limpian los widgets con datos de la cuenta anterior, no solo la sesión.
    for clave in (
        "ritech_autenticado", "ritech_usuario", "ritech_usuario_id",
        "ritech_auto_actualizado", "ritech_codigo_temporal", "ritech_mensaje_final",
        "msg_update", "ultima_alerta_toast", "mostrar_alertas", "capital_inicial",
        "moneda", "fecha_inversion", "umbral_perdida", "umbral_ganancia",
    ):
        st.session_state.pop(clave, None)
    st.session_state["ritech_pantalla"] = "login"
    st.rerun()

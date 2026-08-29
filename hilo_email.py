import threading
import time
import smtplib
import msal
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Configuración de la aplicación registrada en Azure
client_id = 'b550793b-5f0e-4a95-8a23-0bb51d8298e0'  # ID de la aplicación
client_secret = '4JS8Q~SbWcVM5o_DI1Q0O5yY409FC8rfjnqOwbI9'  # Secreto de la aplicación
tenant_id = 'c3d81ad4-ba76-455b-9a0c-56e386330387'  # ID de tu inquilino en Azure AD
authority = f"https://login.microsoftonline.com/{tenant_id}"

# Obtener el token de acceso con MSAL
def get_oauth_token():
    app = msal.ConfidentialClientApplication(
        client_id,
        client_credential=client_secret,
        authority=authority
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" in result:
        print("Token obtenido correctamente:\n", result["access_token"])  # Depuración del token
        return result["access_token"]
    else:
        print("Error al obtener token:", result)  # Depuración del error
        raise Exception("No se pudo obtener el token de acceso.")


import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(subject, body, to_email):
    # Configuración de datos del correo
    from_email = "nexelix@hotmail.com"  # Reemplaza con tu correo
    password = "xpukrycmhlssimxg"       # Reemplaza con tu contraseña o token de aplicación

    # Crear el objeto del mensaje
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Conectar al servidor SMTP de Office 365
        server = smtplib.SMTP('smtp.office365.com', 587)  # Usar puerto 587 para STARTTLS
        server.set_debuglevel(1)  # Activar la depuración para ver los detalles de la comunicación

        # Enviar el saludo EHLO
        server.ehlo()  # Enviar el comando EHLO
        server.starttls()  # Habilitar TLS para la seguridad

        # Enviar nuevamente EHLO después de STARTTLS
        server.ehlo()

        # Iniciar sesión con OAuth2 (ya que estás usando OAuth2 para la autenticación)
        server.login(from_email, password)

        # Enviar el correo
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print("Correo enviado con éxito")

    except Exception as e:
        print(f"Error al enviar correo: {e}")


    time.sleep(2)
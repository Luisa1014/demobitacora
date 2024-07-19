import streamlit as st
import azure.cognitiveservices.speech as speechsdk
from azure.storage.blob import BlobServiceClient, ContentSettings
from fpdf import FPDF
from io import BytesIO
import os
import cv2
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext
import time

# Configuración de Azure
def get_speech_config():
    speech_key = '999fcb4d3f34436ab454ec47920febe0'
    service_region = 'centralus'
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.speech_recognition_language = "es-CO"
    speech_config.speech_synthesis_language = "es-CO"
    speech_config.speech_synthesis_voice_name = "es-CO-GonzaloNeural"
    speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "8000")
    return speech_config

def get_blob_service_client():
    connect_str = 'DefaultEndpointsProtocol=https;AccountName=registrobitacora;AccountKey=y1ypSZq0b/bhuADyaLzu7SWLPWhIYVgM3TGa1Ux4q/66eAU7XdPm2xBaiUGM96rIce76+nenCFWs+AStSDfYmA==;EndpointSuffix=core.windows.net'
    return BlobServiceClient.from_connection_string(connect_str)

def get_sharepoint_context():
    site_url = "https://iacsas-my.sharepoint.com/personal/luisa_molina_iac_com_co/Lists/UsuariosRegistrados/AllItems.aspx?env=WebViewList"
    client_id = "2468f4be-6cc7-4c29-afe4-0d64f6ff44ff"
    client_secret = "yQZ8Q~5eNCLiG3JMKweuj5dTgGT2D4gltiNMYaYs"

    auth_context = AuthenticationContext(site_url)
    if auth_context.acquire_token_for_app(client_id, client_secret):
        ctx = ClientContext(site_url, auth_context)
    else:
        print("Failed to acquire token")

def save_to_sharepoint(ctx, list_name, item_properties):
    list_obj = ctx.web.lists.get_by_title(list_name)
    item_create_info = list_obj.add_item(item_properties)
    ctx.execute_query()
    st.success("Usuario registrado correctamente en SharePoint.")

def create_pdf(responses, image_path):
    pdf = FPDF()
    pdf.add_page()

    # Agregar texto
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    for key, value in responses.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)

    # Agregar imagen
    if image_path:
        pdf.ln(10)
        pdf.image(image_path, x=10, y=pdf.get_y(), w=100)

    # Guardar en un buffer
    pdf_output = BytesIO()
    pdf.output(pdf_output, 'S')  # 'S' para devolver como string
    pdf_output.seek(0)  # Volver al inicio del buffer para leerlo más tarde
    return pdf_output.getvalue()

def save_to_blob(responses, image_path):
    container_name = 'registros'
    pdf_data = create_pdf(responses, image_path)
    
    try:
        container_client = blob_service_client.get_container_client(container_name)
        
        # Guardar el PDF en el blob
        pdf_blob_name = "registro_1.pdf"
        pdf_blob_client = container_client.get_blob_client(pdf_blob_name)
        pdf_blob_client.upload_blob(pdf_data, overwrite=True, content_settings=ContentSettings(content_type='application/pdf'))
        
        st.success("Datos y imagen guardados correctamente.")
    except Exception as e:
        st.error(f"Error al guardar datos: {e}")
        
def speak_and_listen(prompt):
    st.write(prompt)
    speech_synthesizer.speak_text_async(prompt)
    result = speech_recognizer.recognize_once()
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        st.write("No se reconoció ninguna respuesta, por favor inténtalo de nuevo.")
    elif result.reason == speechsdk.ResultReason.Canceled:
        st.write("Error en el reconocimiento de voz. Inténtalo de nuevo.")
    return None

# Clase para manejar la captura de video
class VideoTransformer(VideoTransformerBase):
    def __init__(self):
        self.frame = None

    def transform(self, frame):
        self.frame = frame.to_ndarray(format="bgr24")
        return self.frame

    def get_frame(self):
        return self.frame

# Configuración de Azure
speech_config = get_speech_config()
speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config)
blob_service_client = get_blob_service_client()

# Aplicación principal
st.image("logo.png", width=200)

if "screen" not in st.session_state:
    st.session_state.screen = "login"

if "responses" not in st.session_state:
    st.session_state.responses = {}

if "image_path" not in st.session_state:
    st.session_state.image_path = None

if st.session_state.screen == "login":
    st.header("Iniciar Sesión")
    doc_number = st.text_input("Número de Documento")
    password = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        # Lógica de autenticación
        st.session_state.screen = "main"

    if st.button("Registrarse"):
        st.session_state.screen = "register"

elif st.session_state.screen == "register":
    st.header("Registro de Usuario")
    name = st.text_input("Nombre")
    doc_number = st.text_input("Número de Documento")
    phone = st.text_input("Número Celular")
    email = st.text_input("Correo")
    password = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        ctx = get_sharepoint_context()
        if ctx:
            item_properties = {
                'Título': name,
                'numero documento': doc_number,
                'numero celular': phone,
                'correo': email,
                'contraseña': password
            }
            save_to_sharepoint(ctx, 'UsuariosRegistrados', item_properties)
        st.session_state.screen = "login"

elif st.session_state.screen == "main":
    st.header("Pantalla Principal")
    if st.button("Iniciar Registro"):
        st.session_state.screen = "bitacora"

elif st.session_state.screen == "bitacora":
    st.header("Registro de Bitácora")

    if "completed" not in st.session_state:
        st.session_state.completed = False

    if not st.session_state.completed:
        fields = ["Compañía", "Especialidad", "Descripción de actividades realizadas", "Responsable", "Fecha de entrega actividad", "Estado de la actividad"]
        for field in fields:
            if field not in st.session_state.responses:
                response = speak_and_listen(f"¿Cuál es la {field}?.")
                if response:
                    st.write(f"{field.capitalize()}: {response}")
                    st.session_state.responses[field] = response
                    time.sleep(3)
                else:
                    st.write(f"No se recibió una respuesta válida para {field}.")
                    st.session_state.responses[field] = "No se recibió una respuesta válida"
        st.session_state.completed = True

    if st.session_state.completed:
        st.subheader("Adjuntar Imagen")
        webrtc_ctx = webrtc_streamer(key="example", video_transformer_factory=VideoTransformer)

        if st.button("Tomar Foto"):
            if webrtc_ctx.video_transformer:
                frame = webrtc_ctx.video_transformer.get_frame()
                if frame is not None:
                    if not os.path.exists("temp"):
                        os.makedirs("temp")
                    
                    st.session_state.image_path = os.path.join("temp", "captured_image.png")
                    cv2.imwrite(st.session_state.image_path, frame)
                    st.image(st.session_state.image_path, caption='Imagen Capturada', use_column_width=True)

        if st.button("Confirmar"):
            save_to_blob(st.session_state.responses, st.session_state.image_path)
            st.session_state.screen = "main"
            st.session_state.responses = {}
            st.session_state.image_path = None
            st.session_state.completed = False

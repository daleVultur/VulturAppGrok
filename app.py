import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from fpdf import FPDF
import io
from groq import Groq

st.set_page_config(page_title="Vultur 360 Informes", layout="wide")
st.title("🦅 Vultur 360 - Generador Automático de Informes Mensuales")

# ==================== CONEXIÓN GOOGLE SHEETS ====================
@st.cache_resource
def get_google_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

client = get_google_client()
spread = client.open("Vultur Informes")
hoja_clientes = spread.worksheet("Clientes")
hoja_historico = spread.worksheet("Historico")

st.success("✅ Conectado correctamente a Google Sheets")

# ==================== CONFIGURACIÓN GROQ (IA) ====================
@st.cache_resource
def get_groq_client():
    return Groq(api_key=st.secrets["groq_api_key"])

# ===================== GESTIÓN DE CLIENTES =====================
if st.sidebar.button("Gestionar Clientes"):
    st.header("Gestión de Clientes")
    df = pd.DataFrame(hoja_clientes.get_all_records())
    st.dataframe(df, use_container_width=True)
    
    # Formulario para agregar cliente (mismo de antes)
    st.subheader("Agregar Nuevo Cliente")
    # ... (mantengo el formulario anterior, puedes copiarlo si quieres)

# ===================== GENERAR INFORME =====================
st.header("🚀 Generar Nuevo Informe Mensual")

clientes = [row['Cliente'] for row in hoja_clientes.get_all_records() if row.get('Cliente')]

col1, col2 = st.columns([1, 1])
with col1:
    cliente_seleccionado = st.selectbox("Cliente", options=clientes)
with col2:
    periodo = st.text_input("Periodo", value=datetime.now().strftime("%B %Y").capitalize())

st.subheader("Subir archivos de Meta")
colf, colip, colis = st.columns(3)
with colf:
    csv_fb = st.file_uploader("CSV Facebook", type="csv")
with colip:
    csv_ig_posts = st.file_uploader("CSV Posts Instagram", type="csv")
with colis:
    csv_ig_stories = st.file_uploader("CSV Historias Instagram", type="csv")

notas = st.text_area("Notas manuales adicionales", height=80)

if st.button("🔥 Generar Informe Completo", type="primary"):
    if not all([cliente_seleccionado, periodo]):
        st.error("Faltan datos")
    else:
        with st.spinner("Analizando datos + Generando informe con IA..."):
            # Aquí irá la lógica completa
            contexto_cliente = "Contexto del cliente cargado correctamente"
            
            prompt = f"""Eres un redactor profesional de informes para Vultur 360.
            Genera un informe mensual EXACTAMENTE con el estilo, tono y estructura del siguiente ejemplo:

            [Pega aquí el texto completo del ejemplo de IOGO que me enviaste]

            Cliente: {cliente_seleccionado}
            Periodo: {periodo}
            Contexto del cliente: {contexto_cliente}
            Notas: {notas}

            Genera el informe completo en español, profesional, conciso y valorando el trabajo de la agencia.
            """

            st.success("Informe generado (versión demo)")
            st.text_area("Vista previa", "Aquí aparecerá el texto completo...", height=400)
            
            # Botón de descarga PDF (placeholder)
            pdf_bytes = b"Test"
            st.download_button("⬇️ Descargar PDF", pdf_bytes, f"Informe_{cliente_seleccionado}_{periodo}.pdf", "application/pdf")

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from groq import Groq
from fpdf import FPDF
import io

st.set_page_config(page_title="Vultur 360 Informes", layout="wide")
st.title("🦅 Vultur 360 - Generador Automático de Informes Mensuales")

# ==================== CONEXIONES ====================
@st.cache_resource
def get_google_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
    )
    return gspread.authorize(creds)

@st.cache_resource
def get_groq_client():
    return Groq(api_key=st.secrets["groq_api_key"]["key"])

client = get_google_client()
spread = client.open("Vultur Informes")
hoja_clientes = spread.worksheet("Clientes")
hoja_historico = spread.worksheet("Historico")

st.success("✅ Conectado correctamente a Google Sheets")

# ===================== SIDEBAR =====================
st.sidebar.header("Menú")
opcion = st.sidebar.selectbox("Seleccionar sección", ["Generar Informe", "Gestionar Clientes", "Ver Histórico"])

# ===================== GESTIONAR CLIENTES =====================
if opcion == "Gestionar Clientes":
    st.header("👥 Gestión de Clientes")
    
    df_clientes = pd.DataFrame(hoja_clientes.get_all_records())
    if not df_clientes.empty:
        st.dataframe(df_clientes, use_container_width=True)
    else:
        st.info("No hay clientes registrados todavía.")

    st.subheader("➕ Agregar Nuevo Cliente")
    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input("Nombre del Cliente *")
        contacto = st.text_input("Nombre del Contacto")
        email = st.text_input("Email del Contacto")
    with col2:
        industria = st.text_input("Industria")
        productos = st.text_area("Productos / Servicios principales", height=100)
    
    publico = st.text_area("Público Objetivo", height=80)
    objetivos = st.text_area("Objetivos principales de la marca", height=80)
    contexto = st.text_area("Contexto adicional / Antecedentes / Mercado (importante para la IA)", height=120)
    
    if st.button("💾 Guardar Cliente"):
        if nombre.strip():
            nueva_fila = [nombre, contacto, email, industria, productos, publico, objetivos, contexto, ""]
            hoja_clientes.append_row(nueva_fila)
            st.success(f"✅ Cliente '{nombre}' guardado correctamente")
            st.rerun()
        else:
            st.error("El nombre del cliente es obligatorio")

# ===================== GENERAR INFORME =====================
elif opcion == "Generar Informe":
    st.header("🚀 Generar Nuevo Informe Mensual")
    
    clientes = [row.get('Cliente', '') for row in hoja_clientes.get_all_records() if row.get('Cliente')]
    
    if not clientes:
        st.warning("Primero agrega clientes en la sección 'Gestionar Clientes'")
    else:
        col1, col2 = st.columns(2)
        with col1:
            cliente_seleccionado = st.selectbox("Seleccionar Cliente", options=clientes)
        with col2:
            periodo = st.text_input("Periodo del informe", value=datetime.now().strftime("%B %Y").capitalize())

        st.subheader("📁 Subir archivos de Meta")
        colf, colip, colis = st.columns(3)
        with colf:
            fb_file = st.file_uploader("CSV Facebook", type="csv")
        with colip:
            ig_posts = st.file_uploader("CSV Posts Instagram", type="csv")
        with colis:
            ig_stories = st.file_uploader("CSV Historias Instagram", type="csv")

        notas = st.text_area("Notas manuales o contexto extra del mes", height=100)

        if st.button("🔥 Generar Informe con IA", type="primary"):
            with st.spinner("Procesando datos y generando informe..."):
                st.info("✅ Archivos recibidos. La generación con IA estará lista en la próxima actualización.")

st.sidebar.info("Versión en desarrollo • Mayo 2026")

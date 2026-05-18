import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Vultur 360 Informes", layout="wide")
st.title("🦅 Vultur 360 - Generador Automático de Informes")

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

st.success("✅ Conectado a Google Sheets")

# Sidebar
opcion = st.sidebar.selectbox("Seleccionar opción", 
    ["Generar Nuevo Informe", "Gestionar Clientes", "Ver Histórico"])

if opcion == "Gestionar Clientes":
    st.header("Gestión de Clientes")
    df = pd.DataFrame(hoja_clientes.get_all_records())
    st.dataframe(df, use_container_width=True)
    
    st.subheader("Agregar Nuevo Cliente")
    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input("Nombre del Cliente")
        contacto = st.text_input("Nombre del Contacto")
        email = st.text_input("Email del Contacto")
    with col2:
        industria = st.text_input("Industria")
        productos = st.text_area("Productos / Servicios principales")
    
    publico = st.text_area("Público Objetivo")
    objetivos = st.text_area("Objetivos principales de la marca")
    contexto = st.text_area("Contexto adicional / Historia / Notas importantes")
    
    if st.button("Guardar Cliente"):
        nueva_fila = [nombre, contacto, email, industria, productos, publico, objetivos, contexto, ""]
        hoja_clientes.append_row(nueva_fila)
        st.success(f"Cliente {nombre} guardado correctamente")

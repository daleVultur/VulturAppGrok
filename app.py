import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

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

try:
    client = get_google_client()
    spread = client.open("Vultur Informes")
    hoja_clientes = spread.worksheet("Clientes")
    hoja_historico = spread.worksheet("Historico")
    st.success("✅ Conectado correctamente a Google Sheets")
except Exception as e:
    st.error(f"Error de conexión: {str(e)}")
    st.info("Verifica que el nombre de la hoja sea exactamente 'Vultur Informes' y que el Secret esté correcto.")
    st.stop()

# Sidebar
opcion = st.sidebar.selectbox("Seleccionar opción", 
    ["Generar Nuevo Informe", "Gestionar Clientes", "Ver Histórico"])

# ===================== GESTIÓN DE CLIENTES =====================
if opcion == "Gestionar Clientes":
    st.header("Gestión de Clientes")
    df_clientes = pd.DataFrame(hoja_clientes.get_all_records())
    if not df_clientes.empty:
        st.dataframe(df_clientes, use_container_width=True)
    else:
        st.info("Aún no hay clientes registrados.")
    
    st.subheader("Agregar Nuevo Cliente")
    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input("Nombre del Cliente *")
        contacto = st.text_input("Nombre del Contacto")
        email = st.text_input("Email del Contacto")
    with col2:
        industria = st.text_input("Industria")
        productos = st.text_area("Productos / Servicios principales")
    
    publico = st.text_area("Público Objetivo")
    objetivos = st.text_area("Objetivos principales de la marca")
    contexto = st.text_area("Contexto adicional, antecedentes, mercado, etc. (esto lo usará la IA)")
    
    if st.button("💾 Guardar Cliente"):
        if nombre.strip():
            nueva_fila = [nombre, contacto, email, industria, productos, publico, objetivos, contexto, ""]
            hoja_clientes.append_row(nueva_fila)
            st.success(f"✅ Cliente '{nombre}' guardado correctamente")
            st.rerun()
        else:
            st.error("El nombre del cliente es obligatorio")

# ===================== GENERAR INFORME =====================
elif opcion == "Generar Nuevo Informe":
    st.header("🚀 Generar Nuevo Informe Mensual")
    
    clientes_data = hoja_clientes.get_all_records()
    clientes = [row.get('Cliente', '') for row in clientes_data if row.get('Cliente')]
    
    if not clientes:
        st.warning("Primero agrega al menos un cliente en 'Gestionar Clientes'")
    else:
        cliente_seleccionado = st.selectbox("Seleccionar Cliente", options=clientes)
        periodo = st.text_input("Periodo del informe", value=datetime.now().strftime("%B %Y").capitalize())
        
        st.subheader("📊 Subir archivos exportados de Meta")
        col1, col2, col3 = st.columns(3)
        with col1:
            csv_fb = st.file_uploader("CSV Consolidado Facebook", type=["csv"])
        with col2:
            csv_ig_posts = st.file_uploader("CSV Posts Instagram", type=["csv"])
        with col3:
            csv_ig_stories = st.file_uploader("CSV Historias Instagram", type=["csv"])
        
        notas_manuales = st.text_area("Notas manuales o contexto extra del mes", height=100)
        
        if st.button("🔥 Generar Informe Completo con IA", type="primary", use_container_width=True):
            st.info("🚧 Esta funcionalidad se activará en el siguiente paso (procesamiento de CSVs + IA + PDF).")
            st.success("¡Arquitectura lista! Ahora vamos a añadir la parte inteligente.")

st.sidebar.info(f"🌐 App en desarrollo - {datetime.now().strftime('%d/%m/%Y')}")

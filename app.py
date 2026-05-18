import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from fpdf import FPDF
from groq import Groq
import io

st.set_page_config(page_title="Vultur 360 Informes", layout="wide")
st.title("🦅 Vultur 360 - Generador Automático de Informes Mensuales")

# ==================== CONEXIONES ====================
@st.cache_resource
def get_google_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"])
    return gspread.authorize(creds)

@st.cache_resource
def get_groq_client():
    return Groq(api_key=st.secrets["groq_api_key"]["key"])

client = get_google_client()
spread = client.open("Vultur Informes")
hoja_clientes = spread.worksheet("Clientes")
hoja_historico = spread.worksheet("Historico")

st.success("✅ Conectado a Google Sheets y listo para IA")

# Sidebar
st.sidebar.header("Menú")
opcion = st.sidebar.selectbox("Ir a", ["Generar Informe", "Gestionar Clientes"])

# ===================== GENERAR INFORME =====================
if opcion == "Generar Informe":
    st.header("🚀 Generar Nuevo Informe")

    clientes = [row['Cliente'] for row in hoja_clientes.get_all_records() if row.get('Cliente')]
    cliente_seleccionado = st.selectbox("Cliente", options=clientes)
    periodo = st.text_input("Periodo", value=datetime.now().strftime("%B %Y").capitalize())

    st.subheader("Archivos Meta")
    col1, col2, col3 = st.columns(3)
    with col1:
        fb_file = st.file_uploader("CSV Facebook", type="csv")
    with col2:
        ig_posts = st.file_uploader("CSV Posts IG", type="csv")
    with col3:
        ig_stories = st.file_uploader("CSV Stories IG", type="csv")

    notas = st.text_area("Notas manuales / contexto extra", height=100)

    if st.button("🔥 Generar Informe con IA", type="primary"):
        with st.spinner("Procesando CSVs + Generando informe..."):
            # Leer CSVs (básico por ahora)
            df_fb = pd.read_csv(fb_file) if fb_file else pd.DataFrame()
            df_igp = pd.read_csv(ig_posts) if ig_posts else pd.DataFrame()

            # Buscar contexto del cliente
            contexto_row = next((row for row in hoja_clientes.get_all_records() if row.get('Cliente') == cliente_seleccionado), {})
            contexto = contexto_row.get('ContextoAdicional', 'Sin contexto previo.')

            # Prompt poderoso
            prompt = f"""Eres un consultor senior de Vultur 360. 
Genera un informe mensual **exactamente** en el estilo, tono y estructura del ejemplo que te doy a continuación.
Mantén el mismo nivel de profesionalismo, concisión y siempre resalta positivamente el valor del trabajo de la agencia.

**EJEMPLO DE INFORME (usa esta estructura y tono):**
[Copia aquí todo el texto del informe de IOGO que me enviaste antes]

Cliente actual: {cliente_seleccionado}
Periodo: {periodo}
Contexto de la marca: {contexto}
Notas del mes: {notas}

Datos disponibles:
Facebook: {len(df_fb)} filas
Instagram Posts: {len(df_igp)} filas

Genera el informe completo listo para enviar al cliente.
"""

            groq = get_groq_client()
            response = groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=4000
            )

            informe_texto = response.choices[0].message.content

            st.subheader("📄 Vista Previa del Informe")
            st.text_area("Informe generado", informe_texto, height=500)

            # Generar PDF básico
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, informe_texto)

            pdf_bytes = pdf.output(dest="S").encode("latin1")

            st.download_button(
                label="⬇️ Descargar PDF",
                data=pdf_bytes,
                file_name=f"Informe_{cliente_seleccionado}_{periodo}.pdf",
                mime="application/pdf"
            )

            st.success("¡Informe generado correctamente!")

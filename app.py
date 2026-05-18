import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
from groq import Groq
from fpdf import FPDF

st.set_page_config(page_title="Vultur 360 Informes", layout="wide")
st.title("🦅 Vultur 360 - Generador Automático de Informes Mensuales")

# ==================== CONEXIONES ====================
@st.cache_resource
def get_google_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds)

@st.cache_resource
def get_groq_client():
    return Groq(api_key=st.secrets["groq_api_key"]["key"])

client = get_google_client()
spread = client.open("Vultur Informes")
hoja_clientes = spread.worksheet("Clientes")
hoja_historico = spread.worksheet("Historico")

st.success("✅ Sistema conectado")

st.sidebar.header("Menú")
opcion = st.sidebar.selectbox("Seleccionar sección", ["Generar Informe", "Gestionar Clientes"])

# ===================== GENERAR INFORME =====================
if opcion == "Generar Informe":
    st.header("🚀 Generar o Ver Informe Mensual")

    clientes = [r.get('Cliente', '') for r in hoja_clientes.get_all_records() if r.get('Cliente')]
    cliente_seleccionado = st.selectbox("Cliente", clientes)

    # Dropdown de periodos
    hoy = datetime.now()
    meses = [(hoy - timedelta(days=30*i)).strftime("%B %Y").capitalize() for i in range(6)]
    historico = hoja_historico.get_all_records()
    periodos_guardados = [row.get('Periodo') for row in historico if row.get('Cliente') == cliente_seleccionado]
    periodo = st.selectbox("Periodo", sorted(list(set(meses + periodos_guardados)), reverse=True))

    st.subheader("Archivos de Meta (obligatorio solo la primera vez)")
    c1, c2, c3 = st.columns(3)
    with c1: fb = st.file_uploader("CSV Facebook", type="csv")
    with c2: igp = st.file_uploader("CSV Posts Instagram", type="csv")
    with c3: igs = st.file_uploader("CSV Historias Instagram", type="csv")

    notas = st.text_area("Notas adicionales", height=80)

    if st.button("🔥 Generar Informe con IA", type="primary"):
        with st.spinner("Leyendo CSVs y analizando con IA..."):
            
            # Leer y resumir datos
            datos_fb = "No cargado"
            datos_ig = "No cargado"
            
            if fb is not None:
                df_fb = pd.read_csv(fb)
                datos_fb = f"Alcance aproximado: {df_fb.get('reach', df_fb.get('impressions', pd.Series([0]))).sum():,}"
            
            if igp is not None:
                df_ig = pd.read_csv(igp)
                datos_ig = f"Posts analizados: {len(df_ig)}"

            contexto_row = next((r for r in hoja_clientes.get_all_records() if r.get('Cliente') == cliente_seleccionado), {})
            contexto_cliente = contexto_row.get('ContextoAdicional', '')

            # Prompt mejorado con datos reales
            prompt = f"""Eres redactor senior de Vultur 360. Genera un informe mensual **exactamente** en el estilo profesional, conciso y positivo del ejemplo que conoces.

Cliente: {cliente_seleccionado}
Periodo: {periodo}
Contexto de marca: {contexto_cliente}
Notas manuales: {notas}

Datos extraídos de Meta:
- Facebook: {datos_fb}
- Instagram Posts: {datos_ig}

Analiza los números, compara con meses anteriores si es posible, destaca lo positivo y genera el informe completo."""

            groq = get_groq_client()
            respuesta = groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=4500
            )

            texto_informe = respuesta.choices[0].message.content

            st.subheader("📝 Vista Previa del Informe")
            st.text_area("Informe generado", texto_informe, height=600)

            # === PDF MEJORADO (evita el error de espacio) ===
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=10)   # Fuente más pequeña
            
            # Dividir el texto de forma segura
            lines = texto_informe.split('\n')
            for line in lines:
                pdf.multi_cell(0, 6, line.encode('latin-1', 'replace').decode('latin-1'))
                pdf.ln(1)

            pdf_bytes = pdf.output(dest='S').encode('latin-1', 'replace')

            st.download_button(
                label="⬇️ Descargar PDF",
                data=pdf_bytes,
                file_name=f"Informe_{cliente_seleccionado}_{periodo}.pdf",
                mime="application/pdf"
            )

            st.success("¡Informe generado!")

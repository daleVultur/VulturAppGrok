import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
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

    # Periodos
    hoy = datetime.now()
    meses = [(hoy - timedelta(days=30*i)).strftime("%B %Y").capitalize() for i in range(6)]
    historico = hoja_historico.get_all_records()
    periodos_guardados = [row.get('Periodo') for row in historico if row.get('Cliente') == cliente_seleccionado]
    periodo = st.selectbox("Periodo", sorted(list(set(meses + periodos_guardados)), reverse=True))

    st.subheader("📁 Archivos de Meta")
    c1, c2, c3 = st.columns(3)
    with c1: fb = st.file_uploader("CSV Facebook", type="csv")
    with c2: igp = st.file_uploader("CSV Posts Instagram", type="csv")
    with c3: igs = st.file_uploader("CSV Historias Instagram", type="csv")

    notas = st.text_area("Notas adicionales del mes", height=100)

    if st.button("🔥 Generar Informe con IA", type="primary"):
        with st.spinner("Leyendo archivos Meta + Generando informe..."):
            
            # === PROCESAR ARCHIVOS (mejorado) ===
            resumen_datos = "No se cargaron archivos."
            if fb is not None:
                try:
                    df_fb = pd.read_csv(fb)
                    resumen_datos = f"Facebook: {len(df_fb)} filas cargadas. "
                    if 'reach' in df_fb.columns:
                        resumen_datos += f"Alcance total aprox: {df_fb['reach'].sum():,}"
                except:
                    resumen_datos = "Error al leer CSV Facebook"

            if igp is not None:
                try:
                    df_ig = pd.read_csv(igp)
                    resumen_datos += f" | Instagram Posts: {len(df_ig)} filas"
                except:
                    pass

            contexto_row = next((r for r in hoja_clientes.get_all_records() if r.get('Cliente') == cliente_seleccionado), {})
            contexto_cliente = contexto_row.get('ContextoAdicional', '')

            # Prompt mejorado
            prompt = f"""Eres redactor senior de Vultur 360. 
Genera un informe mensual **exactamente** con el estilo profesional y estructura del ejemplo que te mostré anteriormente.

**Datos del cliente:**
- Cliente: {cliente_seleccionado}
- Periodo: {periodo}
- Contexto de la marca: {contexto_cliente}
- Notas manuales: {notas}

**Datos extraídos de Meta:**
{resumen_datos}

Analiza los números, destaca logros, compara si es posible y genera el informe completo en español."""

            groq = get_groq_client()
            respuesta = groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.65,
                max_tokens=4500
            )

            texto_informe = respuesta.choices[0].message.content

            st.subheader("📝 Vista Previa")
            st.text_area("Informe generado", texto_informe, height=600)

            # === PDF ROBUSTO ===
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=11)
            
            # Método más seguro
            safe_text = texto_informe.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 8, safe_text)

            # Guardar en BytesIO
            byte_buffer = io.BytesIO()
            pdf.output(byte_buffer)
            pdf_bytes = byte_buffer.getvalue()

            st.download_button(
                label="⬇️ Descargar PDF",
                data=pdf_bytes,
                file_name=f"Informe_{cliente_seleccionado}_{periodo}.pdf",
                mime="application/pdf"
            )

            st.success("¡Informe generado correctamente!")

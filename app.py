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

# ===================== GESTIONAR CLIENTES =====================
if opcion == "Gestionar Clientes":
    st.header("👥 Gestión de Clientes")
    df = pd.DataFrame(hoja_clientes.get_all_records())
    st.dataframe(df, use_container_width=True)

    st.subheader("Agregar Nuevo Cliente")
    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input("Nombre del Cliente *")
        contacto = st.text_input("Nombre del Contacto")
        email = st.text_input("Email")
    with col2:
        industria = st.text_input("Industria")
        productos = st.text_area("Productos principales")
    
    publico = st.text_area("Público Objetivo")
    objetivos = st.text_area("Objetivos de la marca")
    contexto = st.text_area("Contexto completo para la IA")
    
    if st.button("Guardar Cliente"):
        if nombre:
            hoja_clientes.append_row([nombre, contacto, email, industria, productos, publico, objetivos, contexto, ""])
            st.success("Cliente guardado")
            st.rerun()

# ===================== GENERAR INFORME =====================
elif opcion == "Generar Informe":
    st.header("🚀 Generar Informe Mensual")

    clientes = [r.get('Cliente', '') for r in hoja_clientes.get_all_records() if r.get('Cliente')]
    cliente_seleccionado = st.selectbox("Cliente", clientes)

    # Periodos
    hoy = datetime.now()
    meses = [(hoy - timedelta(days=30*i)).strftime("%B %Y").capitalize() for i in range(6)]
    historico_list = hoja_historico.get_all_records()
    periodos_guardados = [row.get('Periodo') for row in historico_list if row.get('Cliente') == cliente_seleccionado]
    periodo = st.selectbox("Periodo", sorted(list(set(meses + periodos_guardados)), reverse=True))

    st.subheader("📁 Subir archivos de Meta")
    col1, col2, col3 = st.columns(3)
    with col1: fb_file = st.file_uploader("CSV Facebook", type="csv", key=f"fb_{cliente_seleccionado}")
    with col2: igp_file = st.file_uploader("CSV Posts Instagram", type="csv", key=f"igp_{cliente_seleccionado}")
    with col3: igs_file = st.file_uploader("CSV Historias Instagram", type="csv", key=f"igs_{cliente_seleccionado}")

    notas = st.text_area("Notas adicionales del mes", height=100)

    if st.button("🔥 Generar Informe con IA", type="primary"):
        with st.spinner("Leyendo CSVs y analizando..."):
            
            resumen_datos = "No se subieron archivos.\n"

            if fb_file is not None:
                df_fb = pd.read_csv(fb_file)
                resumen_datos += f"\n--- FACEBOOK ---\nFilas: {len(df_fb)}\n"
                resumen_datos += df_fb.describe(include='all').to_string()[:1500]  # Resumen estadístico

            if igp_file is not None:
                df_ig = pd.read_csv(igp_file)
                resumen_datos += f"\n\n--- INSTAGRAM POSTS ---\nFilas: {len(df_ig)}\n"
                resumen_datos += df_ig.describe(include='all').to_string()[:1500]

            contexto_row = next((r for r in hoja_clientes.get_all_records() if r.get('Cliente') == cliente_seleccionado), {})
            contexto_cliente = contexto_row.get('ContextoAdicional', '')

            st.subheader("📊 Datos enviados a la IA (debug)")
            st.text_area("Resumen de datos", resumen_datos, height=200)

            prompt = f"""Eres redactor senior de Vultur 360. Usa **todos** los datos numéricos proporcionados para generar un informe realista y profesional.

Cliente: {cliente_seleccionado}
Periodo: {periodo}
Contexto marca: {contexto_cliente}
Notas manuales: {notas}

DATOS REALES DE META:
{resumen_datos}

Genera el informe completo siguiendo la estructura y tono del ejemplo que te mostré anteriormente."""

            groq = get_groq_client()
            respuesta = groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.65,
                max_tokens=4500
            )

            texto_informe = respuesta.choices[0].message.content

            st.subheader("📝 Vista Previa")
            st.text_area("Informe generado", texto_informe, height=500)

            # PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=11)
            safe_text = texto_informe.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 8, safe_text)

            byte_buffer = io.BytesIO()
            pdf.output(byte_buffer)
            pdf_bytes = byte_buffer.getvalue()

            st.download_button("⬇️ Descargar PDF", pdf_bytes, f"Informe_{cliente_seleccionado}_{periodo}.pdf", "application/pdf")

            # === GUARDAR EN HISTÓRICO ===
            if st.button("💾 Guardar este informe en Histórico"):
                hoja_historico.append_row([cliente_seleccionado, periodo, "", "", "", "", "", "", "", notas, texto_informe[:1000]])
                st.success("Guardado en Histórico correctamente")

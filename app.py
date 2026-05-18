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

st.success("✅ Sistema conectado y listo para procesar CSVs")

st.sidebar.header("Menú")
opcion = st.sidebar.selectbox("Seleccionar sección", ["Generar Informe", "Gestionar Clientes"])

# ===================== GENERAR INFORME =====================
if opcion == "Generar Informe":
    st.header("🚀 Generar Informe Mensual")

    clientes = [r.get('Cliente', '') for r in hoja_clientes.get_all_records() if r.get('Cliente')]
    cliente_seleccionado = st.selectbox("Cliente", clientes)

    # Periodos
    hoy = datetime.now()
    meses = [(hoy - timedelta(days=30*i)).strftime("%B %Y").capitalize() for i in range(6)]
    historico = hoja_historico.get_all_records()
    periodos_guardados = [row.get('Periodo') for row in historico if row.get('Cliente') == cliente_seleccionado]
    periodo = st.selectbox("Periodo", sorted(list(set(meses + periodos_guardados)), reverse=True))

    st.subheader("📁 Subir los 3 archivos de Meta")
    col1, col2, col3 = st.columns(3)
    with col1: fb_file = st.file_uploader("CSV Facebook", type="csv")
    with col2: ig_posts_file = st.file_uploader("CSV Posts Instagram", type="csv")
    with col3: ig_stories_file = st.file_uploader("CSV Historias Instagram", type="csv")

    notas = st.text_area("Notas adicionales / contexto del mes", height=100)

    if st.button("🔥 Generar Informe con IA", type="primary"):
        with st.spinner("Procesando archivos y generando informe..."):
            
            resumen_datos = f"Cliente: {cliente_seleccionado}\nPeriodo: {periodo}\n\n"

            # === PROCESAMIENTO AVANZADO DE CSVs ===
            if fb_file:
                df_fb = pd.read_csv(fb_file)
                resumen_datos += f"**FACEBOOK**\n"
                resumen_datos += f"Total publicaciones: {len(df_fb)}\n"
                if 'Reach' in df_fb.columns:
                    resumen_datos += f"Alcance total: {df_fb['Reach'].sum():,}\n"
                if 'Views' in df_fb.columns:
                    resumen_datos += f"Vistas totales: {df_fb['Views'].sum():,}\n"
                if 'Reactions' in df_fb.columns:
                    resumen_datos += f"Reacciones totales: {df_fb['Reactions'].sum():,}\n"

            if ig_posts_file:
                df_ig = pd.read_csv(ig_posts_file)
                resumen_datos += f"\n**INSTAGRAM POSTS**\n"
                resumen_datos += f"Total publicaciones: {len(df_ig)}\n"
                if 'Reach' in df_ig.columns:
                    resumen_datos += f"Alcance total: {df_ig['Reach'].sum():,}\n"
                if 'Views' in df_ig.columns:
                    resumen_datos += f"Vistas totales: {df_ig['Views'].sum():,}\n"
                if 'Likes' in df_ig.columns:
                    resumen_datos += f"Likes totales: {df_ig['Likes'].sum():,}\n"
                if 'Comments' in df_ig.columns:
                    resumen_datos += f"Comentarios: {df_ig['Comments'].sum():,}\n"

            if ig_stories_file:
                df_stories = pd.read_csv(ig_stories_file)
                resumen_datos += f"\n**INSTAGRAM STORIES**\n"
                resumen_datos += f"Total stories: {len(df_stories)}\n"
                if 'Reach' in df_stories.columns:
                    resumen_datos += f"Alcance stories: {df_stories['Reach'].sum():,}\n"
                if 'Views' in df_stories.columns:
                    resumen_datos += f"Vistas stories: {df_stories['Views'].sum():,}\n"

            st.subheader("📊 Datos enviados a la IA")
            st.text_area("Resumen extraído", resumen_datos, height=300)

            # Prompt final
            prompt = f"""Eres redactor senior de Vultur 360. Genera un informe mensual profesional, conciso y positivo usando **exactamente** los datos que te proporciono.

{resumen_datos}

Notas adicionales: {notas}

Genera el informe completo siguiendo la estructura:
- Saludo y fecha
- Resumen General
- Resultados Generales (por red)
- Lectura del periodo
- Contenido publicado
- Publicaciones destacadas (si es posible)
- Principales aprendizajes
- Conclusión
- Próximos pasos"""

            groq = get_groq_client()
            respuesta = groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.65,
                max_tokens=4500
            )

            texto_informe = respuesta.choices[0].message.content

            st.subheader("📝 Vista Previa del Informe")
            st.text_area("Informe generado", texto_informe, height=600)

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

            # Guardar histórico
            if st.button("💾 Guardar en Histórico"):
                hoja_historico.append_row([cliente_seleccionado, periodo, "", "", "", "", "", "", "", notas, texto_informe[:800]])
                st.success("Guardado en Histórico")

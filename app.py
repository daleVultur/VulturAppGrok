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

# ===================== GESTIONAR CLIENTES (CORREGIDO) =====================
if opcion == "Gestionar Clientes":
    st.header("👥 Gestión de Clientes")
    df = pd.DataFrame(hoja_clientes.get_all_records())
    st.dataframe(df, use_container_width=True)

    st.subheader("➕ Agregar Nuevo Cliente")
    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input("Nombre del Cliente *")
        contacto = st.text_input("Nombre del Contacto")
        email = st.text_input("Email")
    with col2:
        industria = st.text_input("Industria")
        productos = st.text_area("Productos principales")
    
    publico = st.text_area("Público Objetivo")
    objetivos = st.text_area("Objetivos principales de la marca")
    contexto = st.text_area("Contexto adicional (importante para IA)")
    
    if st.button("💾 Guardar Cliente"):
        if nombre.strip():
            hoja_clientes.append_row([nombre, contacto, email, industria, productos, publico, objetivos, contexto, ""])
            st.success(f"Cliente '{nombre}' guardado")
            st.rerun()

# ===================== GENERAR INFORME =====================
elif opcion == "Generar Informe":
    st.header("🚀 Generar Informe Mensual")

    clientes = [r.get('Cliente', '') for r in hoja_clientes.get_all_records() if r.get('Cliente')]
    cliente_seleccionado = st.selectbox("Cliente", clientes)

    hoy = datetime.now()
    meses = [(hoy - timedelta(days=30*i)).strftime("%B %Y").capitalize() for i in range(6)]
    historico = hoja_historico.get_all_records()
    periodos_guardados = [row.get('Periodo') for row in historico if row.get('Cliente') == cliente_seleccionado]
    periodo = st.selectbox("Periodo", sorted(list(set(meses + periodos_guardados)), reverse=True))

    st.subheader("📁 Subir archivos de Meta")
    col1, col2, col3 = st.columns(3)
    with col1: fb_file = st.file_uploader("CSV Facebook", type="csv")
    with col2: ig_posts_file = st.file_uploader("CSV Posts Instagram", type="csv")
    with col3: ig_stories_file = st.file_uploader("CSV Historias Instagram", type="csv")

    notas = st.text_area("Notas adicionales del mes", height=100)

    if st.button("🔥 Generar Informe con IA", type="primary"):
        with st.spinner("Procesando CSVs y analizando contenido..."):
            
            resumen_datos = f"Cliente: {cliente_seleccionado}\nPeriodo: {periodo}\n\n"

            # Facebook
            if fb_file:
                df_fb = pd.read_csv(fb_file)
                resumen_datos += f"**FACEBOOK** ({len(df_fb)} publicaciones)\n"
                if 'Reach' in df_fb.columns:
                    resumen_datos += f"Alcance total: {df_fb['Reach'].sum():,}\n"
                if 'Views' in df_fb.columns:
                    resumen_datos += f"Vistas totales: {df_fb['Views'].sum():,}\n"
                # Top publicaciones
                if 'Description' in df_fb.columns and 'Reach' in df_fb.columns:
                    top_fb = df_fb.nlargest(3, 'Reach')[['Description', 'Reach']]
                    resumen_datos += "\nTop publicaciones Facebook:\n"
                    for _, row in top_fb.iterrows():
                        resumen_datos += f"- Alcance {row['Reach']:,}: {row['Description'][:150]}...\n"

            # Instagram Posts
            if ig_posts_file:
                df_ig = pd.read_csv(ig_posts_file)
                resumen_datos += f"\n**INSTAGRAM POSTS** ({len(df_ig)} publicaciones)\n"
                if 'Reach' in df_ig.columns:
                    resumen_datos += f"Alcance total: {df_ig['Reach'].sum():,}\n"
                if 'Views' in df_ig.columns:
                    resumen_datos += f"Vistas totales: {df_ig['Views'].sum():,}\n"
                if 'Description' in df_ig.columns and 'Reach' in df_ig.columns:
                    top_ig = df_ig.nlargest(3, 'Reach')[['Description', 'Reach']]
                    resumen_datos += "\nTop publicaciones Instagram:\n"
                    for _, row in top_ig.iterrows():
                        resumen_datos += f"- Alcance {row['Reach']:,}: {row['Description'][:150]}...\n"

            st.subheader("📊 Datos completos enviados a la IA")
            st.text_area("Debug - Datos", resumen_datos, height=400)

            prompt = f"""Eres un analista senior y redactor profesional de Vultur 360.
Analiza **todos** los datos y contenidos proporcionados y genera un informe mensual de alta calidad.

{resumen_datos}

Notas manuales: {notas}

Genera el informe completo con la estructura y tono profesional que usamos (Resumen General, Resultados por red, Lectura del periodo, Contenido publicado, Publicaciones destacadas con análisis de por qué funcionaron, Aprendizajes, Conclusión y Próximos pasos). 
Sé inteligente y extrae insights del tipo de contenido que mejor funcionó."""

            groq = get_groq_client()
            respuesta = groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=5000
            )

            texto_informe = respuesta.choices[0].message.content

            st.subheader("📝 Vista Previa")
            st.text_area("Informe generado", texto_informe, height=700)

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

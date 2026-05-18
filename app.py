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

st.success("✅ Sistema conectado correctamente")

st.sidebar.header("Menú")
opcion = st.sidebar.selectbox("Seleccionar sección", ["Generar Informe", "Gestionar Clientes"])

# ===================== GESTIONAR CLIENTES =====================
if opcion == "Gestionar Clientes":
    st.header("👥 Gestión de Clientes")
    
    df_clientes = pd.DataFrame(hoja_clientes.get_all_records())
    if not df_clientes.empty:
        st.dataframe(df_clientes, use_container_width=True)
    else:
        st.info("Aún no hay clientes registrados.")

    st.subheader("➕ Agregar Nuevo Cliente")
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
    contexto = st.text_area("Contexto adicional (muy importante para la IA)")
    
    if st.button("💾 Guardar Cliente"):
        if nombre.strip():
            hoja_clientes.append_row([nombre, contacto, email, industria, productos, publico, objetivos, contexto, ""])
            st.success(f"✅ Cliente '{nombre}' guardado")
            st.rerun()
        else:
            st.error("El nombre del cliente es obligatorio")

# ===================== GENERAR INFORME =====================
elif opcion == "Generar Informe":
    st.header("🚀 Generar o Ver Informe Mensual")

    clientes = [r.get('Cliente', '') for r in hoja_clientes.get_all_records() if r.get('Cliente')]
    if not clientes:
        st.warning("Primero agrega clientes en 'Gestionar Clientes'")
    else:
        cliente_seleccionado = st.selectbox("Seleccionar Cliente", clientes)

        # Periodos inteligentes
        hoy = datetime.now()
        meses = [(hoy - timedelta(days=30*i)).strftime("%B %Y").capitalize() for i in range(6)]
        historico = hoja_historico.get_all_records()
        periodos_guardados = [row.get('Periodo') for row in historico if row.get('Cliente') == cliente_seleccionado]
        periodo = st.selectbox("Periodo", sorted(list(set(meses + periodos_guardados)), reverse=True))

        st.subheader("📁 Subir archivos de Meta")
        col1, col2, col3 = st.columns(3)
        with col1:
            fb_file = st.file_uploader("CSV Facebook", type="csv")
        with col2:
            ig_posts_file = st.file_uploader("CSV Posts Instagram", type="csv")
        with col3:
            ig_stories_file = st.file_uploader("CSV Historias Instagram", type="csv")

        notas = st.text_area("Notas adicionales del mes", height=100)

        if st.button("🔥 Generar Informe con IA", type="primary"):
            with st.spinner("Leyendo CSVs y generando análisis con IA..."):
                
                # === PROCESAMIENTO REAL DE ARCHIVOS ===
                resumen_datos = ""
                
                if fb_file is not None:
                    df_fb = pd.read_csv(fb_file)
                    resumen_datos += f"Facebook - Filas: {len(df_fb)}\n"
                    for col in ['reach', 'impressions', 'engagements', 'interactions']:
                        if col in df_fb.columns:
                            total = df_fb[col].sum()
                            resumen_datos += f"   • {col.capitalize()}: {total:,}\n"
                
                if ig_posts_file is not None:
                    df_ig = pd.read_csv(ig_posts_file)
                    resumen_datos += f"\nInstagram Posts - Filas: {len(df_ig)}\n"
                    for col in ['reach', 'impressions', 'likes', 'comments', 'saves']:
                        if col in df_ig.columns:
                            total = df_ig[col].sum()
                            resumen_datos += f"   • {col.capitalize()}: {total:,}\n"

                contexto_row = next((r for r in hoja_clientes.get_all_records() if r.get('Cliente') == cliente_seleccionado), {})
                contexto_cliente = contexto_row.get('ContextoAdicional', '')

                prompt = f"""Eres redactor senior de Vultur 360. Genera el informe **exactamente** en el estilo del ejemplo que te mostré.

Cliente: {cliente_seleccionado}
Periodo: {periodo}
Contexto de la marca: {contexto_cliente}
Notas manuales: {notas}

DATOS REALES DE META:
{resumen_datos if resumen_datos else "No se cargaron archivos esta vez."}

Analiza los números, destaca lo positivo, sugiere insights y genera el informe completo."""

                groq = get_groq_client()
                respuesta = groq.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.65,
                    max_tokens=4500
                )

                texto_informe = respuesta.choices[0].message.content

                st.subheader("📝 Vista Previa del Informe")
                st.text_area("Informe", texto_informe, height=600)

                # PDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=11)
                safe_text = texto_informe.encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(0, 8, safe_text)

                byte_buffer = io.BytesIO()
                pdf.output(byte_buffer)
                pdf_bytes = byte_buffer.getvalue()

                st.download_button(
                    label="⬇️ Descargar PDF",
                    data=pdf_bytes,
                    file_name=f"Informe_{cliente_seleccionado}_{periodo}.pdf",
                    mime="application/pdf"
                )

                st.success("¡Informe generado!")

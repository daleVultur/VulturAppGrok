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

st.success("✅ Sistema conectado y listo")

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
    contexto = st.text_area("Contexto completo (antecedentes, mercado, tono, etc.)")
    
    if st.button("Guardar Cliente"):
        if nombre:
            hoja_clientes.append_row([nombre, contacto, email, industria, productos, publico, objetivos, contexto, ""])
            st.success("Cliente guardado")
            st.rerun()

# ===================== GENERAR INFORME =====================
elif opcion == "Generar Informe":
    st.header("🚀 Generar Informe Mensual")

    clientes = [r['Cliente'] for r in hoja_clientes.get_all_records() if r.get('Cliente')]
    cliente_seleccionado = st.selectbox("Cliente", clientes)
    periodo = st.text_input("Periodo", datetime.now().strftime("%B %Y").capitalize())

    st.subheader("Archivos de Meta")
    c1, c2, c3 = st.columns(3)
    with c1: fb = st.file_uploader("CSV Facebook", type="csv")
    with c2: igp = st.file_uploader("CSV Posts Instagram", type="csv")
    with c3: igs = st.file_uploader("CSV Historias Instagram", type="csv")

    notas = st.text_area("Notas adicionales del mes", height=80)

    if st.button("🔥 Generar Informe Completo con IA", type="primary"):
        with st.spinner("Analizando archivos y generando informe..."):
            # Leer CSVs
            df_fb = pd.read_csv(fb) if fb is not None else pd.DataFrame()
            df_ig_posts = pd.read_csv(igp) if igp is not None else pd.DataFrame()

            # Contexto del cliente
            contexto_row = next((r for r in hoja_clientes.get_all_records() if r.get('Cliente') == cliente_seleccionado), {})
            contexto_cliente = contexto_row.get('ContextoAdicional', 'Sin contexto adicional.')

            # Prompt maestro (con tu estilo)
            prompt = f"""Eres el redactor senior de informes de Vultur 360.
Genera un informe **exactamente** en el mismo tono, estructura y estilo profesional del siguiente ejemplo:

**EJEMPLO REAL:**
Cochabamba, 07 de mayo de 2026
Sr. Christian Vrsalovic IOGO Presente.-

Ref.: Informe mensual de trabajo

Estimado Christian:

Hacemos llegar el informe correspondiente al periodo abril del año 2026...

(usa toda la estructura: Resumen General, Resultados Generales por red, Crecimiento vs periodo anterior, Lectura del periodo, Contenido publicado, Publicaciones destacadas, Principales aprendizajes, Conclusión, Próximos pasos)

Cliente actual: {cliente_seleccionado}
Periodo: {periodo}
Contexto de la marca: {contexto_cliente}
Notas del mes: {notas}

Datos crudos:
- Facebook: {len(df_fb)} registros
- Instagram Posts: {len(df_ig_posts)} registros

Genera un informe conciso, profesional y que resalte positivamente el trabajo de Vultur 360."""

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

            # PDF simple
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=11)
            pdf.multi_cell(0, 8, texto_informe)
            
            pdf_output = pdf.output(dest="S").encode("latin1")

            st.download_button(
                "⬇️ Descargar PDF",
                data=pdf_output,
                file_name=f"Informe_{cliente_seleccionado}_{periodo}.pdf",
                mime="application/pdf"
            )

            st.success("¡Informe generado correctamente!")

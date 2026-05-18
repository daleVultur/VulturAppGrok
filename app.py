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

st.success("✅ Sistema conectado y listo")

st.sidebar.header("Menú")
opcion = st.sidebar.selectbox("Seleccionar sección", ["Generar Informe", "Gestionar Clientes", "Ver Histórico"])

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
    contexto = st.text_area("Contexto completo (antecedentes, mercado, etc.)")
    
    if st.button("Guardar Cliente"):
        if nombre:
            hoja_clientes.append_row([nombre, contacto, email, industria, productos, publico, objetivos, contexto, ""])
            st.success("Cliente guardado")
            st.rerun()

# ===================== GENERAR / VER INFORME =====================
elif opcion == "Generar Informe":
    st.header("🚀 Generar o Ver Informe Mensual")

    clientes = [r.get('Cliente', '') for r in hoja_clientes.get_all_records() if r.get('Cliente')]
    cliente_seleccionado = st.selectbox("Cliente", clientes)

    # === Dropdown inteligente de Periodos ===
    hoy = datetime.now()
    meses = []
    for i in range(4):  # Mes actual + 3 anteriores
        fecha = hoy - timedelta(days=30*i)
        meses.append(fecha.strftime("%B %Y").capitalize())

    # Obtener periodos ya guardados en histórico
    historico_existente = hoja_historico.get_all_records()
    periodos_guardados = [row.get('Periodo') for row in historico_existente if row.get('Cliente') == cliente_seleccionado]
    periodos_guardados = list(dict.fromkeys(periodos_guardados))  # eliminar duplicados

    todos_los_periodos = sorted(list(set(meses + periodos_guardados)), reverse=True)
    periodo = st.selectbox("Periodo", options=todos_los_periodos)

    # Ver si ya existe histórico para este periodo
    datos_historico = [row for row in historico_existente if row.get('Cliente') == cliente_seleccionado and row.get('Periodo') == periodo]

    st.subheader("Archivos de Meta (solo si es nuevo)")
    c1, c2, c3 = st.columns(3)
    with c1: fb = st.file_uploader("CSV Facebook", type="csv", key="fb")
    with c2: igp = st.file_uploader("CSV Posts Instagram", type="csv", key="igp")
    with c3: igs = st.file_uploader("CSV Historias Instagram", type="csv", key="igs")

    notas = st.text_area("Notas adicionales del mes", height=80, value=datos_historico[0].get('NotasManuales', '') if datos_historico else "")

    if st.button("🔥 Generar Informe con IA", type="primary"):
        with st.spinner("Procesando..."):
            contexto_row = next((r for r in hoja_clientes.get_all_records() if r.get('Cliente') == cliente_seleccionado), {})
            contexto_cliente = contexto_row.get('ContextoAdicional', '')

            prompt = f"""Eres redactor senior de Vultur 360. Genera informe en el estilo exacto del ejemplo que conoces.

Cliente: {cliente_seleccionado}
Periodo: {periodo}
Contexto: {contexto_cliente}
Notas: {notas}

Genera el informe completo."""

            groq = get_groq_client()
            respuesta = groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.65,
                max_tokens=4000
            )

            texto_informe = respuesta.choices[0].message.content

            st.subheader("📝 Vista Previa")
            st.text_area("Informe", texto_informe, height=500)

            # === PDF ===
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=11)
            for line in texto_informe.split('\n'):
                pdf.multi_cell(0, 8, line.encode('latin-1', 'replace').decode('latin-1'))
            
            pdf_bytes = pdf.output(dest='S').encode('latin-1', 'replace')

            st.download_button(
                label="⬇️ Descargar PDF",
                data=pdf_bytes,
                file_name=f"Informe_{cliente_seleccionado}_{periodo}.pdf",
                mime="application/pdf"
            )

            # Guardar en Histórico (solo si no existe o se quiere actualizar)
            if st.button("💾 Guardar este informe en Histórico"):
                nueva_fila = [cliente_seleccionado, periodo, "", "", "", "", "", "", "", notas, texto_informe[:500]]
                hoja_historico.append_row(nueva_fila)
                st.success("Informe guardado en histórico")

st.sidebar.info("Histórico automático activado")

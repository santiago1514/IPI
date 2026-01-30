"""
============================================================
SISTEMA INTEGRAL DE RIESGO OPERACIONAL
Cálculo del Componente de Pérdida – IPI
============================================================

Este aplicativo en Streamlit permite calcular el componente
de pérdida operacional bajo el enfoque IPI, utilizando:

- RERO_PÉRDIDA (Anexo 9)
- RERO_RECUPERADO (Anexo 10)
- Base de Eventos de Riesgo Operacional (EROs)

El cálculo considera:
- Ventana móvil de 60 meses
- Umbral configurable
- Clasificación Tipo A y Tipo B
- Agrupación por bandas anuales (noviembre–octubre)

"""

# ==========================================================
# IMPORTACIÓN DE LIBRERÍAS
# ==========================================================

import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime
import streamlit as st
import json 
from pathlib import Path


# ==========================================================
# CONFIGURACIÓN HISTORIAL IPI
# ==========================================================
meses = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

anio = st.selectbox("Año", range(2025, datetime.now().year + 1))
mes_num = st.selectbox("Mes", meses.keys(), format_func=lambda x: meses[x])

periodo = f"{anio}-{mes_num:02d}"
st.write("Periodo seleccionado:", periodo)

DATA_FILE = Path("data_ipi.json")
def leer_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ==========================================================
# CONFIGURACIÓN GENERAL DE LA PÁGINA
# ==========================================================
st.set_page_config(
    page_title="Cálculo Componente de Pérdida",
    layout="wide"
)


# ==========================================================
# COLORES CORPORATIVOS
# ==========================================================
AZUL_CORP = "#004b93"
AMARILLO_CORP = "#ffcc00"

# ==========================================================
# ESTILOS PERSONALIZADOS (CSS)
# ==========================================================
st.markdown(f"""
    <style>
    .stApp {{ background-color: #383838; }}
    [data-testid="stHeader"] {{ background-color: {AZUL_CORP}; color: Black; }}
    .stButton>button {{
        background-color: {AZUL_CORP};
        color: Black;
        border-radius: 5px;
    }}
    [data-testid="stMetricValue"] {{ color: {AZUL_CORP} !important; font-weight: bold; }}
    [data-testid="stMetricLabel"] {{ color: #383838 !important; }}
    [data-testid="stMetric"] {{
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid {AMARILLO_CORP};
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05);
    }}
    </style>
    """, unsafe_allow_html=True)

# ==========================================================
# FUNCIÓN: EXPORTACIÓN A EXCEL
# ==========================================================
def to_excel(res, cp, c_val, ipi):
    """
    Genera un archivo Excel consolidado con múltiples hojas.

    Hojas generadas:
    - Resumen Ejecutivo
    - Eventos sobre Umbral
    - Data Procesada
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        res['tabla_final'].to_excel(writer, sheet_name='Resumen Ejecutivo')
        res['df_filtrado'].to_excel(writer, sheet_name='Eventos sobre Umbral')
        res['DATA'].to_excel(writer, sheet_name='Data Procesada')

        df_resultados = pd.DataFrame({
            "Métrica": ["CP (Promedio x 15)", "Cociente (C)", "IPI Asignado"],
            "Valor": [cp, c_val, ipi]
        })
        df_resultados.to_excel(writer, sheet_name='Resultados IPI')

    return output.getvalue()

# ==========================================================
# FUNCIÓN: CALCULO DE IPI
# ==========================================================
def obtener_ipi(c):
    if c <= 0.2: return 0.7
    elif c <= 0.4: return 0.8
    elif c <= 0.7: return 0.9
    elif c <= 1.0: return 1.0
    elif c <= 1.4: return 1.1
    elif c <= 1.8: return 1.2
    elif c <= 2.3: return 1.3
    elif c <= 2.9: return 1.4
    elif c <= 3.6: return 1.5
    elif c <= 4.4: return 1.6
    else: return 1.7

# ==========================================================
# FUNCIÓN PRINCIPAL DE CÁLCULO IPI
# ==========================================================
def ejecutar_calculo(An9, An10, umbral_input):
    """
    Ejecuta el cálculo del componente de pérdida operacional.

    Parámetros:
    - An9: DataFrame RERO_PÉRDIDA
    - An10: DataFrame RERO_RECUPERADO
    - df: Base EROs
    - umbral_input: Umbral monetario definido por el usuario

    Retorna:
    - DATA procesada
    - df_filtrado (eventos sobre umbral)
    - tabla_final consolidada
    - promedio anual de pérdidas
    """

    # ------------------------------------------------------
    # 1. FILTRADO VENTANA DE 60 MESES
    # ------------------------------------------------------
    An9["Fecha_de_registro_contable"] = pd.to_datetime(
        An9["Fecha_de_registro_contable"]
    )
    ultima_fecha    = An9["Fecha_de_registro_contable"].max()
    fecha_min       = ultima_fecha - pd.DateOffset(months=60)

    An9_2 = An9[
        (An9["Fecha_de_registro_contable"] >= fecha_min) &
        (An9["Fecha_de_registro_contable"] <= ultima_fecha)
    ].copy()

    # ------------------------------------------------------
    # 2. CRUCE CON RECUPERACIONES (ANEXO 10)
    # ------------------------------------------------------
    An10["Cuentas Catálogo Recuperación"] = An10["Cuentas_catalogo_afectadas"]
    An10["Recuperacion"] = (
        An10["Cuantia_recuperada_por_seguros"] +
        An10["Cuantia_de_otras_recuperaciones"]
    )

    An10_agg = (
        An10 
        .groupby("Referencia", as_index=False) 
        .agg({ 
            "Recuperacion": "sum", 
            "Fecha_de_recuperacion": "max", 
            "Cuentas Catálogo Recuperación": "first"
        })
    )

    AN9 = An9_2.merge(An10_agg, on="Referencia", how="left")

    # Normalizamos recuperaciones como numérico y dejamos catálogo como cadena vacía si falta
    AN9["Recuperacion"] = pd.to_numeric(AN9["Recuperacion"], errors="coerce").fillna(0)
    AN9["Cuentas Catálogo Recuperación"] = AN9["Cuentas Catálogo Recuperación"].fillna("")
    
    # ------------------------------------------------------
    # 3. CÁLCULO DE PÉRDIDA NETA
    # ------------------------------------------------------
    AN9["Cuantia_bruta"] = pd.to_numeric(AN9["Cuantia_bruta"], errors="coerce").fillna(0)
    # Recuperacion ya normalizada arriba; asignamos directamente como cuantía recuperada
    AN9["Cuantia_recuperada_por_seguros"] = AN9["Recuperacion"]

    AN9["Pérdida neta ( Pérdida bruta menos recuperaciones)"] = (
        AN9["Cuantia_bruta"] -
        AN9["Cuantia_recuperada_por_seguros"]
    )

    AN9.columns = AN9.columns.astype(str)

    # ------------------------------------------------------
    # 4. ESTRUCTURA BASE DE DATOS
    # ------------------------------------------------------
    DATA = AN9[
        [
            "Referencia",
            "Fecha_de_registro_contable",
            "Fecha_de_recuperacion",
            "Cuantia_bruta",
            "Cuantia_recuperada_por_seguros",
            "Pérdida neta ( Pérdida bruta menos recuperaciones)",
            "Clase_de_riesgo_operacional_nivel_2",
            "Cuentas_catalogo_afectadas",
            "Cuentas Catálogo Recuperación"
        ]
    ].copy()

    # ------------------------------------------------------
    # 5. DEFINICIÓN DE AÑO BANDA (NOV–OCT)
    # ------------------------------------------------------
    DATA["Fecha"] = pd.to_datetime(DATA["Fecha_de_registro_contable"], errors="coerce")
    DATA["anio_nov"] = DATA["Fecha"].dt.year
    DATA.loc[DATA["Fecha"].dt.month <= 10, "anio_nov"] -= 1
    DATA["Año_banda"] = DATA["anio_nov"] - DATA["anio_nov"].min() + 1

    # ------------------------------------------------------
    # 6. IDENTIFICACIÓN DE EVENTOS TIPO A
    # ------------------------------------------------------
    df_agrupado = (
        DATA
        .groupby(["Año_banda", "Referencia"], as_index=False)
        ["Pérdida neta ( Pérdida bruta menos recuperaciones)"]
        .sum()
    )

    df_filtrado = df_agrupado[
        df_agrupado["Pérdida neta ( Pérdida bruta menos recuperaciones)"] > umbral_input
    ]
    
    refs_umbral = set(df_filtrado["Referencia"].unique())
    DATA["Tipo de umbral"] = DATA["Referencia"].apply(lambda x: "A" if x in refs_umbral else "B")

    # ------------------------------------------------------
    # 7. TABLA FINAL CONSOLIDADA
    # ------------------------------------------------------
    totalizador_umbral = pd.DataFrame([
        {
            "Año": anio, 
            "Total Pérdida neta": 
            df_filtrado[df_filtrado["Año_banda"] == anio]
            ["Pérdida neta ( Pérdida bruta menos recuperaciones)"].sum()
        } 
        for anio in df_filtrado["Año_banda"].unique()
    ])

    DATA2 = DATA[DATA["Tipo de umbral"] == 'B'].copy()

    map_riesgo_nivel_2 = {
    11: "1.1 Actividades no Autorizadas",
    12: "1.2 Hurto y Fraude Interno",
    13: "1.3 Seguridad de los sistemas",
    14: "1.4 Otros",

    21: "2.1 Hurto y Fraude Externo",
    22: "2.2 Seguridad de los sistemas",
    23: "2.3 Otros",

    31: "3.1 Relaciones Laborales",
    32: "3.2 Higiene y Seguridad laboral",
    33: "3.3 Desigualdad y Discriminación",
    34: "3.4 Otros",

    41: "4.1 Indebida Divulgación de Información y Abuso de Confianza",
    42: "4.2 Prácticas Empresariales o de Mercado Improcedentes",
    43: "4.3 Productos inadecuados",
    44: "4.4 Actividades de Asesoramiento",
    45: "4.5 Otros",

    51: "5.1 Desastres naturales",
    52: "5.2 Otros acontecimientos",
    53: "5.3 Otras causas externas",

    61: "6.1 Sistemas",
    62: "6.2 Otros",

    71: "7.1 Recepción, Ejecución y Mantenimiento de Operaciones",
    72: "7.2 Seguimiento y Presentación de Informes",
    73: "7.3 Aceptación de Clientes y Documentación",
    74: "7.4 Gestión de Cuentas de Clientes",
    75: "7.5 Incumplimiento de la regulación vigente",
    76: "7.6 Acuerdos y Convenios Comerciales",
    77: "7.7 Proveedores",
    78: "7.8 Otros"
    }
    
    DATA2["Clase_de_riesgo_operacional_nivel_2"] = DATA2["Clase_de_riesgo_operacional_nivel_2"].map(map_riesgo_nivel_2)
    DATA["Clase_de_riesgo_operacional_nivel_2"] = DATA["Clase_de_riesgo_operacional_nivel_2"].map(map_riesgo_nivel_2)

    tabla_riesgo_banda          = DATA2.groupby(["Clase_de_riesgo_operacional_nivel_2", "Año_banda"], observed=True)["Cuantia_bruta"].sum().reset_index()    
    tabla_riesgo_banda_umbral   = tabla_riesgo_banda[tabla_riesgo_banda["Cuantia_bruta"] >= umbral_input]
    totalizador_umbral_anio     = tabla_riesgo_banda_umbral.groupby("Año_banda")["Cuantia_bruta"].sum().reset_index()      

    A = totalizador_umbral.set_index("Año")["Total Pérdida neta"] if not totalizador_umbral.empty else pd.Series(dtype=float)
    A.name = "Tipo A"
    B = totalizador_umbral_anio.set_index("Año_banda")["Cuantia_bruta"] if not totalizador_umbral_anio.empty else pd.Series(dtype=float)
    B.name = "Tipo B"

    # Consolidar por año: columnas = años, filas = Tipo A / Tipo B
    tabla_final = pd.concat([A, B], axis=1).fillna(0).T
    tabla_final["TOTAL"] = tabla_final.sum(axis=1)
    # Agregar fila TOTAL (suma por columnas/años)
    tabla_final.loc["TOTAL"] = tabla_final.sum()
    # Promedio anual: media de los totales por año (excluyendo la columna TOTAL)
    if not tabla_final.empty:
        per_year_totals = tabla_final.loc["TOTAL"].drop("TOTAL")
        promedio_anual = per_year_totals.mean()
    else:
        promedio_anual = 0

    clases_B = set(
        zip(
            tabla_riesgo_banda_umbral["Clase_de_riesgo_operacional_nivel_2"],
            tabla_riesgo_banda_umbral["Año_banda"]
        )
    )

    def asignar_umbral(row):
        # Verificamos si la columna existe en la fila actual
        ref     = row.get("Referencia"                          , None)
        clase   = row.get("Clase_de_riesgo_operacional_nivel_2" , None)
        anio    = row.get("Año_banda"                       , None)
        
        if ref in refs_umbral:
            return "A"
        elif (clase, anio) in clases_B:
            return "B"
        else:
            return "N/A"

    DATA = DATA.copy()
    DATA["Tipo de umbral"] = DATA.apply(asignar_umbral, axis=1)


    return {"DATA": DATA, "df_filtrado": df_filtrado, "tabla_final": tabla_final, "promedio_anual": promedio_anual}

# ==========================================================
# ENCABEZADO CORPORATIVOS
# ==========================================================
header_col1, header_col2 = st.columns([1, 4])
with header_col1:
    # Logo Coltefinanciera
    try:
        st.image("logo_empresa.png", width=120) 
    except:
        st.title("🏦") # Fallback si no hay imagen

with header_col2:
    st. title       ("Sistema Integral de Riesgo Operacional"   )
    st. subheader   ("Cálculo Componente de perdida"            )

# ==========================================================
# BARRA LATERAL IZQUIERDA
# ==========================================================
with st.sidebar:
    st.header("⚙️ Parámetros")
    umbral_val  = st.number_input("Umbral de cuantía"                       , value=27470842.66,    format="%.2f")
    cin_input   = st.number_input("CIN: Componente de Indicador de Negocio" , value=13946774132.33,  format="%.2f")
    st.divider  ()
    st.info     ("Cargue los archivos para iniciar el análisis.")

# ==========================================================
# CARGA DE ARCHIVOS
# ==========================================================
col_f1, col_f2, col_f3  = st.columns        (3)
with col_f1: file_an9   = st.file_uploader  ("📂 RERO_PERDIDA"      ,   type=["xlsx"])
with col_f2: file_an10  = st.file_uploader  ("📂 RERO_RECUPERADO"   ,   type=["xlsx"])

if file_an9 and file_an10:
    if st.button("▶ Ejecutar cálculo IPI", width="stretch"):
        An9     = pd.read_excel(file_an9 )
        An10    = pd.read_excel(file_an10)

        res = ejecutar_calculo(An9, An10, umbral_val)

# ==========================================================
# CALCULO COCIENTE (C)
# ==========================================================
        cp_calculado = res['promedio_anual'] * 15
        c_cociente = cp_calculado / cin_input if cin_input > 0 else 0
        ipi_final = obtener_ipi(c_cociente)

# ==========================================================
# BOTÓN DE DESCARGA EXCEL
# ==========================================================
        excel_data = to_excel(res, cp_calculado, c_cociente, ipi_final)
        st.sidebar.download_button(
            label       =   "📥 Descargar Reporte Excel",
            data        =   excel_data,
            file_name   =   "Reporte_IPI_Consolidado.xlsx",
            mime        =   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )




# ==========================================================
# VISUALIZACIÓN EN PANTALLA
# ==========================================================
        st.divider()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Promedio perdida base Rero", f"${res['promedio_anual']:,.0f}")
        m2.metric("Promedio x 15 (Capital)", f"${res['promedio_anual']*15:,.0f}")
        m3.metric("Cociente (C)", f"{c_cociente:.4f}")
        m4.metric("Indicador IPI", f"{ipi_final}")

        st.success(f"Resultado: Con un Cociente **C = {c_cociente:.4f}**, el IPI asignado es **{ipi_final}**.")

        t1, t2 = st.tabs(["📊 Gráficos", "📋 Tablas de Datos"])

        with t1:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Evolución de Pérdidas por Año")
                fig_data = res['DATA'].groupby("Año_banda")["Pérdida neta ( Pérdida bruta menos recuperaciones)"].sum().reset_index()
                fig_bar = px.bar(fig_data, x="Año_banda", y="Pérdida neta ( Pérdida bruta menos recuperaciones)", 
                                 color_discrete_sequence=[AZUL_CORP])
                fig_bar.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_bar, width="stretch", key="barras_corp")
            
            with c2:
                st.subheader("Distribución por Segmento")
                fig_pie = px.pie(res['DATA'], values='Pérdida neta ( Pérdida bruta menos recuperaciones)', 
                                 names='Tipo de umbral', hole=0.5,
                                 color_discrete_sequence=[AZUL_CORP, AMARILLO_CORP])
                st.plotly_chart(fig_pie, width="stretch", key="pie_corp")
                
        with t2:
            st.subheader("Resumen Ejecutivo (Cifras en Pesos)")
            st.table    (res['tabla_final'].style.format("${:,.0f}"))
            
            st.subheader("Listado de Eventos sobre el Umbral")
            st.dataframe(res['df_filtrado'], width="stretch")


data = leer_data()

if data:
    st.subheader("Histórico")
    st.json(data)

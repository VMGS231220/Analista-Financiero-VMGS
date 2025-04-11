import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import datetime
import numpy as np
from deep_translator import GoogleTranslator

# Función para traducir texto
def traducir(texto, lang_destino="es"):
    try:
        return GoogleTranslator(source='auto', target=lang_destino).translate(texto)
    except:
        return texto  # si hay error, retorna el texto original

# Configuración de la página
st.set_page_config(page_title="Análisis Financiero", layout="wide")

st.title("📈 Análisis Financiero by Victor Gutierrez v2")

# Entrada del usuario
ticker = st.text_input("Para comenzar, introduzca el ticker de la empresa (ej: AAPL, MSFT, TSLA):")

if ticker:
    try:
        empresa = yf.Ticker(ticker)
        info = empresa.info

        if "shortName" in info and info["shortName"]:
            st.success(f"Obteniendo la información de {info['shortName']} ({ticker.upper()})")

            # INFORMACIÓN FUNDAMENTAL
            st.subheader("📊 Perfil de la Empresa")
            col1, col2 = st.columns([1, 3])

            with col1:
                logo_url = info.get("logo_url")
                if not logo_url:
                    sitio_web = info.get("website", "")
                    if sitio_web:
                        dominio = sitio_web.replace("http://", "").replace("https://", "").split("/")[0]
                        logo_url = f"https://logo.clearbit.com/{dominio}"
                if logo_url:
                    st.image(logo_url, width=100)
                else:
                    st.write("Logo no disponible")

            with col2:
                nombre = traducir(info.get("longName", "No disponible"))
                sector = traducir(info.get("sector", "No disponible"))
                industria = traducir(info.get("industry", "No disponible"))
                descripcion_completa = traducir(info.get("longBusinessSummary", "Descripción no disponible"))
                descripcion_breve = descripcion_completa[:600].rsplit(". ", 1)[0] + "."

                st.markdown(f"""
                **🧾 Nombre:** {nombre}  
                **🏭 Sector:** {sector}  
                **⚙️ Industria:** {industria}  
                **📌 Descripción:** {descripcion_breve}
                """)

            # INDICADORES FINANCIEROS
            st.subheader("📌 Indicadores Financieros Clave")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("📈 Precio actual", f"${info.get('currentPrice', 'N/A')}")
                st.metric("💰 Market Cap", f"${info.get('marketCap', 0):,}")

            with col2:
                st.metric("📉 P/E Ratio", info.get("trailingPE", "N/A"))
                st.metric("📊 Beta", info.get("beta", "N/A"))

            with col3:
                dividend_yield = info.get("dividendYield", 0)
                st.metric("💸 Dividend Yield", f"{dividend_yield * 100:.2f}%" if dividend_yield else "N/A")
                st.metric("🧾 EPS", info.get("trailingEps", "N/A"))

            # HISTORIAL DE PRECIOS
            st.subheader("📉 Precios históricos")
            st.markdown("Selecciona el rango de fechas:")

            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Desde", datetime.date(2018, 1, 1))
            with col2:
                end_date = st.date_input("Hasta", datetime.date.today())

            if start_date >= end_date:
                st.error("⚠️ La fecha de inicio debe ser anterior a la fecha final.")
            else:
                historial = empresa.history(start=start_date, end=end_date)
                historial_df = pd.DataFrame(historial)

                with st.expander("Ver últimos precios registrados"):
                    st.dataframe(historial_df.tail(10))

                # DESCARGAR CSV
                st.download_button(
                    label="📥 Descargar historial como CSV",
                    data=historial_df.to_csv().encode('utf-8'),
                    file_name=f'{ticker}_historial.csv',
                    mime='text/csv'
                )

                columna_precio = "Adj Close" if "Adj Close" in historial_df.columns else "Close"

                if columna_precio in historial_df.columns:
                    # GRAFICA INTERACTIVA
                    st.subheader("📊 Gráfica Interactiva (Plotly)")
                    fig_plotly = px.line(historial_df, x=historial_df.index, y=columna_precio,
                                         title=f'Precio de Cierre - {ticker.upper()}',
                                         labels={columna_precio: 'Precio ($)', 'index': 'Fecha'})
                    st.plotly_chart(fig_plotly, use_container_width=True)

                    # RENDIMIENTOS ANUALIZADOS (CAGR)
                    st.subheader("📈 Rendimientos Anualizados (CAGR)")

                    def calcular_cagr(precios, años):
                        if len(precios) < 2:
                            return None
                        precio_final = precios[-1]
                        precio_inicial = precios[0]
                        return (precio_final / precio_inicial) ** (1 / años) - 1

                    hoy = historial_df.index[-1]
                    rendimientos = {}

                    for años in [1, 3, 5]:
                        fecha_inicio = hoy - pd.DateOffset(years=años)
                        df_filtrado = historial_df[historial_df.index >= fecha_inicio]

                        if len(df_filtrado) >= 2:
                            cagr = calcular_cagr(df_filtrado[columna_precio].values, años)
                            rendimientos[f"{años} años"] = f"{cagr * 100:.2f}%"
                        else:
                            rendimientos[f"{años} años"] = "Datos insuficientes"

                    cagr_df = pd.DataFrame(rendimientos.items(), columns=["Horizonte", "CAGR"])
                    st.table(cagr_df)

                    st.markdown("""
                    **¿Qué nos muestra el CAGR?**  
                    El CAGR (Tasa de Crecimiento Anual Compuesta) muestra la velocidad constante a la que una inversión habría crecido cada año, asumiendo que los beneficios se reinvierten. Por ejemplo, si el CAGR a 5 años es del 12%, esto indica que el valor ha aumentado un 12% anual de manera compuesta durante ese período de cinco años.
                    """)

                    # VOLATILIDAD ANUALIZADA
                    st.subheader("📉 Volatilidad Anualizada")

                    # Calcular rendimientos diarios
                    historial_df['Daily Return'] = historial_df[columna_precio].pct_change()

                    # Calcular desviación estándar de los rendimientos diarios
                    std_diaria = np.std(historial_df['Daily Return'].dropna())
                    vol_anual = std_diaria * np.sqrt(252)

                    st.metric("📈 Volatilidad Anualizada", f"{vol_anual * 100:.2f}%")

                    st.markdown("""
                    **¿De qué nos sirve la Volatilidad Anualizada?**  
                    La volatilidad anualizada mide cuánto puede cambiar el precio de una acción en un año, en porcentaje. Se calcula usando la desviación estándar de los cambios diarios, ajustada por √252 (días hábiles al año). Por ejemplo, un 20% significa que el precio podría subir o bajar un 20% en promedio; un 40%, un 40%, mostrando más riesgo. Es útil para entender qué tan estable o arriesgada es una inversión.
                    """)
                else:
                    st.warning("⚠️ No se encontraron columnas válidas de precios para graficar.")
        else:
            st.error("❌ El ticker ingresado no existe. Por favor, intenta de nuevo como lo muestra el ejemplo.")
    except Exception as e:
        st.error(f"⚠️ No se han podido obtener los datos. Error: {e}")
else:
    st.info("Ingresa un ticker para comenzar.")



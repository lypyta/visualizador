import streamlit as st
import pandas as pd
import plotly.express as px
import io
import requests

# --- Configuración de la URL de Google Drive ---
# Asegúrate de que esta URL sea la correcta y tenga permisos de acceso público
GOOGLE_SHEETS_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRuj5CR1pOwlDvQY7-LRrCO4l_XaNNUfzUTnYXEO1zSuwG5W6s30HI6xhCuw-1m_w/pub?output=xlsx'

# --- Configuración inicial de la página de Streamlit ---
st.set_page_config(layout="wide")
st.title('📊 Inventario Camaras 1-2 y Reefers 1 al 10')
st.markdown("---")

# --- Función para Cargar y Procesar Datos (Caché para eficiencia) ---
# @st.cache_data # Puedes activarlo una vez que estés seguro de que los datos se actualizan correctamente
def load_and_process_data(url):
    try:
        st.info('Cargando y procesando datos desde Google Drive...')
        response = requests.get(url)
        response.raise_for_status() # Lanza un error para códigos de estado HTTP 4xx/5xx

        # Leer el archivo Excel sin encabezado y asignar manualmente después
        # Se especifica el motor 'openpyxl' para la lectura del archivo Excel
        df_raw = pd.read_excel(io.BytesIO(response.content), header=None, engine='openpyxl')

        # Nombres de columnas esperados en el orden exacto de tu Excel
        expected_excel_headers = ['DESCRIPCION', 'CAJAS APROX', 'MARCA', 'UBICACION', 'UNIDADES']
        
        # Verificar que el número de columnas leídas sea exactamente el esperado
        if len(df_raw.columns) != len(expected_excel_headers):
            st.error(f"Error: El archivo Excel tiene {len(df_raw.columns)} columnas, pero se esperaban exactamente {len(expected_excel_headers)}.")
            st.error(f"Asegúrate de que tu Excel contenga solo las columnas: {', '.join(expected_excel_headers)} en ese orden.")
            st.stop()
        
        # Asignar los nombres de columna de la lista `expected_excel_headers`
        df_raw.columns = expected_excel_headers
        
        # Los datos reales comienzan desde la segunda fila (índice 1), ya que la primera era el encabezado original
        df = df_raw.iloc[1:].copy()
        
        # --- Mapeo de nombres de columnas a nombres internos de la aplicación ---
        column_mapping = {
            'DESCRIPCION': 'Producto',
            'CAJAS APROX': 'Cajas disponibles',
            'MARCA': 'Marca',
            'UBICACION': 'Ubicacion',
            'UNIDADES': 'Unidades'
        }
        df = df.rename(columns=column_mapping)

        # --- Verificación de columnas finales requeridas ---
        required_final_cols = ['Producto', 'Cajas disponibles', 'Marca', 'Ubicacion', 'Unidades']
        missing_cols = [col for col in required_final_cols if col not in df.columns]
        if missing_cols:
            st.error(f"❌ ¡Faltan columnas esenciales después del procesamiento! Asegúrate de que tu Excel contenga los encabezados correctos: {', '.join(missing_cols)}")
            st.warning("Columnas detectadas en tu archivo y cómo se están mapeando:")
            st.dataframe(pd.DataFrame(list(column_mapping.items()), columns=['En Excel', 'Esperado por App']))
            st.dataframe(df.columns.to_frame(name='Columnas Resultantes en App'))
            st.stop()

        # --- Limpieza y estandarización de datos ---
        df['Producto'] = df['Producto'].astype(str).str.strip().str.upper()
        df['Marca'] = df['Marca'].astype(str).str.strip().str.upper()
        df['Ubicacion'] = df['Ubicacion'].astype(str).str.strip().str.upper()

        df.dropna(subset=['Producto', 'Marca', 'Ubicacion', 'Cajas disponibles'], inplace=True)
        if df.empty:
            st.warning('⚠️ El inventario está vacío después de limpiar filas sin Producto, Marca, Ubicación o Cajas disponibles.')
            st.stop()

        df['Cajas disponibles'] = pd.to_numeric(df['Cajas disponibles'], errors='coerce').fillna(0).astype(int)
        df['Unidades'] = pd.to_numeric(df['Unidades'], errors='coerce').fillna(0).astype(int)
            
        st.success('✅ ¡Datos cargados y procesados con éxito!')
        return df

    except requests.exceptions.RequestException as req_err:
        st.error(f"❌ Error de conexión al cargar el archivo. Verifica el enlace y permisos de Drive.")
        st.error(f"Detalles: {req_err}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error inesperado al leer o procesar el archivo. Asegúrate que sea un Excel válido y la estructura de columnas sea la esperada.")
        st.error(f"Detalles: {e}")
        st.stop()

# Cargar los datos al inicio de la aplicación
df = load_and_process_data(GOOGLE_SHEETS_URL)

# --- Navegación en la barra lateral ---
st.sidebar.title("Navegación")
opcion_seleccionada = st.sidebar.radio(
    "Ir a:",
    ("Inventario", "Ventas")
)

# --- Contenido principal de la aplicación basado en la selección ---
if opcion_seleccionada == "Inventario":
    # --- Componentes Interactivos (Filtros en el cuerpo principal) ---
    st.subheader('Filtros de Inventario')

    # Crear columnas para organizar los selectbox horizontalmente
    col1, col2, col3 = st.columns(3)

    with col1:
        # Preparar la lista de marcas disponibles por defecto: Por Cantidad Total de Cajas (Mayor a Menor)
        df_marcas_ordenadas = df.groupby('Marca')['Cajas disponibles'].sum().reset_index()
        df_marcas_ordenadas = df_marcas_ordenadas.sort_values('Cajas disponibles', ascending=False)
        marcas_disponibles = ['Todos'] + df_marcas_ordenadas['Marca'].tolist()

        marca_seleccionada = st.selectbox('Marca', marcas_disponibles)

    with col2:
        # Asegurarse de que las ubicaciones disponibles también estén limpias para el selectbox
        ubicaciones_disponibles = ['Todos'] + sorted(df['Ubicacion'].unique().tolist())
        ubicacion_seleccionada = st.selectbox('Ubicación', ubicaciones_disponibles)

    with col3:
        # Asegurarse de que los productos disponibles también estén limpios para el selectbox
        productos_disponibles = ['Todos'] + sorted(df['Producto'].unique().tolist())
        producto_seleccionado = st.selectbox('Producto', productos_disponibles)


    st.markdown("---") # Separador visual


    # Filtrar el DataFrame según las selecciones
    df_filtrado = df.copy() # Siempre empieza con una copia del DataFrame completo y limpio
    if marca_seleccionada != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Marca'] == marca_seleccionada]
    if ubicacion_seleccionada != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Ubicacion'] == ubicacion_seleccionada]
    if producto_seleccionado != 'Todos': # Aplicar el filtro de producto si se seleccionó uno específico
        df_filtrado = df_filtrado[df_filtrado['Producto'] == producto_seleccionado]


    # Mensaje si no hay datos después de filtrar
    if df_filtrado.empty:
        st.warning("No hay datos para la combinación de filtros seleccionada.")
    else:
        # --- Tabla del Inventario Detallado (filtrado - ordenar por Producto alfabéticamente) ---
        st.subheader(f'Inventario Detallado Completo - {marca_seleccionada} / {ubicacion_seleccionada} / {producto_seleccionado}')
        # La tabla ahora muestra las columnas en el orden solicitado y ordenada por Producto alfabéticamente
        st.dataframe(df_filtrado[['Producto', 'Cajas disponibles', 'Unidades', 'Marca','Ubicacion']].sort_values('Producto', ascending=True), use_container_width=True, hide_index=True)
        st.markdown("---") # Separador visual después de la tabla

        # --- Vista Específica: Productos y Ubicaciones por Marca (cuando se selecciona una marca) ---
        if marca_seleccionada != 'Todos' and producto_seleccionado == 'Todos':
            with st.expander(f"📦 Ver Productos y Ubicaciones para '{marca_seleccionada}'"):
                st.dataframe(
                    df_filtrado[['Producto', 'Ubicacion', 'Cajas disponibles', 'Unidades']] # Incluir 'Unidades'
                    .sort_values('Cajas disponibles', ascending=False)
                    .reset_index(drop=True),
                    use_container_width=True
                )
                st.info("Esta tabla muestra los productos y su ubicación para la marca seleccionada.")
        elif producto_seleccionado != 'Todos':
            st.info(f"Mostrando detalles para el producto: **{producto_seleccionado}**")

        # --- Nuevo Gráfico de Torta: Distribución por Ubicación para Producto Seleccionado (por Cajas disponibles) ---
        # Este gráfico se muestra solo si se selecciona un producto específico
        if producto_seleccionado != 'Todos' and not df_filtrado.empty:
            st.subheader(f"Distribución de Cajas disponibles para '{producto_seleccionado}' por Ubicación")
            df_ubicacion_total_filtrado = df_filtrado.groupby('Ubicacion')['Cajas disponibles'].sum().reset_index()
            if not df_ubicacion_total_filtrado.empty:
                fig_pie_ubicacion = px.pie(
                    df_ubicacion_total_filtrado,
                    values='Cajas disponibles',
                    names='Ubicacion',
                    title=f"Cajas disponibles de '{producto_seleccionado}' por Ubicación",
                    hole=0.3
                )
                st.plotly_chart(fig_pie_ubicacion, use_container_width=True)
            else:
                st.warning(f"No hay datos de ubicación para el producto '{producto_seleccionado}' con los filtros actuales.")

        # --- Gráfico de Torta: Distribución del Stock por Marca/Producto (¡Lógica de visualización actualizada!) ---
        # Este gráfico solo se muestra si NO se ha seleccionado un producto específico
        if producto_seleccionado == 'Todos': # Solo mostrar este gráfico si NO hay un producto específico seleccionado
            if marca_seleccionada == 'Todos':
                st.subheader(f'Distribución de Cajas disponibles por Marca - {ubicacion_seleccionada} / {producto_seleccionado}')
                df_marca_total_filtrado = df_filtrado.groupby('Marca')['Cajas disponibles'].sum().reset_index()
                if not df_marca_total_filtrado.empty:
                    fig_pie = px.pie(
                        df_marca_total_filtrado,
                        values='Cajas disponibles',
                        names='Marca',
                        title='Proporción de Cajas disponibles por Marca',
                        hole=0.3
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.warning("No hay datos de marca para mostrar en el gráfico de torta con los filtros actuales.")
            else: # Si se ha seleccionado una marca específica (y no un producto específico), mostrar distribución por producto
                st.subheader(f"Distribución de Cajas disponibles por Producto para '{marca_seleccionada}'")
                # Agrupar por Producto y sumar Cajas disponibles dentro de la marca seleccionada
                df_producto_total_filtrado = df_filtrado.groupby('Producto')['Cajas disponibles'].sum().reset_index()
                if not df_producto_total_filtrado.empty:
                    fig_pie = px.pie(
                        df_producto_total_filtrado,
                        values='Cajas disponibles',
                        names='Producto',
                        title=f"Cajas disponibles por Producto para '{marca_seleccionada}'",
                        hole=0.3
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.warning(f"No hay datos de producto para mostrar en el gráfico de torta para la marca '{marca_seleccionada}' con los filtros actuales.")


        st.markdown("---")
        st.markdown("---")

        # --- Gráfico de Barras: Stock Total por Producto (filtrado - por Cajas disponibles) ---
        st.subheader(f'Stock Total por Producto (en Cajas disponibles) - {marca_seleccionada} / {ubicacion_seleccionada} / {producto_seleccionado}')

        # Si se selecciona un producto específico, el gráfico de barras será solo para ese producto
        if producto_seleccionado != 'Todos':
            fig_bar = px.bar(
                df_filtrado,
                y='Producto', # Cambiado a eje Y para horizontal
                x='Cajas disponibles', # Cambiado a eje X para horizontal
                color='Marca',
                title=f'Stock del Producto: {producto_seleccionado}',
                labels={'Cajas disponibles': 'Total de Cajas disponibles'},
                text='Cajas disponibles',
                height=300
            )
            # Actualizaciones de layout comunes para el gráfico de un solo producto
            fig_bar.update_layout(xaxis_title='Total de Cajas disponibles', yaxis_title='Producto', showlegend=True)
        else: # Si no se selecciona producto, muestra el top 10 por Cajas disponibles
            # Paso 1: Agrupar por Producto y Marca, y sumar las Cajas disponibles
            df_agrupado = df_filtrado.groupby(['Producto', 'Marca'])['Cajas disponibles'].sum().reset_index()

            # Paso 2: Ordenar el DataFrame agrupado de forma ascendente y tomar los top 10
            top_10_productos = df_agrupado.sort_values('Cajas disponibles', ascending=True).head(10)

            fig_bar = px.bar(
                top_10_productos, # Usar el DataFrame con los top 10 productos agrupados
                y='Producto', # Cambiado a eje Y para horizontal
                x='Cajas disponibles', # Cambiado a eje X para horizontal
                color='Marca', # Mantener el color por Marca
                title='Top 10 Productos por Stock (Cajas disponibles)',
                labels={'Cajas disponibles': 'Total de Cajas disponibles'},
                text='Cajas disponibles',
                height=500
            )
            
            # Obtener la lista de productos en el orden deseado para el eje Y (menor a mayor)
            ordered_products_for_y_axis = top_10_productos['Producto'].tolist()[::-1] # Invertir la lista

            fig_bar.update_layout(
                xaxis_title='Total de Cajas disponibles',
                yaxis_title='Producto',
                showlegend=True,
                yaxis={'categoryorder': 'array', 'categoryarray': ordered_products_for_y_axis}
            )
        
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")
        
        # --- NUEVA TABLA: Resumen de Cajas y Unidades por Producto ---
        st.subheader(f'📦 Resumen Total de Cajas y Unidades por Producto')
        st.info('Esta tabla muestra la cantidad total de cajas y unidades disponibles para cada producto, considerando los filtros aplicados.')
        
        # Agrupar por 'Producto' y sumar 'Cajas disponibles' y 'Unidades'
        df_resumen_producto = df_filtrado.groupby('Producto')[['Cajas disponibles', 'Unidades']].sum().reset_index()
        
        # Renombrar las columnas de suma para mayor claridad en la tabla
        df_resumen_producto.rename(columns={
            'Cajas disponibles': 'Cantidad Total de Cajas',
            'Unidades': 'Cantidad Total de Unidades'
        }, inplace=True)
        
        # Ordenar de mayor a menor cantidad de cajas
        df_resumen_producto = df_resumen_producto.sort_values('Cantidad Total de Cajas', ascending=False)
        
        # Mostrar la tabla
        st.dataframe(df_resumen_producto, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.success("¡Dashboard de Inventario actualizado !")

elif opcion_seleccionada == "Ventas":
    st.header("📈 Dashboard de Ventas")
    st.markdown("---")
    st.info("Aquí puedes añadir tus visualizaciones y análisis de ventas.")
    st.write("Por ejemplo, podrías cargar un nuevo archivo de ventas y mostrar:")
    st.markdown("""
    - Gráfico de ventas por mes/año
    - Ventas por producto
    - Ventas por región
    - Top productos vendidos
    """)
    # Aquí iría el código para cargar y visualizar tus datos de ventas
    # Ejemplo de datos de ventas (puedes reemplazar esto con tu propia carga de datos)
    # data_ventas = {
    #     'Fecha': pd.to_datetime(['2023-01-15', '2023-01-20', '2023-02-10', '2023-02-25', '2023-03-05']),
    #     'Producto': ['Producto A', 'Producto B', 'Producto A', 'Producto C', 'Producto B'],
    #     'Cantidad Vendida': [10, 5, 12, 8, 7],
    #     'Ingresos': [100, 75, 120, 160, 105]
    # }
    # df_ventas = pd.DataFrame(data_ventas)
    # st.subheader("Datos de Ventas (Ejemplo)")
    # st.dataframe(df_ventas)
    # st.subheader("Gráfico de Ventas por Producto (Ejemplo)")
    # fig_ventas_producto = px.bar(df_ventas.groupby('Producto')['Cantidad Vendida'].sum().reset_index(),
    #                              x='Producto', y='Cantidad Vendida', title='Cantidad Vendida por Producto')
    # st.plotly_chart(fig_ventas_producto, use_container_width=True)

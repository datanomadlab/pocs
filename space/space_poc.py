import duckdb
import streamlit as st
import pandas as pd
import plotly.express as px
from sklearn.ensemble import RandomForestClassifier

st.set_page_config(
    page_title= "Space Analytics", 
    layout="wide",
    page_icon="🚀"
)

# Diccionario de ubicaciones conocidas
LAUNCH_SITES = {
    'Kennedy Space Center': {'lat': 28.5728, 'lon': -80.6490},
    'Cape Canaveral': {'lat': 28.4922, 'lon': -80.5772},
    'Baikonur Cosmodrome': {'lat': 45.9646, 'lon': 63.3052},
    'Jiuquan Satellite Launch Center': {'lat': 40.9608, 'lon': 100.2979},
    'Boca Chica': {'lat': 25.9973, 'lon': -97.1559},
    'Vandenberg': {'lat': 34.7420, 'lon': -120.5724},
    'Kourou': {'lat': 5.2520, 'lon': -52.7829},
    'Tanegashima': {'lat': 30.3984, 'lon': 130.9750},
    'Wenchang': {'lat': 19.6145, 'lon': 110.9510},
    'Xichang': {'lat': 28.2463, 'lon': 102.0277},
    'Plesetsk Cosmodrome': {'lat': 62.9271, 'lon': 40.5777},
    'Wallops': {'lat': 37.8383, 'lon': -75.4383},
    'Semnan': {'lat': 35.2345, 'lon': 53.9215},
    'Taiyuan': {'lat': 38.8491, 'lon': 111.6087},
    'Guiana Space Centre': {'lat': 5.2322, 'lon': -52.7693},
    'Mahia': {'lat': -39.2622, 'lon': 177.8647},
}

# 1. Cargar datos desde CSV local
@st.cache_data
def load_data():
    df = pd.read_csv("mission_launches.csv")
    
    # Limpieza básica
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Year'] = df['Date'].dt.year
    df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
    
    return df

df = load_data()

# 2. Configurar DuckDB
conn = duckdb.connect()
conn.register('lanzamientos', df)

# 3. Análisis con SQL
query = """
SELECT 
    Organisation,
    COUNT(*) AS Total_Launches,
    AVG(CASE WHEN Mission_Status = 'Success' THEN 1 ELSE 0 END) AS Success_Rate,
    AVG(Price) AS Avg_Price
FROM lanzamientos
GROUP BY Organisation
ORDER BY Total_Launches DESC
"""
org_stats = conn.execute(query).fetchdf()

# 4. Modelo de ML
@st.cache_resource
def train_model():
    model = RandomForestClassifier()
    
    # Limpieza exhaustiva
    features = pd.get_dummies(df[['Organisation', 'Year', 'Price']], drop_first=True)
    
    # Convertir todos los valores no exitosos a 0
    target = df['Mission_Status'].apply(
        lambda x: 1 if str(x).lower() == 'success' else 0
    )
    
    # Filtrar filas con datos faltantes
    valid_rows = ~features.isna().any(axis=1) & ~target.isna()
    
    model.fit(features[valid_rows].fillna(0), target[valid_rows])
    return model, features.columns

# Entrenar el modelo y obtener las características
model, feature_names = train_model()

# Sección 1: Estadísticas
col1, col2 = st.columns(2)
with col1:
    st.subheader("Lanzamientos por Año")
    year_counts = df.groupby('Year').size()
    st.line_chart(year_counts)

with col2:
    st.subheader("Top Organizaciones")
    st.dataframe(
        org_stats.style.format({
            'Success_Rate': '{:.1%}',
            'Avg_Price': '${:,.2f}M'
        }),
        height=400
    )

# Sección 2: Predicción
st.subheader("Predictor de Éxito")
col3, col4, col5 = st.columns(3)
with col3:
    org = st.selectbox("Organización", df['Organisation'].unique())
with col4:
    year = st.slider("Año", int(df['Year'].min()), 2030)
with col5:
    price = st.number_input("Precio (Millones USD)", min_value=0.0, value=50.0)

if st.button("Predecir"):
    input_data = pd.DataFrame([[org, year, price]], 
                            columns=['Organisation', 'Year', 'Price'])
    features = pd.get_dummies(input_data).reindex(columns=feature_names, fill_value=0)
    proba = model.predict_proba(features)[0][1]
    
    st.success(f"Probabilidad de éxito: {proba*100:.2f}%")
    st.plotly_chart(px.pie(
        names=['Éxito', 'Fracaso'], 
        values=[proba, 1-proba],
        color_discrete_sequence=['#2ecc71', '#e74c3c']
    ))

# Sección 3: Mapa de Lanzamientos
st.subheader("Mapa Global de Lanzamientos")

try:
    # Crear DataFrame para el mapa
    launch_locations = []
    for index, row in df.iterrows():
        location = str(row['Location']).lower()
        for site_name, coords in LAUNCH_SITES.items():
            if any(keyword in location for keyword in [site_name.lower(), site_name.split()[0].lower()]):
                launch_locations.append({
                    'lat': coords['lat'],
                    'lon': coords['lon'],
                    'Organisation': row['Organisation'],
                    'Mission_Status': row['Mission_Status'],
                    'Location': site_name,
                    'count': 1
                })
                break
    
    if launch_locations:
        df_map = pd.DataFrame(launch_locations)
        # Agregar por ubicación
        df_map_agg = df_map.groupby(['Location', 'lat', 'lon']).agg({
            'count': 'sum',
            'Organisation': lambda x: ', '.join(pd.unique(x)[:3])  # Mostrar hasta 3 organizaciones
        }).reset_index()
        
        fig = px.scatter_geo(
            df_map_agg,
            lat='lat',
            lon='lon',
            size='count',  # Tamaño basado en número de lanzamientos
            color='count',
            hover_name='Location',
            hover_data=['Organisation'],
            title=f'Sitios de Lanzamiento ({len(df_map_agg)} ubicaciones)',
            projection='natural earth'  # Corregido aquí
        )
        
        fig.update_geos(
            showcoastlines=True,
            coastlinecolor="RebeccaPurple",
            showland=True,
            landcolor="LightGray",
            showocean=True,
            oceancolor="LightBlue",
            showframe=False,
            showcountries=True,
            countrycolor="Gray"
        )
        
        fig.update_traces(
            marker=dict(
                sizeref=2,
                sizemin=5,
                sizemode='area',
                line=dict(width=1, color='DarkSlateGrey')
            )
        )
        
        fig.update_layout(
            margin=dict(l=0, r=0, t=30, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            geo=dict(
                bgcolor='rgba(0,0,0,0)',
                framecolor='rgba(0,0,0,0)'
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Mostrar estadísticas de ubicaciones
        st.write("### Estadísticas por Sitio de Lanzamiento")
        stats_df = df_map_agg.sort_values('count', ascending=False)
        st.dataframe(stats_df[['Location', 'count', 'Organisation']])
    else:
        st.warning("No se encontraron ubicaciones conocidas en los datos.")
        
except Exception as e:
    st.error(f"Error al generar el mapa: {str(e)}")
    st.write("Estructura de los datos:")
    st.write(df['Location'].value_counts().head())
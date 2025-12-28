import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import glob
import os
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Beijing Air Quality Dashboard",
    page_icon="🌫️",
    layout="wide"
)

# --- JUDUL DASHBOARD ---
st.title("🌫️ Beijing Air Quality Analysis Dashboard")
st.markdown("""
Dashboard ini adalah implementasi interaktif dari proyek analisis data kualitas udara.
Fokus analisis meliputi:
- **Eksplorasi Data (EDA)**: Korelasi dan distribusi.
- **Analisis Tren (Q1)**: Pola tahunan dan musiman.
- **Analisis Cuaca (Q2)**: Dampak suhu, hujan, dan angin.
- **Advanced Analysis**: Clustering kondisi udara.
""")

# --- FUNGSI LOAD DATA (PERSIS SEPERTI NOTEBOOK) ---
@st.cache_data
def load_data():
    # 1. Gathering Data
    folder_path = "PRSA_Data_20130301-20170228"
    
    if not os.path.exists(folder_path):
        st.error(f"Folder '{folder_path}' tidak ditemukan.")
        return None

    all_files = glob.glob(os.path.join(folder_path, "*.csv"))
    
    df_list = []
    for filename in all_files:
        df_temp = pd.read_csv(filename)
        df_list.append(df_temp)
    
    if not df_list:
        return None

    main_df = pd.concat(df_list, axis=0, ignore_index=True)
    
    # 2. Data Cleaning (Sesuai Notebook)
    # A. Datetime Conversion
    main_df['datetime'] = pd.to_datetime(main_df[['year', 'month', 'day', 'hour']])
    main_df.drop(columns=['year', 'month', 'day', 'hour'], inplace=True)
    
    # B. Handling Missing Values
    # Interpolasi Linear untuk data numerik (Time Series Best Practice)
    numeric_cols = main_df.select_dtypes(include=['float64', 'int64']).columns
    for col in numeric_cols:
        main_df[col] = main_df[col].interpolate(method='linear')
    
    # Forward Fill untuk kolom kategori (Arah Angin / wd)
    if 'wd' in main_df.columns:
        main_df['wd'] = main_df['wd'].ffill()
    
    # C. Menambah kolom waktu kembali untuk keperluan filtering & grouping
    main_df['year'] = main_df['datetime'].dt.year
    main_df['month'] = main_df['datetime'].dt.month
    
    return main_df

# Load Data
data = load_data()

if data is None:
    st.warning("Data tidak ditemukan. Pastikan folder dataset sudah benar.")
    st.stop()

# --- SIDEBAR FILTER ---
st.sidebar.header("🎛️ Filter Dashboard")

# Filter Stasiun
station_list = data['station'].unique().tolist()
selected_station = st.sidebar.multiselect("Pilih Stasiun:", station_list, default=station_list)

# Filter Tahun
year_min = int(data['year'].min())
year_max = int(data['year'].max())
selected_year = st.sidebar.slider("Pilih Rentang Tahun:", min_value=year_min, max_value=year_max, value=(year_min, year_max))

# Terapkan Filter
filtered_df = data[
    (data['station'].isin(selected_station)) & 
    (data['year'] >= selected_year[0]) & 
    (data['year'] <= selected_year[1])
]

# --- METRIK RINGKAS ---
st.subheader("📊 Key Metrics")
col1, col2, col3, col4 = st.columns(4)

avg_pm25 = filtered_df['PM2.5'].mean()
max_pm25 = filtered_df['PM2.5'].max()
avg_temp = filtered_df['TEMP'].mean()

# Logika Kondisi Sederhana
if avg_pm25 < 50:
    cond_label = "Baik 🟢"
elif avg_pm25 < 100:
    cond_label = "Sedang 🟡"
else:
    cond_label = "Buruk 🔴"

col1.metric("Rata-rata PM2.5", f"{avg_pm25:.2f} µg/m³")
col2.metric("Max PM2.5", f"{max_pm25:.2f} µg/m³")
col3.metric("Rata-rata Suhu", f"{avg_temp:.2f} °C")
col4.metric("Status Udara", cond_label)

st.markdown("---")

# --- TABS ANALYSIS (STRUKTUR SAMA DENGAN NOTEBOOK) ---
tab1, tab2, tab3, tab4 = st.tabs(["1. Exploratory Data Analysis (EDA)", "2. Tren & Musiman (Q1)", "3. Faktor Cuaca (Q2)", "4. Clustering (Advanced)"])

# === TAB 1: EDA ===
with tab1:
    st.header("Exploratory Data Analysis")
    st.markdown("Melihat hubungan antar variabel dan distribusi data sebelum analisis mendalam.")
    
    col_eda_1, col_eda_2 = st.columns(2)
    
    with col_eda_1:
        st.subheader("Correlation Matrix (Heatmap)")
        # Hitung korelasi (hanya kolom numerik penting)
        corr_cols = ['PM2.5', 'PM10', 'SO2', 'NO2', 'CO', 'O3', 'TEMP', 'PRES', 'DEWP', 'RAIN', 'WSPM']
        corr_matrix = filtered_df[corr_cols].corr()
        
        fig_corr, ax_corr = plt.subplots(figsize=(10, 8))
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f", linewidths=0.5, ax=ax_corr)
        st.pyplot(fig_corr)
        st.caption("Insight: Perhatikan korelasi kuat antara PM2.5 dengan PM10/CO, dan korelasi negatif dengan WSPM (Angin).")

    with col_eda_2:
        st.subheader("Distribusi PM2.5")
        fig_hist, ax_hist = plt.subplots(figsize=(10, 6))
        sns.histplot(filtered_df['PM2.5'], bins=50, kde=True, color='skyblue', ax=ax_hist)
        ax_hist.set_title("Histogram Distribusi PM2.5")
        st.pyplot(fig_hist)
        st.caption("Insight: Distribusi data miring ke kanan (Right-Skewed), menunjukkan adanya outlier polusi ekstrem.")

# === TAB 2: PERTANYAAN 1 ===
with tab2:
    st.header("Pertanyaan 1: Tren & Pola Musiman")
    st.markdown("**Bagaimana tren kualitas udara dari waktu ke waktu?**")
    
    # 1. Tren Time Series Bulanan
    monthly_trend = filtered_df.groupby(filtered_df['datetime'].dt.to_period("M"))['PM2.5'].mean().reset_index()
    monthly_trend['datetime'] = monthly_trend['datetime'].dt.to_timestamp()
    
    st.subheader("Tren Rata-Rata PM2.5 Bulanan")
    fig_trend, ax_trend = plt.subplots(figsize=(14, 6))
    sns.lineplot(data=monthly_trend, x='datetime', y='PM2.5', marker='o', linewidth=2, color='tab:red', ax=ax_trend)
    ax_trend.set_ylabel("PM2.5 (ug/m3)")
    ax_trend.grid(True)
    st.pyplot(fig_trend)
    
    # 2. Pola Musiman
    st.subheader("Pola Musiman (Rata-rata per Bulan)")
    seasonal_pattern = filtered_df.groupby('month')['PM2.5'].mean().reset_index()
    
    fig_season, ax_season = plt.subplots(figsize=(10, 5))
    # Highlight musim dingin (Nov, Dec, Jan, Feb)
    colors = ['#FF6347' if x in [11, 12, 1, 2] else '#D3D3D3' for x in seasonal_pattern['month']]
    
    sns.barplot(data=seasonal_pattern, x='month', y='PM2.5', palette=colors, ax=ax_season)
    ax_season.set_xticks(range(12))
    ax_season.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
    st.pyplot(fig_season)
    
    st.info("""
    **Conclusion Q1:**
    Terlihat pola musiman yang jelas di mana kualitas udara memburuk pada musim dingin (Nov-Feb). 
    Hal ini kemungkinan disebabkan oleh penggunaan pemanas ruangan dan kondisi atmosfer yang stagnan.
    """)

# === TAB 3: PERTANYAAN 2 ===
with tab3:
    st.header("Pertanyaan 2: Pengaruh Cuaca")
    st.markdown("**Bagaimana pengaruh Suhu, Hujan, dan Angin terhadap PM2.5?**")
    
    # Menggunakan 3 kolom agar rapi
    col_q2_1, col_q2_2, col_q2_3 = st.columns(3)
    
    # Sample data agar scatter plot tidak terlalu berat jika data jutaan baris
    if len(filtered_df) > 5000:
        plot_data = filtered_df.sample(5000, random_state=42)
    else:
        plot_data = filtered_df
    
    with col_q2_1:
        st.markdown("#### Suhu vs PM2.5")
        fig_temp, ax_temp = plt.subplots(figsize=(6, 6))
        sns.scatterplot(data=plot_data, x='TEMP', y='PM2.5', alpha=0.2, color='orange', ax=ax_temp)
        ax_temp.set_xlabel("Suhu (°C)")
        st.pyplot(fig_temp)

    with col_q2_2:
        st.markdown("#### Hujan vs PM2.5")
        # Filter hujan > 0 agar lebih jelas
        rain_data = plot_data[plot_data['RAIN'] > 0]
        fig_rain, ax_rain = plt.subplots(figsize=(6, 6))
        sns.scatterplot(data=rain_data, x='RAIN', y='PM2.5', alpha=0.4, color='blue', ax=ax_rain)
        ax_rain.set_xlabel("Curah Hujan (mm)")
        st.pyplot(fig_rain)
        
    with col_q2_3:
        st.markdown("#### Angin vs PM2.5")
        fig_wind, ax_wind = plt.subplots(figsize=(6, 6))
        sns.scatterplot(data=plot_data, x='WSPM', y='PM2.5', alpha=0.2, color='green', ax=ax_wind)
        ax_wind.set_xlabel("Kecepatan Angin (m/s)")
        st.pyplot(fig_wind)
        
    st.info("""
    **Conclusion Q2:**
    - **Suhu:** PM2.5 cenderung tinggi saat suhu rendah.
    - **Hujan & Angin:** Berkorelasi negatif dengan PM2.5 (berfungsi sebagai pembersih udara).
    """)

# === TAB 4: CLUSTERING (LENGKAP) ===
with tab4:
    st.header("Analisis Lanjutan: Clustering K-Means")
    st.markdown("Mengelompokkan data berdasarkan karakteristik cuaca dan polusi untuk menemukan pola tersembunyi.")
    
    # Tombol untuk menjalankan clustering (agar tidak auto-run saat load awal)
    if st.button("Jalankan Clustering"):
        with st.spinner("Sedang melakukan clustering..."):
            # 1. Prepare Data (Sampling untuk performa)
            if len(filtered_df) > 10000:
                cluster_data = filtered_df.sample(10000, random_state=42).copy()
            else:
                cluster_data = filtered_df.copy()
            
            features = ['PM2.5', 'TEMP', 'WSPM', 'RAIN']
            X = cluster_data[features].dropna()
            
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # 2. Fit K-Means
            kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
            cluster_data['Cluster'] = kmeans.fit_predict(X_scaled)
            
            # 3. Visualisasi Lengkap (3 Perspektif)
            st.subheader("Visualisasi Hasil Clustering")
            
            col_c1, col_c2, col_c3 = st.columns(3)
            
            with col_c1:
                st.markdown("**1. Cluster: Suhu vs PM2.5**")
                fig_c1, ax_c1 = plt.subplots(figsize=(6, 6))
                sns.scatterplot(data=cluster_data, x='TEMP', y='PM2.5', hue='Cluster', palette='viridis', ax=ax_c1)
                st.pyplot(fig_c1)
                
            with col_c2:
                st.markdown("**2. Cluster: Angin vs PM2.5**")
                fig_c2, ax_c2 = plt.subplots(figsize=(6, 6))
                sns.scatterplot(data=cluster_data, x='WSPM', y='PM2.5', hue='Cluster', palette='viridis', ax=ax_c2)
                st.pyplot(fig_c2)
                
            with col_c3:
                st.markdown("**3. Cluster: Hujan vs PM2.5**")
                rain_cluster = cluster_data[cluster_data['RAIN'] > 0] # Filter hujan biar jelas
                fig_c3, ax_c3 = plt.subplots(figsize=(6, 6))
                sns.scatterplot(data=rain_cluster, x='RAIN', y='PM2.5', hue='Cluster', palette='viridis', ax=ax_c3)
                st.pyplot(fig_c3)
            
            st.success("Clustering Selesai!")
            st.markdown("""
            **Insight Clustering:**
            Warna (Cluster) menunjukkan kelompok kondisi udara yang mirip. Anda bisa melihat bagaimana kombinasi Suhu dingin, Angin tenang, dan tanpa Hujan seringkali masuk ke cluster dengan PM2.5 tinggi.
            """)
    else:
        st.info("Klik tombol di atas untuk menjalankan analisis clustering.")

# --- FOOTER / COPYRIGHT ---
st.markdown("---")
st.markdown("Created by Muhammad Arief Pratama | ML Assignment GDGoC 2025")
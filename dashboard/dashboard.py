import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

st.set_page_config(
    page_title="Bike Sharing Analytics Dashboard",
    page_icon="🚲",
    layout="wide"
)
sns.set_theme(style="whitegrid")


@st.cache_data
def load_data():
    # Mencari path main_data.csv secara otomatis agar aman dijalankan dari direktori mana saja
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "main_data.csv")
    
    hour_df = pd.read_csv(file_path)
    hour_df['dteday'] = pd.to_datetime(hour_df['dteday'])
    return hour_df

hour_df = load_data()

with st.sidebar:
    st.title("🚲 Bike Sharing Filter")
    st.markdown("Gunakan filter di bawah ini untuk mengeksplorasi data penyewaan sepeda.")

    selected_years = st.multiselect(
        "Pilih Tahun:",
        options=[2011, 2012],
        default=[2012]
    )
    if not selected_years:
        selected_years = [2011, 2012]

    all_seasons = ['Spring', 'Summer', 'Fall', 'Winter']
    selected_seasons = st.multiselect(
        "Pilih Musim:",
        options=all_seasons,
        default=all_seasons
    )
    if not selected_seasons:
        selected_seasons = all_seasons

    min_date = hour_df['dteday'].min().date()
    max_date = hour_df['dteday'].max().date()
    date_range = st.date_input(
        "Rentang Tanggal:",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

if len(date_range) == 2:
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
else:
    start_date, end_date = pd.to_datetime(min_date), pd.to_datetime(max_date)

filtered_hour = hour_df[
    (hour_df['yr'].isin(selected_years)) &
    (hour_df['season'].isin(selected_seasons)) &
    (hour_df['dteday'] >= start_date) &
    (hour_df['dteday'] <= end_date)
]

filtered_day = (
    filtered_hour.groupby(['dteday', 'yr', 'season', 'workingday'], as_index=False)
    .agg(
        casual=('casual', 'sum'),
        registered=('registered', 'sum'),
        cnt=('cnt', 'sum'),
        # Mengambil kondisi cuaca paling dominan/terburuk pada hari tersebut
        weathersit=('weathersit', lambda x: x.mode()[0])
    )
)

st.title("🚲 Capital Bikeshare Analytics Dashboard")
st.markdown("Dashboard interaktif untuk menganalisis pola penyewaan sepeda berdasarkan waktu operasional, tipe pengguna, musim, dan kondisi cuaca.")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Penyewaan", f"{filtered_hour['cnt'].sum():,}")
with col2:
    st.metric("Pengguna Registered", f"{filtered_hour['registered'].sum():,}")
with col3:
    st.metric("Pengguna Casual", f"{filtered_hour['casual'].sum():,}")
with col4:
    avg_daily = filtered_day['cnt'].mean() if not filtered_day.empty else 0
    st.metric("Rata-rata Harian", f"{avg_daily:,.1f}")

st.divider()

st.subheader("1. Pola Penyewaan Per Jam: Working Day vs. Weekend/Holiday")

hourly_avg = (
    filtered_hour.groupby(['workingday', 'hr'])[['casual', 'registered']]
    .mean()
    .reset_index()
)

fig1, axes1 = plt.subplots(1, 2, figsize=(16, 5), sharey=True)
day_types = ['Working Day', 'Weekend/Holiday']
titles1 = ['Working Day (Hari Kerja)', 'Weekend/Holiday (Akhir Pekan & Libur)']

for ax, day_type, title in zip(axes1, day_types, titles1):
    data_plot = hourly_avg[hourly_avg['workingday'] == day_type]
    if not data_plot.empty:
        sns.lineplot(data=data_plot, x='hr', y='registered', label='Registered', marker='o', linewidth=2.5, color='#1f77b4', ax=ax)
        sns.lineplot(data=data_plot, x='hr', y='casual', label='Casual', marker='s', linewidth=2.5, color='#ff7f0e', ax=ax)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_xlabel('Jam (00:00 - 23:00)')
    ax.set_ylabel('Rata-rata Penyewaan Sepeda')
    ax.set_xticks(range(0, 24, 2))
    ax.legend(title='Tipe Pengguna')

plt.tight_layout()
st.pyplot(fig1)

with st.expander("Lihat Insight Pertanyaan 1"):
    st.markdown("""
    - **Working Day:** Membentuk pola dua puncak (*bimodal*) yang didominasi pengguna *registered* pada jam berangkat kerja (08:00) dan jam pulang kerja (17:00–18:00).
    - **Weekend/Holiday:** Membentuk pola satu puncak (*unimodal*) di siang hingga sore hari (11:00–17:00) dengan lonjakan signifikan dari pengguna *casual* yang memuncak pada pukul 14:00.
    """)

st.divider()


st.subheader("2. Dampak Cuaca Buruk Terhadap Penyewaan Per Musim")

bad_weather = ['Light Snow/Rain', 'Heavy Rain/Snow']
weather_eda = filtered_hour[filtered_hour['weathersit'].isin(['Clear'] + bad_weather)].copy()
weather_eda['weather_group'] = weather_eda['weathersit'].apply(
    lambda x: 'Clear' if x == 'Clear' else 'Bad Weather'
)

if not weather_eda.empty:
    weather_pivot = (
        weather_eda.pivot_table(
            index='season',
            columns='weather_group',
            values='cnt',
            aggfunc='mean'
        )
        .reindex([s for s in all_seasons if s in selected_seasons])
    )

    if 'Clear' in weather_pivot.columns and 'Bad Weather' in weather_pivot.columns:
        weather_pivot['Drop (%)'] = (
            (weather_pivot['Clear'] - weather_pivot['Bad Weather']) / weather_pivot['Clear'] * 100
        )

        fig2, axes2 = plt.subplots(1, 2, figsize=(16, 5))

        plot_melted = weather_pivot[['Clear', 'Bad Weather']].reset_index().melt(
            id_vars='season', var_name='Kondisi Cuaca', value_name='Rata-rata Penyewaan'
        )
        sns.barplot(
            data=plot_melted, x='season', y='Rata-rata Penyewaan', hue='Kondisi Cuaca',
            palette={'Clear': '#2ca02c', 'Bad Weather': '#d62728'}, ax=axes2[0]
        )
        axes2[0].set_title('Rata-rata Penyewaan: Cerah vs. Cuaca Buruk', fontsize=12, fontweight='bold')
        axes2[0].set_xlabel('Musim')
        axes2[0].set_ylabel('Rata-rata Penyewaan (cnt)')

        drop_valid = weather_pivot['Drop (%)'].dropna()
        sns.barplot(
            x=drop_valid.index, y=drop_valid.values,
            palette=['#d62728' if v == drop_valid.max() else '#ff9896' for v in drop_valid.values],
            hue=drop_valid.index, legend=False, ax=axes2[1]
        )
        for i, val in enumerate(drop_valid.values):
            axes2[1].text(i, val + 1.5, f"-{val:.2f}%", ha='center', fontweight='bold')

        axes2[1].set_title('Persentase Penurunan Penyewaan Saat Cuaca Buruk', fontsize=12, fontweight='bold')
        axes2[1].set_xlabel('Musim')
        axes2[1].set_ylabel('Penurunan (%)')
        axes2[1].set_ylim(0, drop_valid.max() + 15)

        plt.tight_layout()
        st.pyplot(fig2)
    else:
        st.info("Data cuaca cerah atau cuaca buruk tidak lengkap pada filter yang dipilih.")
else:
    st.info("Tidak ada data yang sesuai dengan filter yang dipilih.")

with st.expander("Lihat Insight Pertanyaan 2"):
    st.markdown("""
    - Cuaca buruk menurunkan rata-rata penyewaan secara signifikan (lebih dari 50%) di seluruh musim dibandingkan cuaca cerah.
    - Penurunan paling tajam terjadi pada musim **Summer** dan **Spring**, sementara **Fall** menjadi musim dengan tingkat penyewaan paling tangguh.
    """)

st.divider()

st.subheader("3. Analisis Lanjutan: Clustering Klaster Waktu Operasional")

cluster_summary = (
    filtered_hour.groupby(['workingday', 'time_cluster'])
    .agg(
        total_rentals=('cnt', 'sum'),
        avg_rentals=('cnt', 'mean')
    )
    .reset_index()
)

if not cluster_summary.empty:
    cluster_summary['share_pct'] = (
        cluster_summary['total_rentals'] /
        cluster_summary.groupby('workingday')['total_rentals'].transform('sum') * 100
    ).round(2)

    fig3, axes3 = plt.subplots(1, 2, figsize=(16, 5.5))

    sns.barplot(
        data=cluster_summary, x='time_cluster', y='avg_rentals', hue='workingday',
        palette={'Working Day': '#1f77b4', 'Weekend/Holiday': '#ff7f0e'}, ax=axes3[0]
    )
    axes3[0].set_title('Rata-rata Penyewaan per Jam per Klaster Waktu', fontsize=12, fontweight='bold')
    axes3[0].set_xlabel('Klaster Waktu Operasional')
    axes3[0].set_ylabel('Rata-rata Penyewaan / Jam')
    axes3[0].tick_params(axis='x', rotation=15)
    axes3[0].legend(title='Tipe Hari')

    sns.barplot(
        data=cluster_summary, x='time_cluster', y='share_pct', hue='workingday',
        palette={'Working Day': '#1f77b4', 'Weekend/Holiday': '#ff7f0e'}, ax=axes3[1]
    )
    for container in axes3[1].containers:
        axes3[1].bar_label(container, fmt='%.1f%%', padding=3, fontsize=9)

    axes3[1].set_title('Kontribusi (%) Total Penyewaan per Klaster Waktu', fontsize=12, fontweight='bold')
    axes3[1].set_xlabel('Klaster Waktu Operasional')
    axes3[1].set_ylabel('Kontribusi (%)')
    axes3[1].set_ylim(0, cluster_summary['share_pct'].max() + 8)
    axes3[1].tick_params(axis='x', rotation=15)
    axes3[1].legend(title='Tipe Hari')

    plt.tight_layout()
    st.pyplot(fig3)

    with st.expander("Lihat Insight Analisis Lanjutan"):
        st.markdown("""
        - **Working Day (2012):** Sebanyak **60,30%** total penyewaan terkonsentrasi di klaster jam sibuk komuter, yaitu *Rush Hour Sore* (36,11%) dan *Rush Hour Pagi* (24,19%).
        - **Weekend/Holiday (2012):** Sebanyak **74,52%** total penyewaan terpusat pada rentang siang hingga sore hari (*Siang* 47,36% dan *Rush Hour Sore* 27,16%), sementara klaster *Dini Hari* (00–05) menjadi waktu paling sepi di kedua tipe hari.
        """)

st.caption("Copyright © 2026 - Capital Bikeshare Data Analysis Project")
import streamlit as st
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import pandas as pd
import folium
from streamlit_folium import folium_static
from datetime import datetime

st.set_page_config(page_title="Prakiraan Cuaca & Peta Kalsel", layout="wide")

st.title("📡 Global Forecast System Viewer (Realtime via NOMADS)")
st.header("Web Hasil Pembelajaran Pengelolaan Informasi Meteorologi")
st.markdown("### **_Editor : Ibnu Hidayat (M8TB_14.24.0005)_**")

tab1, tab2 = st.tabs(["📈 Prakiraan Cuaca", "🗺️ Peta Lokasi Kalsel"])

# ====================
# TAB 1: PRAKIRAAN CUACA
# ====================
with tab1:
    @st.cache_data
    def load_dataset(run_date, run_hour):
        base_url = f"https://nomads.ncep.noaa.gov/dods/gfs_0p25_1hr/gfs{run_date}/gfs_0p25_1hr_{run_hour}z"
        ds = xr.open_dataset(base_url)
        return ds

    st.sidebar.title("⚙️ Pengaturan Cuaca")
    today = datetime.utcnow()
    run_date = st.sidebar.date_input("Tanggal Run GFS (UTC)", today.date())
    run_hour = st.sidebar.selectbox("Jam Run GFS (UTC)", ["00", "06", "12", "18"])
    forecast_hour = st.sidebar.slider("Jam ke depan", 0, 240, 0, step=1)
    parameter = st.sidebar.selectbox("Parameter", [
        "Curah Hujan per jam (pratesfc)",
        "Suhu Permukaan (tmp2m)",
        "Angin Permukaan (ugrd10m & vgrd10m)",
        "Tekanan Permukaan Laut (prmslmsl)"
    ])

    if st.sidebar.button("🔎 Tampilkan Visualisasi"):
        try:
            with st.spinner("Mengunduh dan memuat data dari server GFS..."):
                ds = load_dataset(run_date.strftime("%Y%m%d"), run_hour)
            st.success("Dataset berhasil dimuat.")
        except Exception as e:
            st.error(f"Gagal memuat data: {e}")
            st.stop()

        is_contour = False
        is_vector = False

        if "pratesfc" in parameter:
            var = ds["pratesfc"][forecast_hour, :, :] * 3600
            label = "Curah Hujan (mm/jam)"
            cmap = "Blues"
            vmin, vmax = 0, 50
        elif "tmp2m" in parameter:
            var = ds["tmp2m"][forecast_hour, :, :] - 273.15
            label = "Suhu (°C)"
            cmap = "coolwarm"
            vmin, vmax = -5, 35
        elif "ugrd10m" in parameter:
            u = ds["ugrd10m"][forecast_hour, :, :]
            v = ds["vgrd10m"][forecast_hour, :, :]
            speed = (u**2 + v**2)**0.5 * 1.94384
            var = speed
            label = "Kecepatan Angin (knot)"
            cmap = plt.cm.get_cmap("RdYlGn_r", 10)
            is_vector = True
            vmin, vmax = 0, 40
        elif "prmsl" in parameter:
            var = ds["prmslmsl"][forecast_hour, :, :] / 100
            label = "Tekanan Permukaan Laut (hPa)"
            cmap = "cool"
            is_contour = True
            vmin, vmax = None, None
        else:
            st.warning("Parameter tidak dikenali.")
            st.stop()

        # Filter Kalimantan Selatan
        var = var.sel(lat=slice(-4, -1), lon=slice(114, 116.5))
        if is_vector:
            u = u.sel(lat=slice(-4, -1), lon=slice(114, 116.5))
            v = v.sel(lat=slice(-4, -1), lon=slice(114, 116.5))

        fig = plt.figure(figsize=(10, 6))
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.set_extent([114, 116.5, -4, -1], crs=ccrs.PlateCarree())

        valid_time = ds.time[forecast_hour].values
        valid_dt = pd.to_datetime(str(valid_time))
        valid_str = valid_dt.strftime("%HUTC %a %d %b %Y")
        tstr = f"t+{forecast_hour:03d}"

        ax.set_title(f"{label} Valid {valid_str}", loc="left", fontsize=10, fontweight="bold")
        ax.set_title(f"GFS {tstr}", loc="right", fontsize=10, fontweight="bold")

        if is_contour:
            cs = ax.contour(var.lon, var.lat, var.values, levels=15, colors='black', linewidths=0.8, transform=ccrs.PlateCarree())
            ax.clabel(cs, fmt="%d", colors='black', fontsize=8)
        else:
            im = ax.pcolormesh(var.lon, var.lat, var.values,
                               cmap=cmap, vmin=vmin, vmax=vmax,
                               transform=ccrs.PlateCarree())
            cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.02)
            cbar.set_label(label)
            if is_vector:
                ax.quiver(var.lon[::5], var.lat[::5],
                          u.values[::5, ::5], v.values[::5, ::5],
                          transform=ccrs.PlateCarree(), scale=700, width=0.002, color='black')

        ax.coastlines(resolution='10m', linewidth=0.8)
        ax.add_feature(cfeature.BORDERS, linestyle=':')
        ax.add_feature(cfeature.LAND, facecolor='lightgray')
        st.pyplot(fig)

# ====================
# TAB 2: PETA LOKASI
# ====================
with tab2:
    st.markdown("### 🗺️ **Peta Lokasi Kabupaten/Kota di Kalimantan Selatan**")

    # Koordinat ibu kota kabupaten/kota Kalsel
    kabupaten_data = [
        {"nama": "Banjarmasin", "lat": -3.319, "lon": 114.590},
        {"nama": "Banjarbaru", "lat": -3.442, "lon": 114.844},
        {"nama": "Kab. Banjar", "lat": -3.412, "lon": 114.841},
        {"nama": "Kab. Barito Kuala", "lat": -2.985, "lon": 114.736},
        {"nama": "Kab. Tapin", "lat": -2.977, "lon": 115.030},
        {"nama": "Kab. Hulu Sungai Selatan", "lat": -2.765, "lon": 115.217},
        {"nama": "Kab. Hulu Sungai Tengah", "lat": -2.583, "lon": 115.517},
        {"nama": "Kab. Hulu Sungai Utara", "lat": -2.423, "lon": 115.003},
        {"nama": "Kab. Tabalong", "lat": -2.083, "lon": 115.383},
        {"nama": "Kab. Tanah Laut", "lat": -3.800, "lon": 114.850},
        {"nama": "Kab. Tanah Bumbu", "lat": -3.470, "lon": 115.520},
        {"nama": "Kab. Kotabaru", "lat": -3.300, "lon": 116.000},
    ]

    # Buat peta interaktif
    peta = folium.Map(location=[-3.0, 115.2], zoom_start=7)

    for kab in kabupaten_data:
        folium.Marker(
            location=[kab["lat"], kab["lon"]],
            popup=kab["nama"],
            tooltip=kab["nama"],
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(peta)

    folium_static(peta)

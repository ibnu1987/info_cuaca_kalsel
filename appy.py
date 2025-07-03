import streamlit as st
import xarray as xr
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import pandas as pd
from datetime import datetime

matplotlib.use("Agg")  # Untuk kompatibilitas Streamlit

# Konfigurasi halaman
st.set_page_config(page_title="Prakiraan Cuaca Kalimantan Selatan", layout="wide")
st.title("📡 GFS Viewer - Kalimantan Selatan")
st.header("Pengelolaan Informasi Meteorologi")
st.markdown("### **_Editor: Ibnu Hidayat (M8TB_14.24.0005)_**")

@st.cache_data
def load_dataset(run_date, run_hour):
    url = f"https://nomads.ncep.noaa.gov/dods/gfs_0p25_1hr/gfs{run_date}/gfs_0p25_1hr_{run_hour}z"
    ds = xr.open_dataset(url)
    return ds

# Sidebar
st.sidebar.title("⚙️ Pengaturan")
today = datetime.utcnow()
run_date = st.sidebar.date_input("Tanggal Run (UTC)", today.date())
run_hour = st.sidebar.selectbox("Jam Run (UTC)", ["00", "06", "12", "18"])
forecast_hour = st.sidebar.slider("Prakiraan Jam ke-", 0, 240, 0, 1)
parameter_key = st.sidebar.selectbox("Parameter", [
    "pratesfc", "tmp2m", "ugrd10m_vgrd10m", "prmslmsl"
], format_func=lambda x: {
    "pratesfc": "Curah Hujan (mm/jam)",
    "tmp2m": "Suhu (°C)",
    "ugrd10m_vgrd10m": "Angin 10m (knot)",
    "prmslmsl": "Tekanan Permukaan Laut (hPa)"
}[x])

if st.sidebar.button("🔎 Tampilkan Visualisasi"):
    try:
        with st.spinner("📥 Mengunduh data dari server GFS..."):
            ds = load_dataset(run_date.strftime("%Y%m%d"), run_hour)
        st.success("✅ Data berhasil dimuat")
    except Exception as e:
        st.error(f"❌ Gagal memuat data: {e}")
        st.stop()

    # Wilayah Kalimantan Selatan
    lat_min, lat_max = -4.5, -1.5
    lon_min, lon_max = 114.5, 116.5

    is_vector = False
    is_contour = False

    # Parameter
    if parameter_key == "pratesfc":
        var = ds["pratesfc"][forecast_hour, :, :] * 3600
        label = "Curah Hujan (mm/jam)"
        cmap = "Blues"
        vmin, vmax = 0, 50
    elif parameter_key == "tmp2m":
        var = ds["tmp2m"][forecast_hour, :, :] - 273.15
        label = "Suhu (°C)"
        cmap = "coolwarm"
        vmin, vmax = -5, 35
    elif parameter_key == "ugrd10m_vgrd10m":
        u = ds["ugrd10m"][forecast_hour, :, :]
        v = ds["vgrd10m"][forecast_hour, :, :]
        speed = (u**2 + v**2)**0.5 * 1.94384
        var = speed
        label = "Kecepatan Angin (knot)"
        cmap = "viridis"
        vmin, vmax = 0, 40
        is_vector = True
    elif parameter_key == "prmslmsl":
        var = ds["prmslmsl"][forecast_hour, :, :] / 100
        label = "Tekanan Permukaan Laut (hPa)"
        cmap = "cool"
        is_contour = True
        vmin, vmax = None, None
    else:
        st.warning("Parameter tidak dikenali.")
        st.stop()

    # Potong wilayah dan pastikan urutan dimensi lat-lon
    var = var.sel(lat=slice(lat_max, lat_min), lon=slice(lon_min, lon_max)).transpose("lat", "lon")
    if is_vector:
        u = u.sel(lat=slice(lat_max, lat_min), lon=slice(lon_min, lon_max)).transpose("lat", "lon")
        v = v.sel(lat=slice(lat_max, lat_min), lon=slice(lon_min, lon_max)).transpose("lat", "lon")

    # Meshgrid
    lon2d, lat2d = np.meshgrid(var.lon.values, var.lat.values)

    # Plot
    fig = plt.figure(figsize=(10, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([lon_min, lon_max, lat_min, lat_max])

    time_str = pd.to_datetime(ds.time[forecast_hour].values).strftime("%HUTC %a %d %b %Y")
    ax.set_title(f"{label} | Valid {time_str}", loc="left", fontsize=10, weight="bold")
    ax.set_title(f"GFS t+{forecast_hour:03d}", loc="right", fontsize=10, weight="bold")

    if is_contour:
        cs = ax.contour(lon2d, lat2d, var.values, levels=15, colors='black', linewidths=0.7)
        ax.clabel(cs, fmt="%d", fontsize=8)
    else:
        im = ax.pcolormesh(lon2d, lat2d, var.values, cmap=cmap,
                           vmin=vmin, vmax=vmax, shading="auto", transform=ccrs.PlateCarree())
        cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.02)
        cbar.set_label(label)

        if is_vector:
            step = 5
            ax.quiver(lon2d[::step, ::step], lat2d[::step, ::step],
                      u.values[::step, ::step], v.values[::step, ::step],
                      transform=ccrs.PlateCarree(), color='black', scale=700)

    ax.coastlines(resolution='10m', linewidth=0.7)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAND, facecolor='lightgray')

    # Titik Kabupaten/Kota
    locations = {
        "Banjarmasin": (-3.32, 114.59),
        "Banjarbaru": (-3.44, 114.84),
        "Kab. Banjar": (-3.45, 115.01),
        "Kab. Tapin": (-2.94, 115.04),
        "Kab. HSS": (-2.77, 115.22),
        "Kab. HST": (-2.57, 115.52),
        "Kab. HSU": (-2.43, 115.14),
        "Kab. Balangan": (-2.34, 115.61),
        "Kab. Tabalong": (-1.86, 115.51),
        "Kab. Tala": (-3.80, 114.78),
        "Kab. Tanbu": (-3.45, 115.52),
        "Kab. Kotabaru": (-3.29, 116.23)
    }
    for name, (lat, lon) in locations.items():
        ax.plot(lon, lat, 'ro', markersize=3, transform=ccrs.PlateCarree())
        ax.text(lon + 0.05, lat + 0.05, name, fontsize=6, transform=ccrs.PlateCarree())

    st.pyplot(fig)

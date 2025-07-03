import streamlit as st
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Prakiraan Cuaca Wilayah Indonesia", layout="wide")

st.title("📡 Global Forecast System Viewer (Realtime via NOMADS)")
st.header("Web Hasil Pembelajaran Pengelolaan Informasi Meteorologi")
st.markdown("### **_Editor : Ibnu Hidayat (M8TB_14.24.0005)_**")

@st.cache_data
def load_dataset(run_date, run_hour):
    url = f"https://nomads.ncep.noaa.gov/dods/gfs_0p25_1hr/gfs{run_date}/gfs_0p25_1hr_{run_hour}z"
    ds = xr.open_dataset(url)
    return ds

# Sidebar
st.sidebar.title("⚙️ Pengaturan")
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

    # Parameter
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

    # Filter wilayah Kalimantan Selatan
    lat_min, lat_max = -4.5, -1.0
    lon_min, lon_max = 114.0, 116.5

    var = var.sel(lat=slice(lat_max, lat_min), lon=slice(lon_min, lon_max)).transpose("lat", "lon")
    lon2d, lat2d = np.meshgrid(var.lon.values, var.lat.values)

    if is_vector:
        u = u.sel(lat=slice(lat_max, lat_min), lon=slice(lon_min, lon_max)).transpose("lat", "lon")
        v = v.sel(lat=slice(lat_max, lat_min), lon=slice(lon_min, lon_max)).transpose("lat", "lon")

    # Plot
    fig = plt.figure(figsize=(10, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([lon_min, lon_max, lat_min, lat_max])

    # Validasi waktu
    valid_time = ds.time[forecast_hour].values
    valid_dt = pd.to_datetime(str(valid_time))
    valid_str = valid_dt.strftime("%HUTC %a %d %b %Y")
    tstr = f"t+{forecast_hour:03d}"

    ax.set_title(f"{label} Valid {valid_str}", loc="left", fontsize=10, fontweight="bold")
    ax.set_title(f"GFS {tstr}", loc="right", fontsize=10, fontweight="bold")

    if is_contour:
        cs = ax.contour(lon2d, lat2d, var.values, levels=15, colors='black', linewidths=0.8)
        ax.clabel(cs, fmt="%d", fontsize=8)
    else:
        im = ax.pcolormesh(lon2d, lat2d, var.values,
                           cmap=cmap, vmin=vmin, vmax=vmax,
                           transform=ccrs.PlateCarree(), shading="auto")
        cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.02)
        cbar.set_label(label)
        if is_vector:
            ax.quiver(lon2d[::5, ::5], lat2d[::5, ::5],
                      u.values[::5, ::5], v.values[::5, ::5],
                      transform=ccrs.PlateCarree(), scale=700, width=0.002, color='black')

    # Tambah fitur peta
    ax.coastlines(resolution='10m', linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAND, facecolor='lightgray')

    # Titik lokasi kabupaten/kota Kalimantan Selatan
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

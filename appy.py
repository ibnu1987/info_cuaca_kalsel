import streamlit as st
import xarray as xr
import matplotlib
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import pandas as pd
from datetime import datetime

matplotlib.use("Agg")  # Backend non-GUI untuk Streamlit

# Konfigurasi halaman
st.set_page_config(page_title="Prakiraan Cuaca Kalimantan Selatan", layout="wide")
st.title("📡 Global Forecast System Viewer (Wilayah Kalimantan Selatan)")
st.header("Web Hasil Pembelajaran Pengelolaan Informasi Meteorologi")
st.markdown("### **_Editor : Ibnu Hidayat (M8TB_14.24.0005)_**")

# Fungsi cache untuk load dataset
@st.cache_data
def load_dataset(run_date, run_hour):
    base_url = f"https://nomads.ncep.noaa.gov/dods/gfs_0p25_1hr/gfs{run_date}/gfs_0p25_1hr_{run_hour}z"
    ds = xr.open_dataset(base_url)
    return ds

# Sidebar pengaturan
st.sidebar.title("⚙️ Pengaturan")
today = datetime.utcnow()
run_date = st.sidebar.date_input("Tanggal Run GFS (UTC)", today.date())
run_hour = st.sidebar.selectbox("Jam Run GFS (UTC)", ["00", "06", "12", "18"])
forecast_hour = st.sidebar.slider("Jam ke depan", 0, 240, 0, step=1)
param_options = {
    "pratesfc": "Curah Hujan per jam (pratesfc)",
    "tmp2m": "Suhu Permukaan (tmp2m)",
    "ugrd10m_vgrd10m": "Angin Permukaan (ugrd10m & vgrd10m)",
    "prmslmsl": "Tekanan Permukaan Laut (prmslmsl)"
}
parameter_key = st.sidebar.selectbox("Parameter", options=list(param_options.keys()),
                                     format_func=lambda x: param_options[x])

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

    # Subsetting Kalimantan Selatan
    lat_min, lat_max = -4.5, -1.5
    lon_min, lon_max = 114.5, 116.5

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
        speed = (u**2 + v**2)**0.5 * 1.94384  # konversi ke knot
        var = speed
        label = "Kecepatan Angin (knot)"
        cmap = plt.cm.get_cmap("RdYlGn_r", 10)
        is_vector = True
        vmin, vmax = 0, 40
    elif parameter_key == "prmslmsl":
        var = ds["prmslmsl"][forecast_hour, :, :] / 100
        label = "Tekanan Permukaan Laut (hPa)"
        cmap = "cool"
        is_contour = True
        vmin, vmax = None, None
    else:
        st.warning("Parameter tidak dikenali.")
        st.stop()

    # Subset koordinat wilayah
    var = var.sel(lat=slice(lat_max, lat_min), lon=slice(lon_min, lon_max))
    if is_vector:
        u = u.sel(lat=slice(lat_max, lat_min), lon=slice(lon_min, lon_max))
        v = v.sel(lat=slice(lat_max, lat_min), lon=slice(lon_min, lon_max))

    # Plot visualisasi
    fig = plt.figure(figsize=(10, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # Format waktu
    valid_time = ds.time[forecast_hour].values
    valid_dt = pd.to_datetime(valid_time)
    valid_str = valid_dt.strftime("%HUTC %a %d %b %Y")
    tstr = f"t+{forecast_hour:03d}"

    ax.set_title(f"{label} Valid {valid_str}", loc="left", fontsize=10, fontweight="bold")
    ax.set_title(f"GFS {tstr}", loc="right", fontsize=10, fontweight="bold")

    if is_contour:
        cs = ax.contour(var.lon, var.lat, var.values, levels=15, colors='black', linewidths=0.8, transform=ccrs.PlateCarree())
        ax.clabel(cs, fmt="%d", colors='black', fontsize=8)
    else:
        im = ax.pcolormesh(var.lon, var.lat, var.values, cmap=cmap, vmin=vmin, vmax=vmax, transform=ccrs.PlateCarree())
        cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.02)
        cbar.set_label(label)
        if is_vector:
            step = 5
            ax.quiver(var.lon[::step], var.lat[::step], u.values[::step, ::step], v.values[::step, ::step],
                      transform=ccrs.PlateCarree(), scale=700, width=0.002, color='black')

    # Tambah fitur peta
    ax.coastlines(resolution='10m', linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAND, facecolor='lightgray')

    # Titik kabupaten/kota Kalimantan Selatan
    locations = {
        "Banjarmasin": (-3.3204, 114.5908),
        "Banjarbaru": (-3.442, 114.844),
        "Kab. Banjar": (-3.453, 115.017),
        "Kab. Barito Kuala": (-2.916, 114.716),
        "Kab. Tapin": (-2.944, 115.045),
        "Kab. Hulu Sungai Selatan": (-2.773, 115.225),
        "Kab. Hulu Sungai Tengah": (-2.578, 115.520),
        "Kab. Hulu Sungai Utara": (-2.432, 115.147),
        "Kab. Balangan": (-2.343, 115.615),
        "Kab. Tabalong": (-1.864, 115.516),
        "Kab. Tanah Laut": (-3.804, 114.781),
        "Kab. Tanah Bumbu": (-3.458, 115.525),
        "Kab. Kotabaru": (-3.295, 116.230)
    }

    for name, (lat, lon) in locations.items():
        ax.plot(lon, lat, marker='o', color='red', markersize=3, transform=ccrs.PlateCarree())
        ax.text(lon + 0.05, lat + 0.05, name, fontsize=6, transform=ccrs.PlateCarree())

    st.pyplot(fig)
    st.markdown("---")
    st.markdown("*Data dari [NCEP/NOMADS](https://nomads.ncep.noaa.gov/), GFS 0.25° 1-hourly forecast*")

import streamlit as st
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import pandas as pd
from datetime import datetime
from io import BytesIO
import urllib.request
from contextlib import closing

# Konfigurasi halaman
st.set_page_config(page_title="Prakiraan Cuaca Wilayah Indonesia", layout="wide")

# Judul aplikasi
st.title("📡 Global Forecast System Viewer (Realtime via NOMADS)")
st.header("Web Hasil Pembelajaran Pengelolaan Informasi Meteorologi")
st.markdown("### **_Editor : Ibnu Hidayat (M8TB_14.24.0005)_**")

# Fungsi memeriksa ketersediaan dataset
def check_url(url):
    try:
        with closing(urllib.request.urlopen(url, timeout=5)) as conn:
            return True
    except:
        return False

# Fungsi untuk memuat dataset
@st.cache_data
def load_dataset(run_date, run_hour):
    base_url = f"https://nomads.ncep.noaa.gov/dods/gfs_0p25_1hr/gfs{run_date}/gfs_0p25_1hr_{run_hour}z"
    ds = xr.open_dataset(base_url)
    return ds

# Sidebar
st.sidebar.title("⚙️ Pengaturan")
today = datetime.utcnow()
run_date = st.sidebar.date_input("Tanggal Run GFS (UTC)", today.date())
run_hour = st.sidebar.selectbox("Jam Run GFS (UTC)", ["00", "06", "12", "18"])
forecast_hour = st.sidebar.slider("Jam ke depan (t+)", 0, 240, 0, step=1)
parameter = st.sidebar.selectbox("Parameter", [
    "Curah Hujan per jam (pratesfc)",
    "Suhu Permukaan (tmp2m)",
    "Angin Permukaan (ugrd10m & vgrd10m)",
    "Tekanan Permukaan Laut (prmslmsl)"
])

# Tombol tampilkan
if st.sidebar.button("🔎 Tampilkan Visualisasi"):
    base_url = f"https://nomads.ncep.noaa.gov/dods/gfs_0p25_1hr/gfs{run_date.strftime('%Y%m%d')}/gfs_0p25_1hr_{run_hour}z"
    if not check_url(base_url):
        st.error("Dataset belum tersedia atau tidak dapat diakses. Coba jam/tanggal berbeda.")
        st.stop()

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
        cmap = "YlGnBu"
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
    elif "prmslmsl" in parameter:
        var = ds["prmslmsl"][forecast_hour, :, :] / 100
        label = "Tekanan Permukaan Laut (hPa)"
        cmap = "cool"
        is_contour = True
        vmin, vmax = None, None
    else:
        st.warning("Parameter tidak dikenali.")
        st.stop()

    # Batas wilayah Kalimantan Selatan
    lat_min, lat_max = -4.5, -1
    lon_min, lon_max = 114, 117
    var = var.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))
    if is_vector:
        u = u.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))
        v = v.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

    # Buat figure
    fig, ax = plt.subplots(figsize=(10, 6), subplot_kw={'projection': ccrs.PlateCarree()})
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # Judul peta
    valid_time = ds.time[forecast_hour].values
    valid_dt = pd.to_datetime(str(valid_time))
    valid_str = valid_dt.strftime("%HUTC %a %d %b %Y")
    ax.set_title(f"{label} Valid {valid_str} — GFS t+{forecast_hour:03d}", fontsize=12, weight='bold')

    # Plot data
    if is_contour:
        cs = ax.contour(var.lon, var.lat, var.values, levels=15, colors='black', linewidths=0.8)
        ax.clabel(cs, fmt="%d", fontsize=8)
    else:
        im = ax.pcolormesh(var.lon, var.lat, var.values, cmap=cmap, vmin=vmin, vmax=vmax)
        cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.02)
        cbar.set_label(label)

        if is_vector:
            ax.quiver(var.lon[::5], var.lat[::5], u.values[::5, ::5], v.values[::5, ::5],
                      scale=700, width=0.002, color='black')

    # Fitur peta
    ax.coastlines(resolution='10m')
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAND, facecolor='lightgray')

    # Titik koordinat kabupaten/kota
    kota_lokasi = pd.DataFrame({
        "kota": [
            "Kota Banjarmasin", "Kota Banjarbaru", "Kab.Banjar", "Kab.Barito Kuala",
            "Kab.HSS", "Kab.HST", "Kab.HSU",
            "Kab.Kotabaru", "Kab.Tanah Bumbu", "Kab.Tanah Laut", "Kab.Tabalong",
            "Kab.Tapin", "Kab.Balangan"
        ],
        "lat": [-3.319, -3.442, -3.410, -2.988, -2.716, -2.583, -2.416,
                -3.000, -3.437, -3.804, -2.130, -2.918, -2.590],
        "lon": [114.590, 114.843, 114.904, 114.733, 115.176, 115.385, 115.150,
                116.000, 115.825, 114.761, 115.435, 115.149, 115.518]
    })

    for _, row in kota_lokasi.iterrows():
        ax.plot(row['lon'], row['lat'], marker='o', color='red', markersize=4, transform=ccrs.PlateCarree())
        ax.text(row['lon'] + 0.02, row['lat'] + 0.02, row['kota'], fontsize=6,
                transform=ccrs.PlateCarree(), ha='left', va='bottom')

    # Tampilkan ke Streamlit
    st.pyplot(fig)

    # Unduh sebagai PNG
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    st.download_button("📥 Unduh Gambar", data=buf.getvalue(), file_name="cuaca_kalsel_gfs.png", mime="image/png")

    # Sumber data
    st.caption("Sumber data: NOAA GFS via NOMADS (https://nomads.ncep.noaa.gov)")

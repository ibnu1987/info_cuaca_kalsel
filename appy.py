import streamlit as st
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import pandas as pd
from datetime import datetime

# Konfigurasi halaman
st.set_page_config(page_title="Prakiraan Cuaca Wilayah Indonesia", layout="wide")

# Judul aplikasi
st.title("📡 Global Forecast System Viewer (Realtime via NOMADS)")
st.header("Web Hasil Pembelajaran Pengelolaan Informasi Meteorologi")
st.markdown("### **_Editor : Ibnu Hidayat (M8TB_14.24.0005)_**")

# Fungsi untuk memuat dataset
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
parameter = st.sidebar.selectbox("Parameter", [
    "Curah Hujan per jam (pratesfc)",
    "Suhu Permukaan (tmp2m)",
    "Angin Permukaan (ugrd10m & vgrd10m)",
    "Tekanan Permukaan Laut (prmslmsl)"
])

# Tombol visualisasi
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

    # Pilih parameter
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

    # Area peta: Kalimantan Selatan (lat -4.5 s.d -1, lon 114 s.d 117)
    lat_min, lat_max = -4.5, -1
    lon_min, lon_max = 114, 117
    var = var.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))
    if is_vector:
        u = u.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))
        v = v.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

    # Ukuran plot
    fig_width, fig_height = 10, 6
    fig = plt.figure(figsize=(fig_width, fig_height))
    fig.subplots_adjust(top=0.9)
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # Waktu validasi
    valid_time = ds.time[forecast_hour].values
    valid_dt = pd.to_datetime(str(valid_time))
    valid_str = valid_dt.strftime("%HUTC %a %d %b %Y")
    tstr = f"t+{forecast_hour:03d}"

    # Judul peta
    font_size = max(10, int(fig_width * 1.2))
    judul_peta = f"{label} Valid {valid_str} — GFS {tstr}"
    ax.set_title(judul_peta, fontsize=font_size, fontweight="bold", loc="center", pad=10)

    # Plot data utama
    if is_contour:
        cs = ax.contour(var.lon, var.lat, var.values, levels=15, colors='black',
                        linewidths=0.8, transform=ccrs.PlateCarree())
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

    # Tambahkan fitur peta
    ax.coastlines(resolution='10m', linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAND, facecolor='lightgray')

    # Tambahkan titik lokasi kabupaten/kota
    kota_lokasi = pd.DataFrame({
        "kota": [
            "Banjarmasin", "Banjarbaru", "Martapura", "Pelaihari", "Kandangan",
            "Barabai", "Tanjung", "Paringin", "Marabahan", "Rantau"
        ],
        "lat": [-3.319, -3.442, -3.410, -3.804, -2.716,
                -2.583, -2.130, -2.590, -2.988, -2.918],
        "lon": [114.590, 114.843, 114.904, 114.761, 115.176,
                115.385, 115.435, 115.518, 114.733, 115.149]
    })

    for _, row in kota_lokasi.iterrows():
        ax.plot(row['lon'], row['lat'], marker='o', color='red', markersize=4,
                transform=ccrs.PlateCarree())
        ax.text(row['lon'] + 0.02, row['lat'] + 0.02, row['kota'], fontsize=7,
                transform=ccrs.PlateCarree(), ha='left', va='bottom', color='black')

    # Tampilkan di Streamlit
    st.pyplot(fig)

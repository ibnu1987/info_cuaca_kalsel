import streamlit as st
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import pandas as pd
from datetime import datetime, timedelta
import io
import imageio  # ✅ gunakan imageio biasa

# Konfigurasi halaman
st.set_page_config(page_title="Prakiraan Cuaca Wilayah Indonesia", layout="wide")

st.title("📡 Global Forecast System Viewer (Realtime via NOMADS)")
st.header("Web Hasil Pembelajaran Pengelolaan Informasi Meteorologi")
st.markdown("### **_Editor : Ibnu Hidayat (M8TB_14.24.0005)_**")

@st.cache_data
def load_dataset(run_date, run_hour):
    base_url = f"https://nomads.ncep.noaa.gov/dods/gfs_0p25_1hr/gfs{run_date}/gfs_0p25_1hr_{run_hour}z"
    ds = xr.open_dataset(base_url)
    return ds

st.sidebar.title("⚙️ Pengaturan")
utc_now = datetime.utcnow()
max_date = utc_now.date()
min_date = max_date - timedelta(days=5)

run_date = st.sidebar.date_input("Tanggal Run GFS (UTC)", value=max_date, min_value=min_date, max_value=max_date)
run_hour = st.sidebar.selectbox("Jam Run GFS (UTC)", ["00", "06", "12", "18"])
forecast_hour = st.sidebar.slider("Jam ke depan", 0, 240, 0, step=1)
parameter = st.sidebar.selectbox("Parameter", [
    "Curah Hujan per jam (pratesfc)",
    "Suhu Permukaan (tmp2m)",
    "Angin Permukaan (ugrd10m & vgrd10m)",
    "Tekanan Permukaan Laut (prmslmsl)"
])

def plot_kabupaten(ax):
    kota_lokasi = pd.DataFrame({
        "kota": [
            "Banjarmasin", "Banjarbaru", "Kab. Banjar", "Kab. Barito Kuala",
            "Kab. Hulu Sungai Selatan", "Kab. Hulu Sungai Tengah", "Kab. Hulu Sungai Utara",
            "Kab. Kotabaru", "Kab. Tanah Bumbu", "Kab. Tanah Laut", "Kab. Tabalong",
            "Kab. Tapin", "Kab. Balangan"
        ],
        "lat": [-3.319, -3.442, -3.410, -2.988, -2.716, -2.583, -2.416,
                -3.000, -3.437, -3.804, -2.130, -2.918, -2.590],
        "lon": [114.590, 114.843, 114.904, 114.733, 115.176, 115.385, 115.150,
                116.000, 115.825, 114.761, 115.435, 115.149, 115.518]
    })
    for _, row in kota_lokasi.iterrows():
        ax.plot(row['lon'], row['lat'], marker='o', color='red', markersize=4, transform=ccrs.PlateCarree())
        ax.text(row['lon'] + 0.02, row['lat'] + 0.02, row['kota'], fontsize=7,
                transform=ccrs.PlateCarree(), ha='left', va='bottom')

if st.sidebar.button("🔎 Tampilkan Visualisasi"):
    try:
        with st.spinner("Mengunduh dan memuat data dari server GFS..."):
            ds = load_dataset(run_date.strftime("%Y%m%d"), run_hour)
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        st.stop()

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
        var = ((u**2 + v**2)**0.5) * 1.94384
        label = "Kecepatan Angin (knot)"
        cmap = "RdYlGn_r"
        is_vector = True
        vmin, vmax = 0, 40
    elif "prmsl" in parameter:
        var = ds["prmslmsl"][forecast_hour, :, :] / 100
        label = "Tekanan Permukaan Laut (hPa)"
        cmap = "cool"
        vmin, vmax = 980, 1020

    lat_min, lat_max = -4.5, -1
    lon_min, lon_max = 114, 117
    var = var.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))
    if is_vector:
        u = u.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))
        v = v.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

    fig = plt.figure(figsize=(10, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([lon_min, lon_max, lat_min, lat_max])
    valid_time = pd.to_datetime(str(ds.time[forecast_hour].values))
    ax.set_title(f"{label} Valid {valid_time:%HUTC %a %d %b %Y}", fontsize=12, pad=10)

    im = ax.pcolormesh(var.lon, var.lat, var.values, cmap=cmap, vmin=vmin, vmax=vmax, transform=ccrs.PlateCarree())
    if is_vector:
        ax.quiver(var.lon[::5], var.lat[::5], u.values[::5, ::5], v.values[::5, ::5],
                  transform=ccrs.PlateCarree(), scale=700, width=0.002, color='black')

    ax.coastlines(resolution='10m', linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAND, facecolor='lightgray')
    plot_kabupaten(ax)
    cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.02)
    cbar.set_label(label)
    st.pyplot(fig)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches='tight')
    buf.seek(0)
    filename = f"gfs_{parameter.replace(' ', '_')}_{forecast_hour:03d}.png"
    st.download_button("📥 Unduh Gambar Peta", data=buf, file_name=filename, mime="image/png")

if st.sidebar.button("🎞️ Buat Animasi"):
    try:
        with st.spinner("Membuat animasi GIF..."):
            ds = load_dataset(run_date.strftime("%Y%m%d"), run_hour)
            frames = []
            for fh in range(0, 25, 3):
                if "pratesfc" in parameter:
                    var = ds["pratesfc"][fh, :, :] * 3600
                    label = "Curah Hujan (mm/jam)"
                    cmap = "Blues"
                    vmin, vmax = 0, 50
                elif "tmp2m" in parameter:
                    var = ds["tmp2m"][fh, :, :] - 273.15
                    label = "Suhu (°C)"
                    cmap = "coolwarm"
                    vmin, vmax = -5, 35
                elif "ugrd10m" in parameter:
                    u = ds["ugrd10m"][fh, :, :]
                    v = ds["vgrd10m"][fh, :, :]
                    var = ((u**2 + v**2)**0.5) * 1.94384
                    label = "Kecepatan Angin (knot)"
                    cmap = "RdYlGn_r"
                    vmin, vmax = 0, 40
                elif "prmsl" in parameter:
                    var = ds["prmslmsl"][fh, :, :] / 100
                    label = "Tekanan Permukaan Laut (hPa)"
                    cmap = "cool"
                    vmin, vmax = 980, 1020

                lat_min, lat_max = -4.5, -1
                lon_min, lon_max = 114, 117
                var = var.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))
                if "ugrd10m" in parameter:
                    u = u.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))
                    v = v.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

                fig = plt.figure(figsize=(7, 4.5))
                ax = plt.axes(projection=ccrs.PlateCarree())
                ax.set_extent([lon_min, lon_max, lat_min, lat_max])
                time_str = pd.to_datetime(str(ds.time[fh].values)).strftime("%d %b %HUTC")
                ax.set_title(f"{label} • Valid {time_str} • t+{fh:03d}", fontsize=10, pad=6)

                im = ax.pcolormesh(var.lon, var.lat, var.values, cmap=cmap, vmin=vmin, vmax=vmax,
                                   transform=ccrs.PlateCarree())
                if "ugrd10m" in parameter:
                    ax.quiver(var.lon[::5], var.lat[::5], u.values[::5, ::5], v.values[::5, ::5],
                              transform=ccrs.PlateCarree(), scale=700, width=0.002, color='black')

                ax.coastlines('10m', linewidth=0.6)
                ax.add_feature(cfeature.BORDERS, linestyle=':', linewidth=0.4)
                ax.add_feature(cfeature.LAND, facecolor='lightgray')
                plot_kabupaten(ax)
                plt.colorbar(im, ax=ax, orientation='vertical', pad=0.02).set_label(label, fontsize=8)

                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=100)
                buf.seek(0)
                frames.append(imageio.imread(buf))
                plt.close(fig)

            gif_buffer = io.BytesIO()
            imageio.mimsave(gif_buffer, frames, format='GIF', duration=0.8)
            gif_buffer.seek(0)

            st.image(gif_buffer, caption="Animasi Prakiraan GFS", use_column_width=True)
            st.download_button("📥 Unduh Animasi GIF", data=gif_buffer,
                               file_name=f"animasi_gfs_{parameter.replace(' ', '_')}.gif",
                               mime="image/gif")
    except Exception as e:
        st.error(f"Gagal membuat animasi: {e}")

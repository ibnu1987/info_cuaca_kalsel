import imageio.v2 as imageio  # Tambahkan di bagian import atas

if st.sidebar.button("🎞️ Buat Animasi"):
    try:
        with st.spinner("Mengunduh data dan membuat animasi..."):
            ds = load_dataset(run_date.strftime("%Y%m%d"), run_hour)

            forecast_times = list(range(0, 25, 3))  # t+0 sampai t+24 setiap 3 jam
            frames = []

            for fh in forecast_times:
                # Ambil data sesuai parameter
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
                    speed = (u**2 + v**2)**0.5 * 1.94384
                    var = speed
                    label = "Kecepatan Angin (knot)"
                    cmap = "RdYlGn_r"
                    vmin, vmax = 0, 40
                elif "prmsl" in parameter:
                    var = ds["prmslmsl"][fh, :, :] / 100
                    label = "Tekanan Permukaan Laut (hPa)"
                    cmap = "cool"
                    vmin, vmax = 980, 1020
                else:
                    st.warning("Parameter tidak dikenali.")
                    st.stop()

                lat_min, lat_max = -4.5, -1
                lon_min, lon_max = 114, 117
                var = var.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))
                if "ugrd10m" in parameter:
                    u = u.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))
                    v = v.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

                fig = plt.figure(figsize=(7, 4.5))
                ax = plt.axes(projection=ccrs.PlateCarree())
                ax.set_extent([lon_min, lon_max, lat_min, lat_max])
                valid_time = pd.to_datetime(str(ds.time[fh].values))
                tstr = f"t+{fh:03d}"
                ax.set_title(f"{label} • Valid {valid_time:%d %b %HUTC} • GFS {tstr}",
                             fontsize=10, fontweight="bold", loc="center", pad=6)

                im = ax.pcolormesh(var.lon, var.lat, var.values, cmap=cmap, vmin=vmin, vmax=vmax,
                                   transform=ccrs.PlateCarree())
                if "ugrd10m" in parameter:
                    ax.quiver(var.lon[::5], var.lat[::5], u.values[::5, ::5], v.values[::5, ::5],
                              transform=ccrs.PlateCarree(), scale=700, width=0.002, color='black')

                ax.coastlines('10m', linewidth=0.6)
                ax.add_feature(cfeature.BORDERS, linestyle=':', linewidth=0.4)
                ax.add_feature(cfeature.LAND, facecolor='lightgray')

                cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.02)
                cbar.set_label(label, fontsize=8)

                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=100)
                buf.seek(0)
                frames.append(imageio.imread(buf))
                plt.close(fig)

            # Simpan animasi ke file GIF di memori
            gif_buffer = io.BytesIO()
            imageio.mimsave(gif_buffer, frames, format='GIF', duration=0.8)
            gif_buffer.seek(0)

            st.image(gif_buffer, caption="Animasi Prakiraan GFS", use_column_width=True)
            st.download_button("📥 Unduh Animasi GIF", data=gif_buffer,
                               file_name=f"animasi_gfs_{parameter.replace(' ', '_')}.gif",
                               mime="image/gif")

    except Exception as e:
        st.error(f"Gagal membuat animasi: {e}")

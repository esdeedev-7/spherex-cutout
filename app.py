import io
import numpy as np
import requests
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from astropy.io import fits
from urllib.parse import urlparse

ALLOWED_HOST = "irsa.ipac.caltech.edu"

st.title("SPHEREx Sky Cutout")
st.write("Paste a SPHEREx spectral image link from IRSA, choose a sky position, then download a small PNG.")

url = st.text_input("SPHEREx image link (from IRSA)")
c1, c2, c3 = st.columns(3)
ra = c1.number_input("RA (degrees)", value=156.09328, format="%.5f")
dec = c2.number_input("Dec (degrees)", value=-41.64466, format="%.5f")
size = c3.number_input("Cutout size (degrees)", value=0.2, min_value=0.05, max_value=1.0, step=0.05)

if st.button("Make image"):
    if not url:
        st.error("Paste a SPHEREx link first.")
    elif urlparse(url).hostname != ALLOWED_HOST:
        st.error("Only IRSA SPHEREx links are allowed.")
    else:
        try:
            full_url = f"{url}?center={ra},{dec}&size={size}"
            with st.spinner("Downloading and cutting out the image..."):
                r = requests.get(full_url, timeout=300)
                r.raise_for_status()
                with fits.open(io.BytesIO(r.content)) as hdul:
                    img = None
                    for hdu in hdul:
                        if hdu.data is not None and hdu.data.ndim >= 2:
                            img = np.array(hdu.data, dtype=float)
                            break
                if img is None:
                    st.error("No image found in that file.")
                    st.stop()
                if img.ndim > 2:
                    img = img[0]
                img = np.nan_to_num(img)
                lo, hi = np.nanpercentile(img, [1, 99.5])
                buf = io.BytesIO()
                plt.imsave(buf, np.flipud(img), cmap="gray", vmin=lo, vmax=hi, format="png")
                png = buf.getvalue()
            st.image(png, caption="Sky cutout")
            st.download_button("Download PNG", png, file_name="spherex_cutout.png", mime="image/png")
        except Exception as e:
            st.error(f"Could not make the image: {e}")
import io
import numpy as np
import requests
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from astropy.io import fits
from scipy.ndimage import gaussian_filter
from urllib.parse import urlparse

ALLOWED_HOST = "irsa.ipac.caltech.edu"

def fetch_cutout(url, ra, dec, size):
    """Download one SPHEREx file and return its image as a 2D array."""
    full_url = f"{url}?center={ra},{dec}&size={size}"
    r = requests.get(full_url, timeout=300)
    r.raise_for_status()
    with fits.open(io.BytesIO(r.content)) as hdul:
        img = None
        for hdu in hdul:
            if hdu.data is not None and hdu.data.ndim >= 2:
                img = np.array(hdu.data, dtype=float)
                break
    if img is None:
        raise ValueError("No image found in that file.")
    if img.ndim > 2:
        img = img[0]
    return np.nan_to_num(img)

def to_png(img, cmap="gray", vmin=None, vmax=None):
    if vmin is None:
        vmin, vmax = np.nanpercentile(img, [1, 99.5])
    buf = io.BytesIO()
    plt.imsave(buf, np.flipud(img), cmap=cmap, vmin=vmin, vmax=vmax, format="png")
    return buf.getvalue()

def clean(img, sigma=20):
    """Remove the smooth background glow and scale to noise units."""
    resid = img - gaussian_filter(img, sigma=sigma)
    return resid / (1.4826 * np.median(np.abs(resid)) + 1e-9)

def check_link(url):
    if not url:
        return "Paste a SPHEREx link first."
    if urlparse(url).hostname != ALLOWED_HOST:
        return "Only IRSA SPHEREx links are allowed."
    return None

st.title("SPHEREx Sky Compare")
st.write("Paste two SPHEREx links from IRSA, for example two different weeks. "
         "The app cuts out the same patch of sky from each and shows what changed.")

url1 = st.text_input("First SPHEREx link (earlier week)")
url2 = st.text_input("Second SPHEREx link (later week)")
c1, c2, c3 = st.columns(3)
ra = c1.number_input("RA (degrees)", value=156.09328, format="%.5f")
dec = c2.number_input("Dec (degrees)", value=-41.64466, format="%.5f")
size = c3.number_input("Cutout size (degrees)", value=0.2, min_value=0.05, max_value=1.0, step=0.05)

if st.button("Compare"):
    err = check_link(url1) or check_link(url2)
    if err:
        st.error(err)
    else:
        try:
            with st.spinner("Downloading and comparing the two weeks..."):
                a = fetch_cutout(url1, ra, dec, size)
                b = fetch_cutout(url2, ra, dec, size)
                # Crop both to the same shape so they can be subtracted
                h = min(a.shape[0], b.shape[0])
                w = min(a.shape[1], b.shape[1])
                a, b = a[:h, :w], b[:h, :w]

                lo, hi = np.nanpercentile(a, [1, 99.5])
                png_a = to_png(a, vmin=lo, vmax=hi)
                png_b = to_png(b, vmin=lo, vmax=hi)
                diff = clean(b) - clean(a)
                png_d = to_png(diff, cmap="bwr", vmin=-10, vmax=10)

            st.subheader("Earlier week")
            st.image(png_a)
            st.subheader("Later week")
            st.image(png_b)
            st.subheader("Difference (red = brighter later, blue = dimmer later)")
            st.image(png_d)
            st.caption("Automatic detection is not included yet. Judge the changes yourself.")
            st.download_button("Download difference PNG", png_d,
                               file_name="spherex_difference.png", mime="image/png")
        except Exception as e:
            st.error(f"Could not compare: {e}")

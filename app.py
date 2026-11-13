import io
import re
import base64
import datetime
import numpy as np
import requests
import streamlit as st
import streamlit.components.v1 as components
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from astropy.io import fits
from scipy.ndimage import gaussian_filter
from urllib.parse import urlparse

ALLOWED_HOST = "irsa.ipac.caltech.edu"
BUILT_IN_1 = "https://irsa.ipac.caltech.edu/ibe/data/spherex/qr2/level2/2025W19_2B/l2b-v20-2025-247/6/level2_2025W19_2B_0073_2D6_spx_l2b-v20-2025-247.fits"
BUILT_IN_2 = "https://irsa.ipac.caltech.edu/ibe/data/spherex/qr2/level2/2025W25_1B/l2b-v20-2025-253/6/level2_2025W25_1B_0768_1D6_spx_l2b-v20-2025-253.fits"

PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SPHEREx Sky Viewer</title>
<style>
body { background: #05070d url("data:image/jpeg;base64,__BG__") center / cover fixed; color: #e8ecf4; }
body { font-family: sans-serif; margin: 8px; }
.stage { position: relative; width: 640px; max-width: 100%; }
.stage img { width: 100%; display: block; }
#b { position: absolute; top: 0; left: 0; opacity: 0; }
</style>
</head>
<body>

<h1>How the Sky Changed: SPHEREx</h1>

<p id="label"></p>

<div class="stage">
  <img id="a" alt="Earlier week">
  <img id="b" alt="Later week">
</div>

<p><input type="range" id="fade" min="0" max="100" value="0" style="width: 640px; max-width: 100%;"></p>

<p>
<button onclick="blink()">Blink</button>
<button onclick="reset()">Show both weeks</button>
<button onclick="diff()">Difference</button>
</p>

<p>Slide to fade from the earlier week to the later week. Stars that stay put look the same in both weeks.</p>
<p>Difference view: red means brighter in the later week. Blue means dimmer in the later week. A star that looks different between weeks shows as a red and blue pair.</p>
<p>This page does not confirm any moving object. Automatic detection is not included yet, so judge the changes yourself.</p>
<p>This publication makes use of data products from the Spectro-Photometer for the History of the Universe,
Epoch of Reionization and Ices Explorer (SPHEREx), which is a joint project of the Jet Propulsion Laboratory
and the California Institute of Technology, and is funded by the National Aeronautics and Space Administration.</p>

<script>
const A = "__A__", B = "__B__", D = "__D__";
const LA = "__LA__", LB = "__LB__";
const a = document.getElementById('a'), b = document.getElementById('b');
const fade = document.getElementById('fade'), label = document.getElementById('label');
let timer = null;
function stop() { if (timer) { clearInterval(timer); timer = null; } }
function reset() {
  stop(); a.src = A; b.src = B; fade.value = 0; b.style.opacity = 0;
  label.textContent = 'Earlier: ' + LA + '   Later: ' + LB;
}
fade.oninput = () => {
  stop(); b.style.opacity = fade.value / 100;
  label.textContent = 'Fading from the earlier week to the later week';
};
function blink() {
  reset();
  let on = false;
  timer = setInterval(() => {
    on = !on; b.style.opacity = on ? 1 : 0;
    label.textContent = on ? 'Later: ' + LB : 'Earlier: ' + LA;
  }, 700);
}
function diff() {
  stop(); a.src = D; b.style.opacity = 0; fade.value = 0;
  label.textContent = 'Difference: later week minus earlier week';
}
reset();
</script>

</body>
</html>"""

def fetch_cutout(url, ra, dec, size):
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

def clean(img, sigma=2):
    resid = img - gaussian_filter(img, sigma=sigma)
    return resid / (1.4826 * np.median(np.abs(resid)) + 1e-9)

def to_uri(img, cmap, vmin, vmax, scale=4):
    img = np.kron(np.flipud(img), np.ones((scale, scale)))  # enlarge, keep pixels sharp
    buf = io.BytesIO()
    plt.imsave(buf, img, cmap=cmap, vmin=vmin, vmax=vmax, format="png")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

def date_label(url):
    m = re.search(r"(2025W\d+)", url)
    return m.group(1) if m else "Unknown week"
    d = re.search(r"-2025-(\d{3})", url)
    if d:
        date = datetime.date(2025, 1, 1) + datetime.timedelta(days=int(d.group(1)) - 1)
        return f"{week} ({date:%B %d, %Y})"
    return week

def check_link(url):
    if not url:
        return "Paste a SPHEREx link first."
    if urlparse(url).hostname != ALLOWED_HOST:
      import os
BG = base64.b64encode(open(os.path.join(os.path.dirname(__file__), "stars.jpg"), "rb").read()).decode()

st.markdown(f"""<style>
.stApp {{ background: #05070d url("data:image/jpeg;base64,{BG}") center / cover fixed; }}
h1, h2, h3, p, label, .stCaption {{ color: #e8ecf4 !important; }}
</style>""", unsafe_allow_html=True)
        return "Only IRSA SPHEREx links are allowed."
    return None

@st.cache_data(show_spinner="Downloading and building the viewer...")
def build_viewer(url1, url2, ra, dec, size):
    a = fetch_cutout(url1, ra, dec, size)
    b = fetch_cutout(url2, ra, dec, size)
    h = min(a.shape[0], b.shape[0])
    w = min(a.shape[1], b.shape[1])
    a, b = a[:h, :w], b[:h, :w]
    lo, hi = np.nanpercentile(a, [1, 99.5])
    ca = gaussian_filter(clean(a), 1.5)
    cb = gaussian_filter(clean(b), 1.5)
    html = PAGE.replace("__A__", to_uri(a, "gray", lo, hi))
    html = html.replace("__B__", to_uri(b, "gray", lo, hi))
    html = html.replace("__D__", to_uri(cb - ca, "bwr", -10, 10))
    html = html.replace("__LA__", date_label(url1)).replace("__LB__", date_label(url2))
    return html

url1 = st.text_input("First SPHEREx link (earlier week)", value=BUILT_IN_1)
url2 = st.text_input("Second SPHEREx link (later week)", value=BUILT_IN_2)
st.caption("The two links above are a built-in example (May and June 2025). "
           "Paste any two SPHEREx links from IRSA to compare other weeks. Both links must be "
           "the same detector band (D6) and the same sky spot, and RA and Dec must point to that spot.")

c1, c2, c3 = st.columns(3)
ra = c1.number_input("RA (degrees)", value=156.09328, format="%.5f")
dec = c2.number_input("Dec (degrees)", value=-41.64466, format="%.5f")
size = c3.number_input("Cutout size (degrees)", value=0.5, min_value=0.05, max_value=1.0, step=0.05)

err = check_link(url1) or check_link(url2)
if err:
    st.error(err)
else:
    try:
        html = build_viewer(url1, url2, ra, dec, float(size))
        components.html(html, height=1200, scrolling=True)
    except Exception as e:
        st.error(f"Could not build the viewer: {e}")

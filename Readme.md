# SPHEREx Sky Viewer

A small web tool for comparing two weeks of SPHEREx sky images, so you can see what changed at a spot in the sky.

**Live viewer (fixed example):** https://spherex-sky-viewer.vercel.app/
**Comparison tool (any IRSA links):** https://spherex-cutout-jirogsnxg7fvm2gtm6hp48.streamlit.app/

## What it does

- **Blink:** switches between the earlier and later week.
- **Fade:** a slider that blends one week into the other.
- **Difference:** shows the change between the two weeks, with red for brighter in the later week and blue for dimmer.
- **Comparison tool:** paste any two SPHEREx spectral image links from IRSA, set the RA and Dec of the spot, and compare them.

## How to use the comparison tool

1. Open the Spectral Image Search on IRSA and search a sky position.
2. Filter `energy_bandpassname` to one band, such as SPHEREx-D6, so both weeks use the same detector.
3. Check two rows from different weeks, generate the download script, and copy the two URLs from the `.txt` file.
4. Paste them into the two link boxes, set RA and Dec to that spot, and press Compare.

Both links must be from the same band and cover the same sky position. Otherwise the difference view shows instrument differences, not sky changes.

## Data

The example uses two weeks of SPHEREx Quick Release data from the IRSA archive, May 8 and June 19, 2025.

This publication makes use of data products from the Spectro-Photometer for the History of the Universe, Epoch of Reionization and Ices Explorer (SPHEREx), which is a joint project of the Jet Propulsion Laboratory and the California Institute of Technology, and is funded by the National Aeronautics and Space Administration.

## Limitations

- **Automatic detection of moving objects is not reliable yet.** We tested a detector with a planted fake object, and it found the fake object. On real data it flagged many candidates, most likely noise and bad pixels, so the app does not report detections.
- Stars that differ slightly between weeks appear as red and blue pairs in the difference view, even when nothing moved.
- Cutouts are small, and the comparison depends on IRSA's server. If IRSA is busy, a link may return a 503 error. Try again later.

## Files

- `app.py`: the Streamlit comparison tool.
- `requirements.txt`: Python packages.
- `stars.jpg`: the background photo.

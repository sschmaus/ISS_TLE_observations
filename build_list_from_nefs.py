### build_list_from_nefs.py
### This script scans for .nef files in the parent directory,
### constructs URLs for each image based on its filename,
### and saves the compiled information into a CSV file and a markdown README.


from pathlib import Path
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

nefs = list(Path("../").rglob("*.nef"))

image_list = []

for nef in nefs:
    
    # iss029e037312.nef
    img_id = nef.stem.upper()  # Get the filename without extension and convert to uppercase
    mission = img_id[:6]       # First 6 characters represent the mission
    roll = img_id[6]           # 7th character represents the roll
    frame = str(int(img_id[7:]))      # Remaining characters represent the frame

    listing = f"https://eol.jsc.nasa.gov/SearchPhotos/photo.pl?mission={mission}&roll={roll}&frame={frame}"
    thumbnail = f"https://eol.jsc.nasa.gov/DatabaseImages/ESC/small/{mission}/{mission}-{roll}-{frame}.JPG"
    fullres = f"https://eol.jsc.nasa.gov/DatabaseImages/ESC/large/{mission}/{mission}-{roll}-{frame}.JPG"
    if int(mission[3:]) < 73:
        nefname = f"{mission.lower()}{roll.lower()}{frame.zfill(6)}.NEF"
    else:
        nefname = f"{mission.lower()}{roll.lower()}{frame.zfill(7)}.NEF"

    raw_request = f"https://eol.jsc.nasa.gov/SearchPhotos/RequestOriginalImage.pl?mission={mission.upper()}&roll={roll}&frame={frame.zfill(6)}&file={nefname}"

    # download thumbnail if not already present
    thumb_path = Path(f"thumbnails/{mission}-{roll}-{frame}.jpg")
    if not thumb_path.exists():
        # download_thumbnail(thumbnail)
        fname = thumbnail.split("/")[-1]

        #download thumbnail
        # reuse a single Session with browser-like headers and retries
        if "session" not in globals():

            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            })
            retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504])
            adapter = HTTPAdapter(max_retries=retries)
            session.mount("https://", adapter)
            session.mount("http://", adapter)

        Path("thumbnails").mkdir(parents=True, exist_ok=True)
        resp = session.get(thumbnail, headers={"Referer": listing}, timeout=10)
        if resp.ok:
            with open(f"thumbnails/{fname}", "wb") as f:
                f.write(resp.content)
            print(f"Downloaded thumbnail for {fname}")
        else:
            print(f"Warning: failed to download {thumbnail} (status {resp.status_code})")

    image_list.append({
        "img_id": f"{mission}-{roll}-{frame}",
        "listing": listing,
        "thumbnail": thumbnail,
        "fullres": fullres,
        "raw_request": raw_request
    })


# save image list as csv
df = pd.DataFrame(image_list)
df.to_csv("image_list.csv", index=False)
print(f"Saved {len(image_list)} entries to image_list.csv")

#save image list as markdown table with thumbnails
with open("README.md", "w") as f:
    f.write("# ISS TLE Observations\n\n")
    f.write("This is a list of images showing Transient Luminous Events (TLEs) captured from the International Space Station (ISS). Each entry includes a thumbnail, a link to the full-resolution image, and a request link for the RAW NEF file.\n\n")
    f.write("| Image ID | Thumbnail | Full Resolution | Request RAW |\n")
    f.write("|----------|-----------|-----------------|-------------|\n")
    for item in image_list:
        img_id = item["img_id"]
        listing = item["listing"]
        thumbnail = item["thumbnail"]
        fullres = item["fullres"]
        raw_request = item["raw_request"]
        f.write(f"| [{img_id}]({listing}) | [![{img_id}]({thumbnail})]({listing}) | [Full resolution]({fullres}) | [Request Raw]({raw_request}) |\n")
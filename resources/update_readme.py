### update_readme.py
### This reads the image_list.csv file, constructs URLs for each image based on its filename,
### and saves the compiled information into the TLE_observations CSV file and a markdown README.


from pathlib import Path
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


dirname = Path(__file__).parent
image_csv = dirname / "image_list.csv"
images_table = pd.read_csv(image_csv).to_dict(orient="records")


image_list = []

for line in images_table:
    
    # iss029e037312.nef
    img_id = line["img_id"]   # Get the filename without extension and convert to uppercase
    mission, roll, frame = img_id.split("-")    
    types = line["type_of_tle"].split(" ")
    astronaut = line["astronaut"]

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
        "astronaut": astronaut,
        "types": (" ").join(types),
        "listing": listing,
        "thumbnail": thumbnail,
        "fullres": fullres,
        "raw_request": raw_request,
    })


# save image list as csv
df = pd.DataFrame(image_list)
df.to_csv(dirname.parent / "TLE_observations.csv", index=False)
print(f"Saved {len(image_list)} entries to TLE_observations.csv")

# save image list as markdown using a template header, then append the table
template_path = dirname / "readme_template.md"
with open(dirname.parent / "README.md", "w", encoding="utf-8") as f:
    with open(template_path, "r", encoding="utf-8") as tf:
        template = tf.read().rstrip()
        f.write(template + "\n\n")
    f.write("| Image ID | Thumbnail | Info | Download |\n")
    f.write("|----------|-----------|------|----------|\n")
    for item in image_list:
        img_id = item["img_id"]
        listing = item["listing"]
        thumbnail = item["thumbnail"]
        fullres = item["fullres"]
        raw_request = item["raw_request"]
        types = item["types"].split(" ")
        astronaut = item["astronaut"] if not pd.isna(item["astronaut"]) else "*Unknown*"
        f.write(f"| [{img_id}]({listing}) | [<img src=\"{thumbnail}\" width=\"300px\"/>]({listing}) | TLE Type: {', '.join(types)} <br/><br/> Astronaut: {astronaut} | [Full resolution]({fullres}) <br/><br/> [Request Raw]({raw_request}) |\n")
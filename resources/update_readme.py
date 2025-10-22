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


class ImageID:
    """Class to generate URLs and filenames for ISS images."""

    def __init__(self, img_id):
        """Initialize with img_id in format 'mission-roll-frame'."""
        self.img_id = img_id
        self.mission, self.roll, self.frame = img_id.split("-")

    def __str__(self):
        return self.img_id

    @property
    def listing(self):
        return f"https://eol.jsc.nasa.gov/SearchPhotos/photo.pl?mission={self.mission}&roll={self.roll}&frame={self.frame}"

    @property
    def thumbnail(self):
        return f"https://eol.jsc.nasa.gov/DatabaseImages/ESC/small/{self.mission}/{self.mission}-{self.roll}-{self.frame}.JPG"

    @property
    def fullres(self):
        return f"https://eol.jsc.nasa.gov/DatabaseImages/ESC/large/{self.mission}/{self.mission}-{self.roll}-{self.frame}.JPG"

    @property
    def nefname(self):
        if int(self.mission[3:]) < 73:
            return f"{self.mission.lower()}{self.roll.lower()}{self.frame.zfill(6)}.NEF"
        else:
            return f"{self.mission.lower()}{self.roll.lower()}{self.frame.zfill(7)}.NEF"

    @property
    def jpgname(self):
        return f"{self.img_id}.JPG".upper()

    @property
    def raw_request(self):
        return f"https://eol.jsc.nasa.gov/SearchPhotos/RequestOriginalImage.pl?mission={self.mission.upper()}&roll={self.roll}&frame={self.frame.zfill(6)}&file={self.nefname}"


image_list = []

for line in images_table:
    # iss029e037312.nef
    img_id = ImageID(
        line["img_id"]
    )  # Get the filename without extension and convert to uppercase

    types = line["type_of_tle"].split(" ")
    astronaut = line["astronaut"]

    # listing = img_id.listing
    # thumbnail = img_id.thumbnail
    # fullres = img_id.fullres
    # nefname = img_id.nefname
    # raw_request = img_id.raw_request

    # download thumbnail if not already present
    thumb_path = Path(f"thumbnails/unprocessed/{img_id}.JPG")
    if not thumb_path.exists():
        # download_thumbnail(thumbnail)
        fname = img_id.thumbnail.split("/")[-1]

        # download thumbnail
        # reuse a single Session with browser-like headers and retries
        if "session" not in globals():
            session = requests.Session()
            session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
                    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                }
            )
            retries = Retry(
                total=3, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504]
            )
            adapter = HTTPAdapter(max_retries=retries)
            session.mount("https://", adapter)
            session.mount("http://", adapter)

        Path("thumbnails/unprocessed/").mkdir(parents=True, exist_ok=True)
        resp = session.get(
            img_id.thumbnail, headers={"Referer": img_id.listing}, timeout=10
        )
        if resp.ok:
            with open(f"thumbnails/unprocessed/{fname}", "wb") as f:
                f.write(resp.content)
            print(f"Downloaded thumbnail for {fname}")
        else:
            print(
                f"Warning: failed to download {img_id.thumbnail} (status {resp.status_code})"
            )

    image_list.append(
        {
            "img_id": img_id.__str__(),
            "astronaut": astronaut,
            "types": (" ").join(types),
            "listing": img_id.listing,
            "thumbnail": img_id.thumbnail,
            "fullres": img_id.fullres,
            "raw_request": img_id.raw_request,
        }
    )


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
    f.write("| Image ID | Processed crop | Processed preview | Info | Download |\n")
    f.write("|----------|----------------|-------------------|------|----------|\n")
    for item in image_list:
        img_id = ImageID(item["img_id"])
        types = item["types"].split(" ")
        astronaut = item["astronaut"] if not pd.isna(item["astronaut"]) else "*Unknown*"

        preview_crop = f"thumbnails/crop/{img_id.nefname.replace('.NEF', '.jpg')}"
        preview_edit = f"thumbnails/edit/{img_id.nefname.replace('.NEF', '.jpg')}"

        #check if preview files exist
        if not Path(preview_crop).exists() or not Path(preview_edit).exists():
            print(f"Warning: preview files for {img_id} do not exist, please export them from Lightroom.")
        f.write(
            f'| [{img_id}]({img_id.listing}) '\
            f'| [<img src="{preview_crop}" width="200px"/>]({img_id.listing}) ' \
            f'| [<img src="{preview_edit}" width="300px"/>]({img_id.listing}) ' \
            f'| TLE Type: {", ".join(types)} <br/><br/> Astronaut: {astronaut} ' \
            f'| [Full resolution]({img_id.fullres}) <br/><br/> [Request Raw]({img_id.raw_request}) |\n'
        )

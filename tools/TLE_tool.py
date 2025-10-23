### update_readme.py
### This reads the image_list.csv file, constructs URLs for each image based on its filename,
### and saves the compiled information into the TLE_observations CSV file and a markdown README.


from pathlib import Path
import pandas as pd

from gape import ImageID, download
import argparse


dirname = Path(__file__).parent

def read_tle_observations():
    """read TLE observations from CSV"""
    df = pd.read_csv(dirname.parent / "TLE_observations.csv")
    return df

def write_tle_observations(image_df):
    """write TLE observations to CSV"""
    # sort by img_id
    image_df = image_df.sort_values(by="img_id").reset_index(drop=True)
    # save to CSV
    image_df.to_csv(dirname.parent / "TLE_observations.csv", index=False)
    print(f"Saved {len(image_df)} entries to TLE_observations.csv")

def add_image(img_id, astronaut, types_of_tle, images_df=read_tle_observations(), overwrite=False):
    """Add a new image entry to the image_list.csv file."""
    img_id = ImageID(img_id)

    types_of_tle = types_of_tle if isinstance(types_of_tle, list) else [types_of_tle]

    new_entry = {
                "img_id": img_id.__str__(),
                "astronaut": astronaut,
                "types": f'{", ".join(types_of_tle)}',
                "listing_url": img_id.listing,
                "small_url": img_id.small,
                "large_url": img_id.large,
                "raw_request_url": img_id.raw_request,
            }
    # check for duplicates with pandas
    df = images_df
    if img_id.__str__() in df["img_id"].values and overwrite:
        # replace existing entry completely
        print(f"Overwriting existing entry for {img_id} in image_list.csv")
        df = df[df["img_id"] != img_id.__str__()]  # remove existing entry
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    elif img_id.__str__() in df["img_id"].values and not overwrite:
        # only update url fields in case they were generated incorrectly before
        print(f"Image {img_id} already exists in image_list., skipping entry. To overwrite, set overwrite=True.")
        df.loc[df["img_id"] == img_id.__str__(), ["listing_url", "small_url", "large_url", "raw_request_url"]] = \
            img_id.listing, img_id.small, img_id.large, img_id.raw_request
    else: 
        # append new entry
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        print(f"Added new entry for {img_id} to image_list.csv")

    return df

def update_thumbnails(image_df=read_tle_observations()):
    """check that thumbnails are downloaded for all images in the dataframe"""
    for _, row in image_df.iterrows():
        img_id = ImageID(row["img_id"])

        # download thumbnail if not already present
        thumb_path = Path(f"thumbnails/unprocessed/{img_id}.JPG")
        if not thumb_path.exists():
            # download thumbnail
            download(img_id, thumb_path.parent, img_size="small")

def update_readme():
    """save image list as markdown using a template header, then append the table"""

    df = read_tle_observations()
    image_list = df.to_dict(orient="records")

    # ensure thumbnails are present
    update_thumbnails(df)

    template_path = dirname / "readme_template.md"
    with open(dirname.parent / "README.md", "w", encoding="utf-8") as f:
        with open(template_path, "r", encoding="utf-8") as tf:
            template = tf.read().rstrip()
            f.write(template + "\n\n")
        f.write(
            "| Photo Number | Processed crop | Processed full | Info | Download |\n"
        )
        f.write(
            "|--------------|----------------|----------------|------|----------|\n"
        )
        for item in image_list:
            img_id = ImageID(item["img_id"])
            types = item["types"].split(" ")
            astronaut = (
                item["astronaut"] if not pd.isna(item["astronaut"]) else "*Unknown*"
            )

            preview_crop = f"thumbnails/crop/{img_id.nefname.replace('.NEF', '.jpg')}"
            preview_full = f"thumbnails/edit/{img_id.nefname.replace('.NEF', '.jpg')}"

            # check if preview files exist
            if not Path(preview_crop).exists() or not Path(preview_full).exists():
                print(
                    f"Warning: preview files for {img_id} do not exist, please export them from Lightroom."
                )
                preview_full = f"thumbnails/unprocessed/{img_id.jpgname}"
            f.write(
                f'| [{img_id}]({img_id.listing} "Link to the image listing") '
                f'| [<img src="{preview_crop}" width="200px"/>]({preview_crop} "Full resolution will be uploaded to Flickr") '
                f'| [<img src="{preview_full}" width="300px"/>]({preview_full} "Full resolution will be uploaded to Flickr") '
                f"| TLE Type: {', '.join(types)} <br/><br/> Astronaut: {astronaut} "
                f"| [Full resolution]({img_id.large}) <br/><br/> [Request Raw]({img_id.raw_request}) |\n"
            )

def cli_add_image():
    """call the add_image function from command line arguments"""
    img_id = ImageID(input("Enter image ID (e.g., ISS029-E-37312): ").strip())
    astronaut = input("Enter astronaut name (or leave blank): ").strip()
    types_of_tle = input("Enter types of TLE (comma-separated): ").strip().split(",")
    overwrite = input("Overwrite existing entry if present? (y/n): ").strip().lower() == "y"

    images_df = read_tle_observations()
    updated_df = add_image(img_id, astronaut, types_of_tle, images_df, overwrite)
    write_tle_observations(updated_df)
    

def main():
    parser = argparse.ArgumentParser(prog="tool", description="ISS TLE Observations Tool")

    parser.add_argument(
        "--add-image",
        action="store_true",
        help="Add a new image entry to the TLE_observations.csv file.",
    )
    parser.add_argument(
        "--update-readme",
        action="store_true",
        help="Update the README.md file with the latest image list.",
    )
    args = parser.parse_args()

    if args.add_image:
        cli_add_image()
    if args.update_readme:
        update_readme()


if __name__ == "__main__":
    main()

    # images_df = read_tle_observations()
    # updated_df = add_image("ISS065-E-394522", "Thomas Pesquet", ["sprite", "halo"], images_df, True)
    # write_tle_observations(updated_df)
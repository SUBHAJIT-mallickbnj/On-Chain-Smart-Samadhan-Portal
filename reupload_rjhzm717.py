"""
One-time script: Upload RJHZM717's local media file to Cloudinary and update the CSV.
"""
import os, pandas as pd, csv
import cloudinary, cloudinary.uploader
from config import Config

# Configure Cloudinary
cloudinary.config(
    cloud_name=Config.CLOUDINARY_CLOUD_NAME,
    api_key=Config.CLOUDINARY_API_KEY,
    api_secret=Config.CLOUDINARY_API_SECRET,
    secure=True,
)

LOCAL_PATH = os.path.join("static", "uploads", "complaints", "RJHZM717", "file_0.jpeg")
REF_NO = "RJHZM717"

if not os.path.exists(LOCAL_PATH):
    print(f"❌ Local file not found: {LOCAL_PATH}")
else:
    try:
        result = cloudinary.uploader.upload(
            LOCAL_PATH,
            folder=f"complaints/{REF_NO}",
            resource_type="image",
            use_filename=True,
            unique_filename=True,
        )
        url = result.get("secure_url", "")
        print(f"✅ Uploaded to Cloudinary: {url}")

        # Update complaints.csv
        df = pd.read_csv("complaints.csv", quoting=csv.QUOTE_MINIMAL, on_bad_lines="skip")
        mask = df["Reference No"].astype(str) == REF_NO
        df.loc[mask, "Media URLs"] = url
        df.to_csv("complaints.csv", index=False, quoting=csv.QUOTE_MINIMAL)
        print(f"✅ Updated CSV for {REF_NO}")
    except Exception as e:
        print(f"❌ Failed: {e}")

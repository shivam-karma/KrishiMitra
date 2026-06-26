"""
Downloads leaf disease images from PlantVillage dataset on GitHub.
Downloads ~100 images per class into dataset/train/<Class>/.
Run this BEFORE train_model.py.

Usage:
    python download_data.py
"""
import os
import requests
import time

BASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset", "train")

# GitHub raw base
RAW = "https://raw.githubusercontent.com/spmohanty/plantvillage-dataset/master/raw/color"

# Map class name → list of GitHub folder paths to pull images from
SOURCES = {
    "Healthy": [
        "Apple___healthy",
        "Blueberry___healthy",
        "Cherry_(including_sour)___healthy",
        "Grape___healthy",
        "Peach___healthy",
        "Pepper,_bell___healthy",
        "Raspberry___healthy",
        "Soybean___healthy",
        "Strawberry___healthy",
        "Tomato___healthy",
    ],
    "Leaf_Spot": [
        "Tomato___Septoria_leaf_spot",
        "Tomato___Target_Spot",
        "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
        "Strawberry___Leaf_scorch",
        "Cherry_(including_sour)___Powdery_mildew",
        "Tomato___Early_blight",
        "Tomato___Late_blight",
        "Potato___Early_blight",
        "Potato___Late_blight",
    ],
    "Rust": [
        "Corn_(maize)___Common_rust_",
        "Apple___Cedar_apple_rust",
        "Wheat___Yellow_Rust_Stripe_Rust",
    ],
}

IMAGES_PER_CLASS = 100  # target images per class
DELAY = 0.05            # seconds between requests (be gentle to GitHub)

def get_file_list(folder_name: str) -> list[str]:
    """Use GitHub API to list all files in a PlantVillage folder."""
    api_url = f"https://api.github.com/repos/spmohanty/plantvillage-dataset/contents/raw/color/{folder_name}"
    try:
        resp = requests.get(api_url, timeout=15)
        if resp.status_code == 200:
            return [f["name"] for f in resp.json() if f["name"].lower().endswith((".jpg", ".jpeg", ".png"))]
    except Exception as e:
        print(f"  API error for {folder_name}: {e}")
    return []

def download_images():
    for class_name, folders in SOURCES.items():
        out_dir = os.path.join(BASE_PATH, class_name)
        os.makedirs(out_dir, exist_ok=True)

        downloaded = 0
        target = IMAGES_PER_CLASS

        print(f"\n{'='*50}")
        print(f"Class: {class_name}  (target: {target} images)")
        print(f"{'='*50}")

        for folder in folders:
            if downloaded >= target:
                break

            print(f"  Scanning folder: {folder}")
            filenames = get_file_list(folder)
            print(f"  Found {len(filenames)} files")

            for filename in filenames:
                if downloaded >= target:
                    break

                save_path = os.path.join(out_dir, f"{class_name}_{downloaded:03d}.jpg")
                if os.path.exists(save_path):
                    downloaded += 1
                    continue

                encoded_name = requests.utils.quote(filename)
                url = f"{RAW}/{folder}/{encoded_name}"
                try:
                    r = requests.get(url, timeout=15)
                    if r.status_code == 200:
                        with open(save_path, "wb") as f:
                            f.write(r.content)
                        downloaded += 1
                        if downloaded % 10 == 0:
                            print(f"  [{class_name}] Downloaded {downloaded}/{target}")
                    time.sleep(DELAY)
                except Exception as e:
                    print(f"  Error: {e}")

        print(f"  ✅ {class_name}: {downloaded} images saved to {out_dir}")

if __name__ == "__main__":
    print("KrishiMitra — Leaf Disease Dataset Downloader")
    print(f"Saving to: {BASE_PATH}\n")
    download_images()
    print("\n✅ Download complete! Now run: python train_model.py")

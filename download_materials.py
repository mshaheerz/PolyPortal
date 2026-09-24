"""
download_materials.py
Downloads high quality, royalty-free CC0 PBR texture sets from Poly Haven API (1k jpg maps).
Stores maps in materials/<category>/
- Diffuse / Albedo
- Roughness
- Normal GL
"""

import os
import sys
import json
import urllib.request

MATERIALS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "materials")

TEXTURE_TARGETS = {
    "wood":    "dark_wood",
    "leather": "brown_leather",
    "marble":  "marble_01",
    "metal":   "metal_plate"
}

HEADERS = {"User-Agent": "BlenderPBRAutomator/1.0"}

def download_file(url, dest_path):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as out:
        out.write(resp.read())

def download_material(category, texture_id):
    target_dir = os.path.join(MATERIALS_DIR, category)
    os.makedirs(target_dir, exist_ok=True)
    
    print(f"[*] Fetching metadata for '{texture_id}' ({category})...")
    api_url = f"https://api.polyhaven.com/files/{texture_id}"
    req = urllib.request.Request(api_url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        info = json.loads(resp.read().decode("utf-8"))

    # Map types to extract
    maps = {
        "diffuse": ("Diffuse", "diff"),
        "roughness": ("Rough", "rough"),
        "normal": ("nor_gl", "nor")
    }

    for map_key, (primary, fallback) in maps.items():
        key_found = primary if primary in info else (fallback if fallback in info else None)
        if not key_found:
            for k in info:
                if fallback in k.lower():
                    key_found = k
                    break
        
        if key_found and "1k" in info[key_found] and "jpg" in info[key_found]["1k"]:
            file_url = info[key_found]["1k"]["jpg"]["url"]
            dest_file = os.path.join(target_dir, f"{map_key}.jpg")
            if not os.path.exists(dest_file):
                print(f"    -> Downloading {map_key} ({file_url.split('/')[-1]})...")
                download_file(file_url, dest_file)
            else:
                print(f"    -> {map_key}.jpg already exists.")
        else:
            print(f"    [!] Warning: map '{map_key}' not found in 1k jpg format for {texture_id}")

    print(f"[+] '{category}' material ready at: {target_dir}\n")

def main():
    print("="*50)
    print("  Downloading PBR Texture Libraries (Poly Haven CC0)")
    print("="*50 + "\n")
    
    for category, texture_id in TEXTURE_TARGETS.items():
        try:
            download_material(category, texture_id)
        except Exception as e:
            print(f"[!] Error downloading {category}: {e}\n")

    print("[SUCCESS] All materials downloaded.")

if __name__ == "__main__":
    main()

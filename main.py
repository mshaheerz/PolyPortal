"""
main.py — Orchestrator for the automated 3D model pipeline
Run this daily via Task Scheduler (through run_daily.bat)
"""

import os
import sys
import json
import subprocess
import datetime
import csv

# ─────────────────────────────────────────
# Paths (relative to this script's directory)
# ─────────────────────────────────────────
SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE    = os.path.join(SCRIPT_DIR, "config.json")
CATEGORIES_FILE = os.path.join(SCRIPT_DIR, "categories.json")
BLENDER_SCRIPT = os.path.join(SCRIPT_DIR, "blender", "generate_model.py")
LOG_FILE       = os.path.join(SCRIPT_DIR, "tracker", "log.csv")

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def load_categories():
    with open(CATEGORIES_FILE, 'r') as f:
        return json.load(f)

import random
import argparse

def get_model_index(categories, force_name=None, force_style=None):
    """
    Select model index. Supports random selection without immediate repeats,
    or forcing a specific model name / style (e.g. 'photorealistic' / 'high_poly').
    """
    os.makedirs(os.path.join(SCRIPT_DIR, "tracker"), exist_ok=True)
    history_file = os.path.join(SCRIPT_DIR, "tracker", "history.json")

    # If specific model name requested
    if force_name:
        for i, c in enumerate(categories):
            if c["name"].lower() == force_name.lower():
                return i
        try:
            val = int(force_name)
            if 0 <= val < len(categories):
                return val
        except ValueError:
            pass

    # Filter candidate indices
    if force_style in ("high_poly", "photorealistic"):
        candidate_indices = [
            i for i, c in enumerate(categories)
            if c.get("style") in ("photorealistic", "high_poly") or c["name"].startswith("hp_")
        ]
    elif force_style == "low_poly":
        candidate_indices = [
            i for i, c in enumerate(categories)
            if c.get("style") not in ("photorealistic", "high_poly") and not c["name"].startswith("hp_")
        ]
    else:
        candidate_indices = list(range(len(categories)))

    # Load recently used indices to avoid immediate repeats
    used = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                used = json.load(f)
        except Exception:
            used = []

    available = [i for i in candidate_indices if i not in used]
    if not available:
        # All candidates have been used; reset history pool
        available = candidate_indices
        used = [i for i in used if i not in candidate_indices]

    selected_idx = random.choice(available)
    used.append(selected_idx)

    with open(history_file, "w") as f:
        json.dump(used, f)

    return selected_idx


def write_info_txt(output_dir, model_data):
    """Write a ready-to-copy info file for manual upload to Sketchfab."""
    info_path = os.path.join(output_dir, "info.txt")
    content = f"""
==============================================
  SKETCHFAB UPLOAD INFO — Copy & Paste Below
==============================================

TITLE:
{model_data['title']}

DESCRIPTION:
{model_data['description']}

TAGS (paste as comma-separated):
{', '.join(model_data['tags'])}

SUGGESTED PRICE: ${model_data['price']} USD

CATEGORY: {model_data['category'].title()}

FILES TO UPLOAD:
  • {model_data['name']}.glb   ← Main upload file (drag to Sketchfab)
  • {model_data['name']}.fbx   ← Include in ZIP for buyers
  • {model_data['name']}.obj   ← Include in ZIP for buyers

THUMBNAIL:
  Use preview_perspective.png as the main thumbnail.

==============================================
"""
    with open(info_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("  -> info.txt written")

def log_result(model_data, output_dir, status, error=""):
    """Append result to tracker/log.csv."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    fieldnames = ["date", "model_name", "display_name", "category",
                  "price", "output_dir", "status", "error"]
    write_header = not os.path.exists(LOG_FILE)

    with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "date":         datetime.date.today().isoformat(),
            "model_name":   model_data.get("name", ""),
            "display_name": model_data.get("display_name", ""),
            "category":     model_data.get("category", ""),
            "price":        model_data.get("price", ""),
            "output_dir":   output_dir,
            "status":       status,
            "error":        error,
        })

def main():
    parser = argparse.ArgumentParser(description="Automated 3D Model Generator")
    parser.add_argument("--model", type=str, default=None, help="Force a specific model name or index")
    parser.add_argument("--style", type=str, choices=["low_poly", "high_poly", "photorealistic"], default=None, help="Filter by model style")
    cli_args = parser.parse_args()

    print("\n" + "="*50)
    print("  [BOT] 3D Model Automation Pipeline")
    print(f"  Date: {datetime.date.today()}")
    print("="*50 + "\n")

    # -- Load config & categories --
    config     = load_config()
    categories = load_categories()
    blender    = config["blender_path"]
    resolution = config.get("render_resolution", [1080, 1080])[0]
    samples    = config.get("render_samples", 64)

    # -- Pick today's model --
    idx        = get_model_index(categories, force_name=cli_args.model, force_style=cli_args.style)
    model_data = categories[idx]
    is_hp      = model_data.get("style") in ("photorealistic", "high_poly") or model_data["name"].startswith("hp_")
    print(f"[MODEL] Selected: {model_data['display_name']} ({'High Poly / Photorealistic' if is_hp else 'Low Poly'}) [Index: #{idx+1}]")

    # -- Create dated output folder --
    today       = datetime.date.today().isoformat()
    folder_name = f"{today}_{model_data['name']}"
    output_dir  = os.path.join(SCRIPT_DIR, config["output_dir"], folder_name)
    os.makedirs(output_dir, exist_ok=True)
    print(f"[FOLDER] Output folder: {output_dir}\n")

    # -- Run Blender headless --
    cmd = [
        blender,
        "--background",
        "--python", BLENDER_SCRIPT,
        "--",
        "--category_file", CATEGORIES_FILE,
        "--output_dir",    output_dir,
        "--model_index",   str(idx),
        "--resolution",    str(resolution),
        "--samples",       str(samples),
    ]

    print(f"[BLENDER] Running Blender (this takes 1-3 minutes)...\n")
    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode != 0:
        print(f"\n[ERROR] Blender failed with exit code {result.returncode}")
        log_result(model_data, output_dir, "FAILED", f"Exit code {result.returncode}")
        sys.exit(1)

    # -- Write info.txt for manual upload --
    print(f"\n[INFO] Writing upload info...")
    write_info_txt(output_dir, model_data)

    # -- Log success --
    log_result(model_data, output_dir, "SUCCESS")

    print("\n" + "="*50)
    print("  DONE! Your model is ready to upload.")
    print(f"  Open: {output_dir}")
    print("  Copy info.txt -> paste into Sketchfab")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()

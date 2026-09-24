# 🌌 PolyPortal

**PolyPortal** is a unified, locally-hosted Command Center for AI Image-to-3D generation. It routes concept images to state-of-the-art AI engines (HuggingFace, Colab, and REST APIs), generates 3D meshes, and can automatically execute headless Blender scripts to clean up the geometry and assign PBR materials.

![PolyPortal UI Screenshot](https://raw.githubusercontent.com/gradio-app/gradio/main/guides/assets/gradio-logo.svg) <!-- Replace with an actual screenshot of your UI later! -->

## ✨ Features

- **Multi-Engine Routing:** Easily switch between the world's best open-source and commercial Image-to-3D models:
  - `TRELLIS` (via HuggingFace Spaces)
  - `Stable Fast 3D` (via HuggingFace Spaces)
  - `InstantMesh` (via HuggingFace Spaces)
  - `TripoSR` (via Custom Google Colab URLs)
  - `Meshy.ai` (via official REST API)
- **Automated Blender Post-Processing:** Optionally trigger a background Blender script (`mesh_cleanup.py`) that scales the raw mesh, decimates it, and overwrites the default vertex colors with a sleek metallic PBR material.
- **Dynamic API Key Vault:** Securely stores your HuggingFace tokens and Meshy API keys in a local JSON file so you never have to re-type them, while dynamically hiding inputs you aren't actively using.
- **Persistent Output Gallery:** Keeps a timestamped history of all your generated `.glb` models and displays them in a built-in interactive 3D viewer.

## 🛠️ Prerequisites

1. **Python 3.10+**
2. **Blender:** Must be installed on your system. 
   * *Note: Open `portal.py` and update the `BLENDER_EXE` variable to point to your local Blender executable path if it differs from the default.*

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/PolyPortal.git
cd PolyPortal
```

2. Install the required Python dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure `mesh_cleanup.py` is in the same directory (or update the `CLEANUP_SCRIPT` path in `portal.py`).

## 🎮 Usage

Run the web portal using Python (or your Blender Python environment):

```bash
python portal.py
```

The Command Center will open in your browser at `http://127.0.0.1:7860`. 

1. **Upload** a concept image.
2. **Select** your preferred AI Engine.
3. **Configure** API Keys (keys are automatically saved locally).
4. **Toggle** Auto-Cleanup (Leave unchecked to preserve full-color textures for TRELLIS, SF3D, and Meshy).
5. **Generate & View!**

## ⚠️ Security Note
Your API keys are saved locally in `output/portal_settings.json`. This file is explicitly ignored in the `.gitignore` to prevent you from accidentally uploading your private keys to GitHub.

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the issues page.

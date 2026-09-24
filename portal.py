import gradio as gr
import os
import subprocess
import shutil
import datetime
import glob
import requests
import base64
import time
from gradio_client import Client, handle_file

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
CLEANUP_SCRIPT = r"c:\Users\Sunu\Documents\home\zaigopc\Desktop\personal\automate\mesh_cleanup.py"
OUTPUT_DIR = r"c:\Users\Sunu\Documents\home\zaigopc\Desktop\personal\automate\output\portal_builds"
SETTINGS_FILE = os.path.join(OUTPUT_DIR, "portal_settings.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

import json
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"colab_url": "", "meshy_key": "", "hf_token": ""}

def save_settings(colab_url, meshy_key, hf_token):
    with open(SETTINGS_FILE, "w") as f:
        json.dump({"colab_url": colab_url, "meshy_key": meshy_key, "hf_token": hf_token}, f)

def get_history():
    files = glob.glob(os.path.join(OUTPUT_DIR, "build_*", "final_*.glb"))
    files.sort(key=os.path.getmtime, reverse=True)
    choices = [(os.path.basename(os.path.dirname(f)), f) for f in files]
    return choices

def load_history_model(filepath):
    if filepath and os.path.exists(filepath):
        return filepath, filepath
    return None, None

def run_pipeline(image_path, backend_choice, custom_url, hf_token, meshy_key, run_cleanup):
    save_settings(custom_url, meshy_key, hf_token)
    
    if not image_path:
        return gr.update(), None, None, "Error: Please upload a concept image."
        
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = os.path.join(OUTPUT_DIR, f"build_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)
    
    raw_glb_path = os.path.join(run_dir, f"raw_{timestamp}.glb")
    final_glb_path = os.path.join(run_dir, f"final_{timestamp}.glb")
    
    try:
        # === 1. ENGINE ROUTING ===
        if backend_choice == "Colab / Custom URL (TripoSR)":
            if not custom_url:
                return gr.update(), None, None, "Error: Please provide your Colab URL."
            client = Client(custom_url)
            yield gr.update(), None, None, "1/3: Removing background on Colab Server..."
            processed_image = client.predict(handle_file(image_path), True, 0.85, api_name="/preprocess")
            yield gr.update(), None, None, "2/3: Generating 3D Mesh on Colab Server..."
            result = client.predict(handle_file(processed_image), 256, api_name="/generate")
            downloaded_glb = result[1] if isinstance(result, (list, tuple)) and len(result) > 1 else result

        elif backend_choice == "HuggingFace API (InstantMesh)":
            if not hf_token: return gr.update(), None, None, "Error: Missing HF Token."
            client = Client("TencentARC/InstantMesh", token=hf_token)
            yield gr.update(), None, None, "1/3: Preprocessing & Generating multi-views (InstantMesh)..."
            processed_image = client.predict(handle_file(image_path), True, api_name="/preprocess")
            client.predict(handle_file(processed_image), 75, 42, api_name="/generate_mvs")
            yield gr.update(), None, None, "2/3: Reconstructing 3D Mesh..."
            result = client.predict(api_name="/make3d")
            downloaded_glb = result[1] if isinstance(result, tuple) else result

        elif backend_choice == "HuggingFace API (Stable Fast 3D)":
            if not hf_token: return gr.update(), None, None, "Error: Missing HF Token."
            client = Client("stabilityai/stable-fast-3d", token=hf_token)
            yield gr.update(), None, None, "1/2: Processing Image Background..."
            try:
                bg_res = client.predict(handle_file(image_path), 0.85, api_name="/requires_bg_remove")
                bg_path = bg_res[0]["value"] if isinstance(bg_res, tuple) else bg_res
                yield gr.update(), None, None, "2/2: Generating Mesh with Stable Fast 3D (0.5 seconds)..."
                result = client.predict(handle_file(bg_path), api_name="/run_button")
                downloaded_glb = result[1] if isinstance(result, tuple) else result
            except Exception as sf3d_err:
                raise Exception(f"Stability AI's HuggingFace space is currently down or overloaded: {str(sf3d_err)}")

        elif backend_choice == "HuggingFace API (TRELLIS)":
            if not hf_token: return gr.update(), None, None, "Error: Missing HF Token."
            client = Client("microsoft/TRELLIS.2", token=hf_token)
            yield gr.update(), None, None, "1/3: Preprocessing image (TRELLIS)..."
            # Use positional args to avoid 'image is not a valid key-word argument' error
            processed_image = client.predict(handle_file(image_path), api_name="/preprocess_image")
            yield gr.update(), None, None, "2/3: Generating 3D Structured Latents (Takes ~30 seconds)..."
            client.predict(handle_file(processed_image), api_name="/image_to_3d")
            yield gr.update(), None, None, "3/3: Extracting high-res GLB..."
            result = client.predict(300000, 2048, api_name="/extract_glb")
            downloaded_glb = result[1] if isinstance(result, tuple) else result

        elif backend_choice == "Meshy.ai API":
            if not meshy_key: return gr.update(), None, None, "Error: Please provide your Meshy API Key."
            yield gr.update(), None, None, "1/3: Uploading to Meshy API..."
            with open(image_path, "rb") as f:
                b64_img = base64.b64encode(f.read()).decode("utf-8")
            data_uri = f"data:image/png;base64,{b64_img}"
            headers = {"Authorization": f"Bearer {meshy_key}"}
            payload = {"image_url": data_uri, "enable_pbr": True}
            
            response = requests.post("https://api.meshy.ai/v1/image-to-3d", headers=headers, json=payload)
            if response.status_code != 200:
                raise Exception(f"Meshy API Error: {response.text}")
            task_id = response.json()["result"]
            
            yield gr.update(), None, None, "2/3: Meshy is modeling your asset (this takes a few minutes)..."
            while True:
                resp = requests.get(f"https://api.meshy.ai/v1/image-to-3d/{task_id}", headers=headers).json()
                if resp["status"] == "SUCCEEDED":
                    model_url = resp["model_urls"]["glb"]
                    break
                elif resp["status"] in ["FAILED", "EXPIRED"]:
                    raise Exception(f"Meshy Task Failed: {resp}")
                time.sleep(5)
            
            yield gr.update(), None, None, "3/3: Downloading Meshy GLB..."
            dl_resp = requests.get(model_url)
            with open(raw_glb_path, "wb") as f:
                f.write(dl_resp.content)
            downloaded_glb = raw_glb_path

        # === 2. SAVE RAW FILE ===
        if downloaded_glb != raw_glb_path:
            shutil.copy2(downloaded_glb, raw_glb_path)
        
        # === 3. BLENDER CLEANUP ===
        if run_cleanup:
            yield gr.update(), None, None, "Final Step: Running Blender Auto-Cleanup (Decimating, Metallic Materials)..."
            cmd = [
                BLENDER_EXE,
                "--background",
                "--python", CLEANUP_SCRIPT,
                "--",
                raw_glb_path,
                final_glb_path
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            if not os.path.exists(final_glb_path):
                raise Exception("Blender finished but no output file was found!")
        else:
            yield gr.update(), None, None, "Skipping Blender Cleanup to preserve textures..."
            shutil.copy2(raw_glb_path, final_glb_path)
            
        # === 4. SUCCESS ===
        choices = get_history()
        yield gr.update(choices=choices, value=final_glb_path), final_glb_path, final_glb_path, f"Success! Saved to: {run_dir}"
        
    except Exception as e:
        yield gr.update(), None, None, f"Error occurred: {str(e)}"

settings = load_settings()

def update_settings_ui(choice):
    # Returns (colab_box_visible, hf_box_visible, meshy_box_visible)
    if "Colab" in choice:
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)
    elif "Meshy" in choice:
        return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)
    else:
        return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)


# Refined, modern UI styling
custom_theme = gr.themes.Soft(
    primary_hue="indigo", 
    secondary_hue="blue",
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"]
)

with gr.Blocks(title="3D Command Center", theme=custom_theme) as demo:
    gr.HTML("""
    <div style='text-align: center; padding: 25px 0; margin-bottom: 20px; background: linear-gradient(90deg, rgba(79,70,229,0.1) 0%, rgba(59,130,246,0.1) 100%); border-radius: 12px;'>
        <h1 style='font-weight: 900; font-size: 2.8em; margin: 0; color: #1e1e1e; display: flex; align-items: center; justify-content: center; gap: 15px;'>
            <span style='font-size: 1.2em;'>🚀</span> 3D Command Center
        </h1>
        <p style='color: #4b5563; font-size: 1.1em; margin-top: 10px; font-weight: 500;'>
            Automated Pipeline: Concept Image ➡️ AI Generation ➡️ Auto-Cleanup ➡️ Polished 3D Model
        </p>
    </div>
    """)
    
    with gr.Row():
        with gr.Column(scale=4):
            with gr.Group():
                gr.Markdown("### 📸 1. Input")
                input_image = gr.Image(type="filepath", label="Upload Concept Image")
            
            with gr.Group():
                gr.Markdown("### ⚙️ 2. Engine Settings")
                backend_choice = gr.Radio(
                    [
                        "HuggingFace API (TRELLIS)",
                        "HuggingFace API (Stable Fast 3D)",
                        "HuggingFace API (InstantMesh)", 
                        "Colab / Custom URL (TripoSR)",
                        "Meshy.ai API"
                    ], 
                    label="Select Backend Engine",
                    value="HuggingFace API (TRELLIS)"
                )
                
                # Dynamic Visibility Boxes based on Backend Choice
                hf_token = gr.Textbox(
                    label="🔑 HuggingFace Token", 
                    value=settings.get("hf_token", ""),
                    type="password",
                    visible=True
                )
                custom_url = gr.Textbox(
                    label="🔗 Colab Gradio URL", 
                    placeholder="e.g. https://ee6df5e0...gradio.live",
                    value=settings.get("colab_url", ""),
                    visible=False
                )
                meshy_key = gr.Textbox(
                    label="🔑 Meshy API Key", 
                    placeholder="e.g. msy_...",
                    type="password",
                    value=settings.get("meshy_key", ""),
                    visible=False
                )
                
                backend_choice.change(
                    fn=update_settings_ui,
                    inputs=[backend_choice],
                    outputs=[custom_url, hf_token, meshy_key]
                )
                
                gr.Markdown("---")
                run_cleanup = gr.Checkbox(
                    label="🪄 Run Auto-Cleanup (Metallic Materials & Decimation)", 
                    value=False,
                    info="Leave unchecked for TRELLIS, SF3D, and Meshy to preserve their beautiful colors/textures!"
                )
            
            generate_btn = gr.Button("🔨 Generate 3D Model", variant="primary", size="lg")
            status_text = gr.Textbox(label="Status Logging", interactive=False)
            
        with gr.Column(scale=5):
            with gr.Group():
                gr.Markdown("### 🎨 3. Output Gallery")
                
                history_dropdown = gr.Dropdown(
                    choices=get_history(), 
                    label="View Past Generations (History)",
                    value=get_history()[0][1] if get_history() else None
                )
                
                output_model = gr.Model3D(
                    label="Interactive 3D Viewer", 
                    value=get_history()[0][1] if get_history() else None,
                    height=500
                )
                
                output_file = gr.File(
                    label="Download Finished GLB File",
                    value=get_history()[0][1] if get_history() else None
                )
            
            history_dropdown.change(
                fn=load_history_model,
                inputs=[history_dropdown],
                outputs=[output_model, output_file]
            )

    generate_btn.click(
        fn=run_pipeline,
        inputs=[input_image, backend_choice, custom_url, hf_token, meshy_key, run_cleanup],
        outputs=[history_dropdown, output_model, output_file, status_text]
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True, allowed_paths=[OUTPUT_DIR])

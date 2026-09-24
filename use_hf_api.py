import sys
import os
import shutil
from gradio_client import Client, handle_file

def generate_3d_from_image(image_path, output_dir):
    print(f"Connecting to TRELLIS HuggingFace Space...")
    
    print(f"Uploading image {image_path} and generating 3D model...")
    print("This might take 1-3 minutes depending on server load...")
    
    try:
        # Authenticate with the user's provided token to bypass anonymous rate limits
        hf_token = "YOUR_HF_TOKEN_HERE"
        client = Client("TencentARC/InstantMesh", token=hf_token)
        
        print("1. Preprocessing image...")
        processed_image = client.predict(
            input_image=handle_file(image_path),
            do_remove_background=True,
            api_name="/preprocess"
        )
        
        print("2. Generating multi-view images...")
        mvs = client.predict(
            input_image=handle_file(processed_image),
            sample_steps=75,
            sample_seed=42,
            api_name="/generate_mvs"
        )
        
        print("3. Reconstructing 3D mesh...")
        result = client.predict(api_name="/make3d")
        
        # result is a tuple (obj_path, glb_path)
        glb_path = result[1] if isinstance(result, tuple) else result

        
        os.makedirs(output_dir, exist_ok=True)
        final_path = os.path.join(output_dir, "generated_model.glb")
        shutil.copy2(glb_path, final_path)
        
        print(f"Success! Saved 3D model to: {final_path}")
        return final_path
        
    except Exception as e:
        print(f"API Error: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python use_hf_api.py <input_image.jpg> <output_directory>")
    else:
        generate_3d_from_image(sys.argv[1], sys.argv[2])

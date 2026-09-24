import json
import os
import datetime

def update_metadata():
    output_dir = r"c:\Users\Sunu\Documents\home\zaigopc\Desktop\personal\automate\output\test_instantmesh"
    
    # 1. Create info.txt
    info_path = os.path.join(output_dir, "info.txt")
    info_content = f"""Model: iPhone 17 Pro (AI Generated)
Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Workflow: Image-to-3D (InstantMesh API) -> Blender Auto-Cleanup
Polycount: Optimized (90% Decimation)
Scale: Real-world (Height: 149.6mm)
Materials: PBR (Metallic/Roughness enhanced)
"""
    with open(info_path, "w") as f:
        f.write(info_content)
    print(f"Created {info_path}")

    # 2. Update categories.json
    cat_path = r"c:\Users\Sunu\Documents\home\zaigopc\Desktop\personal\automate\categories.json"
    if os.path.exists(cat_path):
        with open(cat_path, "r") as f:
            data = json.load(f)
            
        new_entry = {
            "name": "iPhone 17 Pro",
            "category": "Electronics",
            "type": "High-Poly Photorealistic",
            "path": output_dir,
            "pipeline": "AI Image-to-3D"
        }
        
        # Avoid duplicates
        if not any(item.get("name") == "iPhone 17 Pro" for item in data):
            data.append(new_entry)
            with open(cat_path, "w") as f:
                json.dump(data, f, indent=4)
            print("Updated categories.json")
        else:
            print("Model already exists in categories.json")

if __name__ == "__main__":
    update_metadata()

import bpy
import os
import sys

def setup_workbench_passes():
    scene = bpy.context.scene
    scene.render.resolution_x = 800
    scene.render.resolution_y = 800
    
def create_silhouette_mat():
    if "Mat_Silhouette" in bpy.data.materials:
        return bpy.data.materials["Mat_Silhouette"]
    mat = bpy.data.materials.new(name="Mat_Silhouette")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    out = nodes.new(type='ShaderNodeOutputMaterial')
    emit = nodes.new(type='ShaderNodeEmission')
    emit.inputs['Color'].default_value = (1, 1, 1, 1)
    mat.node_tree.links.new(emit.outputs[0], out.inputs[0])
    return mat

def render_pass(scene, cam, output_path, pass_type):
    scene.camera = cam
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.filepath = output_path
    
    # Store original materials and modifiers
    meshes = [obj for obj in scene.objects if obj.type == 'MESH']
    
    if pass_type == 'silhouette':
        scene.render.film_transparent = True
        mat_sil = create_silhouette_mat()
        for obj in meshes:
            if len(obj.data.materials) == 0:
                obj.data.materials.append(mat_sil)
            else:
                for i in range(len(obj.data.materials)):
                    obj.data.materials[i] = mat_sil
    
    elif pass_type == 'wireframe':
        scene.render.film_transparent = True
        # Add wireframe modifier
        for obj in meshes:
            mod = obj.modifiers.new(name="WirePass", type='WIREFRAME')
            mod.thickness = 0.005
            mod.use_replace = True
            
    elif pass_type == 'beauty':
        scene.render.film_transparent = False
        
    bpy.ops.render.render(write_still=True)
    
    # Clean up (we reload the scene anyway between runs, but let's just let it be since we do one pass loop)
    if pass_type == 'wireframe':
        for obj in meshes:
            if "WirePass" in obj.modifiers:
                obj.modifiers.remove(obj.modifiers["WirePass"])


def generate_technical_passes(glb_path, output_dir):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    if not os.path.exists(glb_path):
        print(f"Error: Could not find {glb_path}")
        return
        
    os.makedirs(output_dir, exist_ok=True)
    
    # Import the generated mesh
    bpy.ops.import_scene.gltf(filepath=glb_path)
    
    # Find the imported object
    imported_objs = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    if not imported_objs:
        print("No mesh found in GLB!")
        return
        
    # Group them
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0,0))
    root = bpy.context.active_object
    for obj in imported_objs:
        obj.parent = root
        
    # Normalize scale and location (fit into 1x1x1 box at origin)
    bpy.ops.object.select_all(action='DESELECT')
    root.select_set(True)
    for obj in imported_objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    
    # Set up a target empty for cameras
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0,0))
    target = bpy.context.active_object
    
    # Create cameras (Front, Side, Top)
    cameras = []
    positions = {
        'front': (0, -2, 0),
        'side': (2, 0, 0),
        'top': (0, 0, 2)
    }
    
    scene = bpy.context.scene
    scene.render.resolution_x = 800
    scene.render.resolution_y = 800
    
    for name, loc in positions.items():
        cam_data = bpy.data.cameras.new(name)
        cam = bpy.data.objects.new(name, cam_data)
        bpy.context.collection.objects.link(cam)
        cam.location = loc
        
        const = cam.constraints.new(type='TRACK_TO')
        const.target = target
        const.track_axis = 'TRACK_NEGATIVE_Z'
        const.up_axis = 'UP_Y'
        
        cameras.append((name, cam))
        
    # Render passes
    passes = ['silhouette', 'wireframe', 'beauty']
    
    for cam_name, cam in cameras:
        for p_type in passes:
            out_path = os.path.join(output_dir, f"{cam_name}_{p_type}.png")
            print(f"Rendering {cam_name} {p_type} pass...")
            render_pass(scene, cam, out_path, p_type)
            
    print("Technical passes generated successfully!")

if __name__ == "__main__":
    import sys
    # args after '--' are passed to script
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
        if len(argv) >= 2:
            generate_technical_passes(argv[0], argv[1])
        else:
            print("Usage: blender --background --python script.py -- <glb_path> <output_dir>")

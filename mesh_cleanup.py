import bpy
import mathutils
import sys
import os

def clean_and_optimize_mesh(input_glb, output_glb):
    print(f"Starting cleanup for: {input_glb}")
    
    # 1. Clear scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    # 2. Import the raw AI-generated GLB
    bpy.ops.import_scene.gltf(filepath=input_glb)
    
    # Get imported meshes
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    if not meshes:
        print("Error: No mesh found in the imported file.")
        return
        
    # Assume the first mesh is our primary object (AI models usually output a single mesh)
    target = meshes[0]
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    
    # 3. Normalize Scale and Location
    # Calculate bounding box dimensions
    bbox_corners = [target.matrix_world @ mathutils.Vector(corner) for corner in target.bound_box]
    min_z = min([c.z for c in bbox_corners])
    max_z = max([c.z for c in bbox_corners])
    min_x = min([c.x for c in bbox_corners])
    max_x = max([c.x for c in bbox_corners])
    min_y = min([c.y for c in bbox_corners])
    max_y = max([c.y for c in bbox_corners])
    
    current_height = max_z - min_z
    target_height = 0.1496  # iPhone 17 Pro height in meters (approx 15cm)
    
    if current_height > 0:
        scale_factor = target_height / current_height
        target.scale = (scale_factor, scale_factor, scale_factor)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
    # Center object at world origin (resting on the floor Z=0)
    # Recalculate bounding box after scale
    bbox_corners = [target.matrix_world @ mathutils.Vector(corner) for corner in target.bound_box]
    min_z = min([c.z for c in bbox_corners])
    center_x = sum([c.x for c in bbox_corners]) / 8.0
    center_y = sum([c.y for c in bbox_corners]) / 8.0
    
    target.location.x -= center_x
    target.location.y -= center_y
    target.location.z -= min_z
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    
    print("Scale and location normalized.")

    # 4. Topology Cleanup (Decimation)
    print("Decimating dense triangle mesh...")
    decimate_mod = target.modifiers.new("Optimize", type='DECIMATE')
    decimate_mod.decimate_type = 'COLLAPSE'
    # Reduce to 10% of original polycount to remove noise but keep shape
    decimate_mod.ratio = 0.1 
    bpy.ops.object.modifier_apply(modifier="Optimize")
    
    # 5. Smoothing
    print("Applying smooth shading...")
    for poly in target.data.polygons:
        poly.use_smooth = True
    
    # Add Edge Split to keep sharp corners sharp while smoothing faces
    edge_split = target.modifiers.new("SharpEdges", type='EDGE_SPLIT')
    edge_split.split_angle = 0.523599  # 30 degrees
    bpy.ops.object.modifier_apply(modifier="SharpEdges")
    
    # 6. Material Enhancement
    # AI models usually output flat diffuse colors (vertex colors or texture). 
    # Let's make it look like a sleek electronic device (shiny, metallic).
    if target.data.materials:
        mat = target.data.materials[0]
        if mat.use_nodes:
            nodes = mat.node_tree.nodes
            for node in nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    # Make it look like metal/glass
                    node.inputs['Metallic'].default_value = 0.6
                    node.inputs['Roughness'].default_value = 0.25
                    print("Enhanced material properties (Metallic/Roughness).")
                    break

    # 7. Export the polished GLB
    print(f"Exporting polished model to: {output_glb}")
    bpy.ops.export_scene.gltf(
        filepath=output_glb,
        export_format='GLB',
        use_selection=True,
        export_apply=True
    )
    print("Cleanup and export complete!")

if __name__ == "__main__":
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1:]
        if len(argv) >= 2:
            clean_and_optimize_mesh(argv[0], argv[1])
        else:
            print("Usage: blender --background --python mesh_cleanup.py -- <input.glb> <output.glb>")

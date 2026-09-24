import bpy
import math
import sys
import os

def fix_camera_lens(input_glb, output_glb):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=input_glb)
    
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    if not meshes:
        return
    main_cam = meshes[0]
    
    # 1. Calculate the bounding box to find the lumpy lens
    bbox = [main_cam.matrix_world @ mathutils.Vector(corner) for corner in main_cam.bound_box]
    min_x, max_x = min([c.x for c in bbox]), max([c.x for c in bbox])
    min_y, max_y = min([c.y for c in bbox]), max([c.y for c in bbox])
    min_z, max_z = min([c.z for c in bbox]), max([c.z for c in bbox])
    
    width = max_x - min_x
    height = max_z - min_z
    depth = max_y - min_y
    
    center_x = (max_x + min_x) / 2.0
    center_z = (max_z + min_z) / 2.0 - (height * 0.1) # Lens is usually slightly below center
    
    # 2. Add a mathematically perfect Cylinder to replace the lumpy lens
    lens_radius = width * 0.35  # Lens is about 70% of the camera body width
    lens_depth = depth * 0.45   # Lens sticks out about 45% of the total depth
    
    # Create the outer lens barrel
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=64, 
        radius=lens_radius, 
        depth=lens_depth, 
        location=(center_x, min_y + (lens_depth / 2.0) + 0.005, center_z),
        rotation=(math.pi / 2.0, 0, 0)
    )
    lens_barrel = bpy.context.active_object
    lens_barrel.name = "Perfect_Lens_Barrel"
    bpy.ops.object.shade_smooth()
    
    # Create the inner glass lens
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=64, 
        radius=lens_radius * 0.85, 
        depth=0.002, 
        location=(center_x, min_y - 0.001, center_z),
        rotation=(math.pi / 2.0, 0, 0)
    )
    lens_glass = bpy.context.active_object
    lens_glass.name = "Perfect_Lens_Glass"
    bpy.ops.object.shade_smooth()
    
    # 3. Apply Materials
    mat_barrel = bpy.data.materials.new(name="Mat_LensBarrel")
    mat_barrel.use_nodes = True
    bsdf = mat_barrel.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.05, 0.05, 0.05, 1)
        bsdf.inputs['Metallic'].default_value = 0.9
        bsdf.inputs['Roughness'].default_value = 0.2
    lens_barrel.data.materials.append(mat_barrel)
    
    mat_glass = bpy.data.materials.new(name="Mat_LensGlass")
    mat_glass.use_nodes = True
    bsdf_glass = mat_glass.node_tree.nodes.get('Principled BSDF')
    if bsdf_glass:
        bsdf_glass.inputs['Base Color'].default_value = (0.01, 0.01, 0.02, 1)
        bsdf_glass.inputs['Metallic'].default_value = 0.1
        bsdf_glass.inputs['Roughness'].default_value = 0.05
        # fake glass reflection
    lens_glass.data.materials.append(mat_glass)
    
    # 4. Smooth out the rest of the camera body heavily
    bpy.context.view_layer.objects.active = main_cam
    mod = main_cam.modifiers.new(name="Smooth", type='SMOOTH')
    mod.factor = 1.0
    mod.iterations = 15
    bpy.ops.object.modifier_apply(modifier="Smooth")
    
    # 5. Export the Perfected GLB
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=output_glb, export_format='GLB', use_selection=True)
    print("Perfected model exported.")

if __name__ == "__main__":
    import mathutils
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
        fix_camera_lens(args[0], args[1])

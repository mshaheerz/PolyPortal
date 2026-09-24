"""
Test Turntable Skill on HP Tactical Pistol
Uses the turntable skill workflow from .agents/skills/turntable/SKILL.md:
- Loads the finished pistol model
- Creates TurntableTarget empty and TurntableCamera with TRACK_TO constraint
- Keyframes a smooth 360-degree orbit (36 frames, 10 degrees per frame)
- Renders turntable sequence to output/2026-09-21_hp_tactical_pistol/turntable/
"""

import bpy
import math
from mathutils import Vector
import os

def run_turntable():
    # 1. Clear scene and import model
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if not bpy.data.scenes:
        bpy.data.scenes.new("Scene")
        
    model_path = r"c:\Users\Sunu\Documents\home\zaigopc\Desktop\personal\automate\output\2026-09-21_hp_tactical_pistol\hp_tactical_pistol.glb"
    bpy.ops.import_scene.gltf(filepath=model_path)
    
    # 2. Calculate center and bounding box
    mesh_objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    all_verts = []
    for o in mesh_objs:
        for c in o.bound_box:
            all_verts.append(o.matrix_world @ Vector(c))
            
    center = sum(all_verts, Vector()) / len(all_verts)
    
    # 3. Create Turntable Target Empty
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=center)
    target = bpy.context.active_object
    target.name = "TurntableTarget"
    
    # 4. Create Turntable Camera
    cam_dist = 0.42
    cam_height = center.z + 0.08
    bpy.ops.object.camera_add(location=(center.x, center.y - cam_dist, cam_height))
    cam = bpy.context.active_object
    cam.name = "TurntableCamera"
    cam.data.lens = 65
    bpy.context.scene.camera = cam
    
    track = cam.constraints.new(type='TRACK_TO')
    track.target = target
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis = 'UP_Y'
    
    # Parent camera to target empty for orbiting
    bpy.ops.object.select_all(action='DESELECT')
    cam.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
    
    # 5. Animate 360 degree rotation over 36 frames
    TOTAL_FRAMES = 36
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = TOTAL_FRAMES
    scene.render.fps = 24
    
    target.rotation_euler = (0, 0, 0)
    target.keyframe_insert(data_path='rotation_euler', frame=1)
    target.rotation_euler = (0, 0, math.radians(360))
    target.keyframe_insert(data_path='rotation_euler', frame=TOTAL_FRAMES + 1)
    
    # Set linear interpolation
    if target.animation_data and target.animation_data.action:
        action = target.animation_data.action
        # Support both classic fcurves and layered actions
        fcurves = []
        if hasattr(action, 'fcurves'):
            fcurves = action.fcurves
        elif hasattr(action, 'layers') and action.layers:
            for strip in action.layers[0].strips:
                for cb in strip.channelbags:
                    fcurves.extend(cb.fcurves)
        for fc in fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
                
    # 6. Studio Lighting from skill guide
    # Golden Key
    bpy.ops.object.light_add(type='AREA', location=(-0.5, 0.3, 0.6))
    key = bpy.context.active_object
    key.name = "GoldenKey"
    key.data.energy = 45.0
    key.data.size = 0.8
    key.data.color = (1.0, 0.96, 0.90)
    
    # Cool Fill
    bpy.ops.object.light_add(type='AREA', location=(0.6, -0.3, 0.4))
    fill = bpy.context.active_object
    fill.name = "CoolFill"
    fill.data.energy = 22.0
    fill.data.size = 1.0
    fill.data.color = (0.85, 0.92, 1.0)
    
    # Sharp Rim
    bpy.ops.object.light_add(type='AREA', location=(0.3, -0.5, 0.55))
    rim = bpy.context.active_object
    rim.name = "WarmRim"
    rim.data.energy = 65.0
    rim.data.size = 0.1
    rim.data.size_y = 1.2
    
    # Neutral Studio World
    world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs['Color'].default_value = (0.75, 0.78, 0.82, 1.0)
        bg.inputs['Strength'].default_value = 0.4
        
    # Reflective Tabletop
    bpy.ops.mesh.primitive_plane_add(size=6.0, location=(0, 0, center.z - 0.095))
    floor = bpy.context.active_object
    mat_floor = bpy.data.materials.new(name="Mat_Floor")
    mat_floor.use_nodes = True
    bsdf = mat_floor.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.20, 0.22, 0.25, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.25
    floor.data.materials.append(mat_floor)
    
    # 7. Render Settings
    out_dir = r"c:\Users\Sunu\Documents\home\zaigopc\Desktop\personal\automate\output\2026-09-21_hp_tactical_pistol\turntable"
    os.makedirs(out_dir, exist_ok=True)
    
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'RenderSettings') and 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    scene.render.resolution_x = 800
    scene.render.resolution_y = 800
    scene.render.filepath = os.path.join(out_dir, "frame_")
    
    print(f"Rendering 36-frame turntable to {out_dir}...")
    bpy.ops.render.render(animation=True)
    print("[SUCCESS] Turntable animation rendered successfully!")

if __name__ == "__main__":
    run_turntable()

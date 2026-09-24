import bpy
import bmesh
import math
import mathutils
import os

# Clean scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

for block in bpy.data.materials:
    bpy.data.materials.remove(block)

# ----------------------------------------------------
# 1. PBR Shaders
# ----------------------------------------------------
def make_mat(name, color, metallic=0.0, roughness=0.35, bump=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    prin = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(prin.outputs['BSDF'], out.inputs['Surface'])
    prin.inputs['Base Color'].default_value = (*color, 1.0)
    prin.inputs['Metallic'].default_value = metallic
    prin.inputs['Roughness'].default_value = roughness
    if bump > 0:
        noise = nt.nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 32.0
        noise.inputs['Detail'].default_value = 8.0
        b_node = nt.nodes.new('ShaderNodeBump')
        b_node.inputs['Strength'].default_value = bump
        nt.links.new(noise.outputs['Fac'], b_node.inputs['Height'])
        nt.links.new(b_node.outputs['Normal'], prin.inputs['Normal'])
    return mat

slide_mat     = make_mat("Slide_Nitride", [0.06, 0.06, 0.07], metallic=0.92, roughness=0.22, bump=0.01)
barrel_mat    = make_mat("Barrel_Steel",  [0.03, 0.03, 0.03], metallic=0.96, roughness=0.18)
frame_mat     = make_mat("Polymer_Frame", [0.08, 0.08, 0.09], metallic=0.05, roughness=0.55, bump=0.035)
grip_mat      = make_mat("Stipple_Grip",  [0.06, 0.06, 0.07], metallic=0.04, roughness=0.68, bump=0.08)
sight_dot_mat = make_mat("Sight_Dot",     [0.98, 0.98, 0.98], metallic=0.0, roughness=0.1)

# ----------------------------------------------------
# 2. Precision Machined Steel Slide
# ----------------------------------------------------
bm_slide = bmesh.new()
bmesh.ops.create_cube(bm_slide, size=1.0)
# Width 0.27, Length 1.84, Height 0.32
bmesh.ops.scale(bm_slide, vec=(0.27, 1.84, 0.32), verts=bm_slide.verts)
bmesh.ops.translate(bm_slide, vec=(0, 0.0, 0.70), verts=bm_slide.verts)

# 45-degree top edge chamfers
top_edges = [e for e in bm_slide.edges if all(v.co.z > 0.84 for v in e.verts) and abs(e.verts[0].co.x - e.verts[1].co.x) < 0.001]
if top_edges:
    bmesh.ops.bevel(bm_slide, geom=top_edges, offset=0.034, segments=2, profile=0.5)

# Front tactical bull-nose taper
for v in bm_slide.verts:
    if v.co.y < -0.76 and v.co.z < 0.66:
        v.co.y += 0.12 * (0.66 - v.co.z) / 0.16

mesh_slide = bpy.data.meshes.new('SlideMesh')
bm_slide.to_mesh(mesh_slide)
bm_slide.free()

slide_obj = bpy.data.objects.new('Pistol_Slide', mesh_slide)
bpy.context.collection.objects.link(slide_obj)
slide_bev = slide_obj.modifiers.new('Bevel', 'BEVEL')
slide_bev.limit_method = 'ANGLE'
slide_bev.angle_limit = math.radians(35)
slide_bev.width = 0.006
slide_bev.segments = 2
bpy.context.view_layer.objects.active = slide_obj
bpy.ops.object.shade_smooth()
slide_obj.data.materials.append(slide_mat)

# Recessed Slide Serrations (Rear & Front)
for side_x in [-0.138, 0.138]:
    for y_pos in [0.44, 0.52, 0.60, 0.68, 0.76, -0.42, -0.50, -0.58]:
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(side_x, y_pos, 0.73))
        cut = bpy.context.active_object
        cut.name = "Serration"
        cut.scale = (0.012, 0.032, 0.18)
        cut.rotation_euler = (0, 0, math.radians(14 if side_x > 0 else -14))
        bpy.ops.object.transform_apply(scale=True, rotation=True)
        bpy.ops.object.shade_smooth()
        cut.data.materials.append(slide_mat)

# Ejection Port
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.09, 0.10, 0.81))
eject = bpy.context.active_object
eject.name = "Ejection_Port"
eject.scale = (0.12, 0.38, 0.12)
bpy.ops.object.transform_apply(scale=True)
bpy.ops.object.shade_smooth()
eject.data.materials.append(barrel_mat)

# ----------------------------------------------------
# 3. Match-Grade Threaded Barrel
# ----------------------------------------------------
bpy.ops.mesh.primitive_cylinder_add(radius=0.068, depth=0.34, location=(0, -0.98, 0.68), vertices=32)
barrel = bpy.context.active_object; barrel.name = "Barrel"
barrel.rotation_euler = (math.radians(90), 0, 0)
bpy.ops.object.transform_apply(rotation=True)
bpy.ops.object.shade_smooth()
barrel.data.materials.append(barrel_mat)

# Knurled thread protector cap
bpy.ops.mesh.primitive_cylinder_add(radius=0.082, depth=0.12, location=(0, -1.06, 0.68), vertices=32)
cap = bpy.context.active_object; cap.name = "Thread_Cap"
cap.rotation_euler = (math.radians(90), 0, 0)
bpy.ops.object.transform_apply(rotation=True)
bpy.ops.object.shade_smooth()
cap.data.materials.append(barrel_mat)

# Hollow muzzle bore
bpy.ops.mesh.primitive_cylinder_add(radius=0.046, depth=0.08, location=(0, -1.11, 0.68), vertices=24)
bore = bpy.context.active_object; bore.name = "Bore"
bore.rotation_euler = (math.radians(90), 0, 0)
bpy.ops.object.transform_apply(rotation=True)
bore.data.materials.append(make_mat("Bore_Dark", [0.01, 0.01, 0.01], roughness=0.9))

# ----------------------------------------------------
# 4. Polymer Lower Receiver & Seamless Ergonomic Grip
# ----------------------------------------------------
# Dust Cover & Accessory Rail
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, -0.42, 0.46))
dust_cover = bpy.context.active_object
dust_cover.name = "Frame_DustCover"
dust_cover.scale = (0.26, 0.98, 0.17)
bpy.ops.object.transform_apply(scale=True)
dc_bev = dust_cover.modifiers.new('Bevel', 'BEVEL')
dc_bev.limit_method = 'ANGLE'
dc_bev.angle_limit = math.radians(35)
dc_bev.width = 0.018
dc_bev.segments = 3
bpy.ops.object.shade_smooth()
dust_cover.data.materials.append(frame_mat)

# Picatinny rail cross-slots
for slot_y in [-0.25, -0.45, -0.65]:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, slot_y, 0.365))
    slot = bpy.context.active_object
    slot.name = "Rail_Slot"
    slot.scale = (0.24, 0.05, 0.025)
    bpy.ops.object.transform_apply(scale=True)
    slot.data.materials.append(frame_mat)

# Ergonomic Grip Body (Smooth quads with bevel & subsurf)
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0.22, 0.12))
grip = bpy.context.active_object
grip.name = "Grip_Body"
grip.scale = (0.26, 0.46, 0.82)
grip.rotation_euler = (math.radians(-18), 0, 0)
bpy.ops.object.transform_apply(scale=True, rotation=True)
grip_bev = grip.modifiers.new('Bevel', 'BEVEL')
grip_bev.limit_method = 'ANGLE'
grip_bev.angle_limit = math.radians(35)
grip_bev.width = 0.04
grip_bev.segments = 3
grip_sub = grip.modifiers.new('Subsurf', 'SUBSURF')
grip_sub.levels = 2
bpy.ops.object.shade_smooth()
grip.data.materials.append(frame_mat)

# Stippled Texture Panels on Grip (Left & Right)
for p_side in [-0.134, 0.134]:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(p_side, 0.23, 0.12))
    panel = bpy.context.active_object
    panel.name = f"Stipple_Panel_{p_side}"
    panel.scale = (0.010, 0.34, 0.58)
    panel.rotation_euler = (math.radians(-18), 0, 0)
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    p_bev = panel.modifiers.new('Bevel', 'BEVEL')
    p_bev.width = 0.02
    p_bev.segments = 2
    bpy.ops.object.shade_smooth()
    panel.data.materials.append(grip_mat)

# Beavertail (Smooth curved rear extension)
bpy.ops.mesh.primitive_cone_add(radius1=0.11, radius2=0.03, depth=0.30, location=(0, 0.65, 0.52), vertices=24)
btail = bpy.context.active_object
btail.name = "Beaver_Tail"
btail.rotation_euler = (math.radians(-65), 0, 0)
bpy.ops.object.transform_apply(rotation=True)
btail.modifiers.new('Subsurf', 'SUBSURF')
btail.modifiers['Subsurf'].levels = 2
bpy.ops.object.shade_smooth()
btail.data.materials.append(frame_mat)

# Tactical Combat Trigger Guard (Molded thick loop with flat front finger rest)
# Front vertical wall of guard
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, -0.34, 0.28))
guard_front = bpy.context.active_object
guard_front.name = "Guard_Front"
guard_front.scale = (0.10, 0.06, 0.24)
bpy.ops.object.transform_apply(scale=True)
g_bev1 = guard_front.modifiers.new('Bevel', 'BEVEL')
g_bev1.width = 0.015
bpy.ops.object.shade_smooth()
guard_front.data.materials.append(frame_mat)

# Bottom horizontal floor of guard
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, -0.18, 0.165))
guard_bot = bpy.context.active_object
guard_bot.name = "Guard_Bottom"
guard_bot.scale = (0.10, 0.32, 0.05)
bpy.ops.object.transform_apply(scale=True)
g_bev2 = guard_bot.modifiers.new('Bevel', 'BEVEL')
g_bev2.width = 0.015
bpy.ops.object.shade_smooth()
guard_bot.data.materials.append(frame_mat)

# Rear transition into grip undercut
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, -0.04, 0.23))
guard_rear = bpy.context.active_object
guard_rear.name = "Guard_Rear"
guard_rear.scale = (0.10, 0.06, 0.14)
guard_rear.rotation_euler = (math.radians(-25), 0, 0)
bpy.ops.object.transform_apply(scale=True, rotation=True)
g_bev3 = guard_rear.modifiers.new('Bevel', 'BEVEL')
g_bev3.width = 0.015
bpy.ops.object.shade_smooth()
guard_rear.data.materials.append(frame_mat)

# Combat Trigger with Safety Blade
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, -0.13, 0.31))
trigger = bpy.context.active_object
trigger.name = "Combat_Trigger"
trigger.scale = (0.045, 0.08, 0.20)
trigger.rotation_euler = (math.radians(-16), 0, 0)
bpy.ops.object.transform_apply(scale=True, rotation=True)
trig_bev = trigger.modifiers.new('Bevel', 'BEVEL')
trig_bev.width = 0.012
trigger.modifiers.new('Subsurf', 'SUBSURF')
bpy.ops.object.shade_smooth()
trigger.data.materials.append(slide_mat)

# Magazine Basepad Plate
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0.35, -0.28))
magpad = bpy.context.active_object
magpad.name = "Mag_Basepad"
magpad.scale = (0.28, 0.52, 0.08)
magpad.rotation_euler = (math.radians(-18), 0, 0)
bpy.ops.object.transform_apply(scale=True, rotation=True)
mag_bev = magpad.modifiers.new('Bevel', 'BEVEL')
mag_bev.width = 0.02
magpad.modifiers.new('Subsurf', 'SUBSURF')
bpy.ops.object.shade_smooth()
magpad.data.materials.append(frame_mat)

# ----------------------------------------------------
# 5. Low-Profile Dovetail Combat Sights
# ----------------------------------------------------
# Front Sight Blade
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, -0.78, 0.89))
front_sight = bpy.context.active_object
front_sight.name = "Sight_Front"
front_sight.scale = (0.042, 0.09, 0.065)
bpy.ops.object.transform_apply(scale=True)
fs_bev = front_sight.modifiers.new('Bevel', 'BEVEL')
fs_bev.width = 0.008
bpy.ops.object.shade_smooth()
front_sight.data.materials.append(slide_mat)

# Front sight white combat dot
bpy.ops.mesh.primitive_cylinder_add(radius=0.011, depth=0.01, location=(0, -0.73, 0.89), vertices=16)
dot_f = bpy.context.active_object
dot_f.rotation_euler = (math.radians(90), 0, 0)
bpy.ops.object.transform_apply(rotation=True)
dot_f.data.materials.append(sight_dot_mat)

# Rear Combat U-Notch Sight
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0.78, 0.895))
rear_sight = bpy.context.active_object
rear_sight.name = "Sight_Rear"
rear_sight.scale = (0.15, 0.09, 0.075)
bpy.ops.object.transform_apply(scale=True)
rs_bev = rear_sight.modifiers.new('Bevel', 'BEVEL')
rs_bev.width = 0.008
bpy.ops.object.shade_smooth()
rear_sight.data.materials.append(slide_mat)

# Rear sight dual white dots
for dot_x in [-0.048, 0.048]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.010, depth=0.01, location=(dot_x, 0.73, 0.895), vertices=16)
    dot_r = bpy.context.active_object
    dot_r.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.object.transform_apply(rotation=True)
    dot_r.data.materials.append(sight_dot_mat)

# ----------------------------------------------------
# 6. Studio Lighting & Dynamic Product Camera
# ----------------------------------------------------
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = 1080
scene.render.resolution_y = 1080

# Studio World (Soft dark-neutral gradient)
world = bpy.data.worlds.new("StudioWorld")
scene.world = world
world.use_nodes = True
nt_w = world.node_tree
nt_w.nodes.clear()
out_w = nt_w.nodes.new('ShaderNodeOutputWorld')
bg_w = nt_w.nodes.new('ShaderNodeBackground')
bg_w.inputs['Color'].default_value = (0.07, 0.07, 0.08, 1.0)
bg_w.inputs['Strength'].default_value = 0.7
nt_w.links.new(bg_w.outputs['Background'], out_w.inputs['Surface'])

# Studio Area Lights
# Key light (Angled from front-top catching the top slide bevels)
bpy.ops.object.light_add(type='AREA', location=(-2.8, -2.8, 3.5))
key = bpy.context.active_object
key.data.energy = 700
key.data.size = 2.2
key.data.color = (1.0, 0.98, 0.95)

# Fill light (Soft from right side)
bpy.ops.object.light_add(type='AREA', location=(3.5, 1.2, 2.0))
fill = bpy.context.active_object
fill.data.energy = 220
fill.data.size = 4.0
fill.data.color = (0.75, 0.82, 0.95)

# Back Rim light (Outlines the slide top, sights, and rear backstrap)
bpy.ops.object.light_add(type='AREA', location=(0.0, 3.2, 2.8))
rim = bpy.context.active_object
rim.data.energy = 450
rim.data.size = 1.8

# Camera setup: 65mm lens, framed to show the whole pistol cleanly
cam_data = bpy.data.cameras.new("StudioCamera")
cam_data.lens = 65
cam_obj = bpy.data.objects.new("Camera", cam_data)
bpy.context.collection.objects.link(cam_obj)
scene.camera = cam_obj

# Camera 1: Perspective 3/4 beauty view (showing front muzzle, slide chamfer, and grip)
target_center = mathutils.Vector((0.0, -0.05, 0.35))
cam_obj.location = (2.8, -3.2, 2.0)
direction = target_center - cam_obj.location
cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

out_dir = r"C:\Users\Sunu\Documents\home\zaigopc\Desktop\personal\automate\output\2026-09-21_hp_tactical_pistol"
os.makedirs(out_dir, exist_ok=True)
scene.render.filepath = os.path.join(out_dir, "preview_perspective.png")
print("Rendering perspective view...")
bpy.ops.render.render(write_still=True)

# Camera 2: Side Profile view (well framed, no clipping)
cam_obj.location = (4.5, -0.05, 0.35)
direction = target_center - cam_obj.location
cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = os.path.join(out_dir, "preview_side.png")
print("Rendering side view...")
bpy.ops.render.render(write_still=True)

# Export all formats
bpy.ops.object.select_all(action='DESELECT')
for o in scene.objects:
    if o.type == 'MESH':
        o.select_set(True)
active_m = next((o for o in scene.objects if o.type == 'MESH'), None)
bpy.context.view_layer.objects.active = active_m

bpy.ops.export_scene.gltf(filepath=os.path.join(out_dir, "hp_tactical_pistol.glb"), use_selection=True)
bpy.ops.export_scene.fbx(filepath=os.path.join(out_dir, "hp_tactical_pistol.fbx"), use_selection=True)
bpy.ops.wm.obj_export(filepath=os.path.join(out_dir, "hp_tactical_pistol.obj"), export_selected_objects=True)

print("[SUCCESS] Overhauled Pistol V2 rendered and exported successfully!")

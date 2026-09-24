"""
Blender 5.2 Automated Model Generator
Runs headless: blender --background --python generate_model.py -- --category_file ... --output_dir ...
"""

import bpy
import sys
import os
import json
import math
import random

# ─────────────────────────────────────────
# Parse arguments passed after "--"
# ─────────────────────────────────────────
def get_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--category_file", required=True)
    parser.add_argument("--output_dir",    required=True)
    parser.add_argument("--model_index",   type=int, default=0)
    parser.add_argument("--resolution",    type=int, default=1080)
    parser.add_argument("--samples",       type=int, default=64)
    return parser.parse_args(argv)

# ─────────────────────────────────────────
# Scene Setup
# ─────────────────────────────────────────
def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        bpy.data.materials.remove(block)

def setup_render(resolution, samples, output_path, render_mode='eevee'):
    scene = bpy.context.scene
    if render_mode == 'cycles':
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        # Use GPU if available, fallback to CPU
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'CUDA'
        try:
            prefs.get_devices()
            scene.cycles.device = 'GPU'
        except Exception:
            scene.cycles.device = 'CPU'
    else:
        scene.render.engine = 'BLENDER_EEVEE'
        scene.eevee.taa_render_samples = samples
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = output_path

def add_world_background(color=(0.08, 0.08, 0.12, 1.0)):
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = color
        bg.inputs[1].default_value = 0.3

def add_lights():
    # Key light (sun)
    bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
    sun = bpy.context.active_object
    sun.data.energy = 3.0
    sun.data.color = (1.0, 0.95, 0.85)
    sun.rotation_euler = (math.radians(45), math.radians(10), math.radians(45))

    # Fill light (area)
    bpy.ops.object.light_add(type='AREA', location=(-3, 3, 5))
    fill = bpy.context.active_object
    fill.data.energy = 200
    fill.data.size = 4
    fill.data.color = (0.6, 0.7, 1.0)

def add_camera(location=(5, -5, 4), look_at=(0, 0, 0.5)):
    bpy.ops.object.camera_add(location=location)
    cam = bpy.context.active_object
    bpy.context.scene.camera = cam

    # Point camera at subject
    direction = (
        look_at[0] - location[0],
        look_at[1] - location[1],
        look_at[2] - location[2]
    )
    rot_quat = bpy.context.object.matrix_world.to_quaternion()
    import mathutils
    track = mathutils.Vector(direction).normalized()
    cam.rotation_mode = 'QUATERNION'
    # Simple look-at via constraint
    constraint = cam.constraints.new(type='TRACK_TO')
    # Use an empty as target
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=look_at)
    target = bpy.context.active_object
    target.name = "CameraTarget"
    constraint.target = target
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'
    return cam

# ─────────────────────────────────────────
# Material Helpers
# ─────────────────────────────────────────
def make_material(name, color, metallic=0.0, roughness=0.6, emission=None):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output   = nodes.new('ShaderNodeOutputMaterial')
    principled = nodes.new('ShaderNodeBsdfPrincipled')
    links.new(principled.outputs['BSDF'], output.inputs['Surface'])

    principled.inputs['Base Color'].default_value    = (*color, 1.0)
    principled.inputs['Metallic'].default_value      = metallic
    principled.inputs['Roughness'].default_value     = roughness

    if emission:
        principled.inputs['Emission Color'].default_value  = (*emission, 1.0)
        principled.inputs['Emission Strength'].default_value = 2.0

    return mat

def assign_material(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

# ─────────────────────────────────────────
# Model Generators
# ─────────────────────────────────────────

def make_low_poly_oak_tree(data):
    color_trunk  = data.get("color_trunk",  [0.25, 0.15, 0.05])
    color_foliage = data.get("color_foliage", [0.1, 0.45, 0.1])

    # Trunk
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.12, depth=1.4, location=(0, 0, 0.7),
        vertices=6
    )
    trunk = bpy.context.active_object
    trunk.name = "Trunk"
    assign_material(trunk, make_material("Trunk_Mat", color_trunk, roughness=0.9))

    # Foliage — 3 spheres offset to form a canopy
    foliage_mat = make_material("Foliage_Mat", color_foliage, roughness=0.8)
    offsets = [(0,0,2.0), (0.3,0.2,1.6), (-0.3,-0.1,1.7)]
    for i, (x, y, z) in enumerate(offsets):
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=1, radius=0.7 - i*0.05,
            location=(x, y, z)
        )
        leaf = bpy.context.active_object
        leaf.name = f"Foliage_{i}"
        assign_material(leaf, foliage_mat)

def make_sci_fi_crate(data):
    color_base   = data.get("color_base",   [0.15, 0.2, 0.25])
    color_detail = data.get("color_detail",  [0.8, 0.5, 0.1])

    # Main box
    bpy.ops.mesh.primitive_cube_add(size=1.4, location=(0, 0, 0.7))
    box = bpy.context.active_object
    box.name = "Crate_Body"
    # Bevel for panel look
    bpy.ops.object.modifier_add(type='BEVEL')
    box.modifiers["Bevel"].width = 0.04
    box.modifiers["Bevel"].segments = 2
    bpy.ops.object.modifier_apply(modifier="Bevel")
    assign_material(box, make_material("Crate_Mat", color_base, metallic=0.8, roughness=0.4))

    # Corner bolts (small cubes)
    bolt_mat = make_material("Bolt_Mat", color_detail, metallic=1.0, roughness=0.3)
    corners = [(0.6, 0.6), (0.6, -0.6), (-0.6, 0.6), (-0.6, -0.6)]
    for cx, cy in corners:
        bpy.ops.mesh.primitive_cube_add(size=0.12, location=(cx, cy, 1.3))
        bolt = bpy.context.active_object
        bolt.name = "Bolt"
        assign_material(bolt, bolt_mat)

    # Warning stripe on front
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.72, 0.7))
    stripe = bpy.context.active_object
    stripe.scale = (0.9, 0.01, 0.15)
    bpy.ops.object.transform_apply(scale=True)
    stripe.name = "Warning_Stripe"
    assign_material(stripe, make_material("Stripe_Mat", color_detail, roughness=0.5))

def make_medieval_barrel(data):
    color_wood  = data.get("color_wood",  [0.35, 0.2, 0.08])
    color_metal = data.get("color_metal", [0.3, 0.3, 0.3])

    # Body — cylinder with taper
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.45, depth=0.9, location=(0, 0, 0.45),
        vertices=12
    )
    body = bpy.context.active_object
    body.name = "Barrel_Body"
    # Subtle bulge via proportional edit not possible headless; use cast modifier
    bpy.ops.object.modifier_add(type='CAST')
    body.modifiers["Cast"].factor = 0.25
    bpy.ops.object.modifier_apply(modifier="Cast")
    assign_material(body, make_material("Wood_Mat", color_wood, roughness=0.95))

    # Metal bands (3 flat cylinders)
    band_mat = make_material("Band_Mat", color_metal, metallic=0.9, roughness=0.5)
    for z in [0.15, 0.45, 0.75]:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.47, depth=0.04, location=(0, 0, z),
            vertices=12
        )
        band = bpy.context.active_object
        band.name = f"Band_{z}"
        assign_material(band, band_mat)

def make_simple_rock(data):
    color_stone = data.get("color_stone", [0.4, 0.38, 0.35])

    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.8, location=(0, 0, 0.5))
    rock = bpy.context.active_object
    rock.name = "Rock"

    # Random squash for natural look
    rock.scale = (1.0, 0.75, 0.6)
    bpy.ops.object.transform_apply(scale=True)

    # Displace slightly for rocky feel
    bpy.ops.object.modifier_add(type='DISPLACE')
    tex = bpy.data.textures.new("RockTex", type='VORONOI')
    rock.modifiers["Displace"].texture = tex
    rock.modifiers["Displace"].strength = 0.15
    bpy.ops.object.modifier_apply(modifier="Displace")

    assign_material(rock, make_material("Stone_Mat", color_stone, roughness=0.95))

def make_wooden_chest(data):
    color_wood  = data.get("color_wood",  [0.3, 0.18, 0.07])
    color_metal = data.get("color_metal", [0.8, 0.6, 0.1])

    wood_mat  = make_material("ChestWood_Mat",  color_wood,  roughness=0.85)
    metal_mat = make_material("ChestMetal_Mat", color_metal, metallic=0.9, roughness=0.3)

    # Base box
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.35))
    base = bpy.context.active_object
    base.scale = (1.2, 0.7, 0.6)
    bpy.ops.object.transform_apply(scale=True)
    base.name = "Chest_Base"
    assign_material(base, wood_mat)

    # Lid (slightly taller, on top)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.82))
    lid = bpy.context.active_object
    lid.scale = (1.2, 0.7, 0.25)
    bpy.ops.object.transform_apply(scale=True)
    lid.name = "Chest_Lid"
    assign_material(lid, wood_mat)

    # Front latch
    bpy.ops.mesh.primitive_cube_add(size=0.15, location=(0, 0.72, 0.55))
    latch = bpy.context.active_object
    latch.name = "Latch"
    assign_material(latch, metal_mat)

    # Corner brackets
    corners = [(1.15, 0.65), (1.15, -0.65), (-1.15, 0.65), (-1.15, -0.65)]
    for cx, cy in corners:
        bpy.ops.mesh.primitive_cube_add(size=0.12, location=(cx, cy, 0.35))
        bracket = bpy.context.active_object
        bracket.name = "Bracket"
        assign_material(bracket, metal_mat)

def make_pine_tree(data):
    color_trunk  = data.get("color_trunk",  [0.25, 0.15, 0.05])
    color_foliage = data.get("color_foliage", [0.05, 0.3, 0.08])

    # Trunk
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.1, depth=1.0, location=(0, 0, 0.5), vertices=6
    )
    trunk = bpy.context.active_object
    trunk.name = "Pine_Trunk"
    assign_material(trunk, make_material("Pine_Trunk_Mat", color_trunk, roughness=0.9))

    # Cone layers (3 cones stacked)
    foliage_mat = make_material("Pine_Foliage_Mat", color_foliage, roughness=0.8)
    layers = [(0, 0, 1.2, 0.75, 1.0), (0, 0, 1.8, 0.55, 0.8), (0, 0, 2.3, 0.35, 0.7)]
    for x, y, z, r, h in layers:
        bpy.ops.mesh.primitive_cone_add(
            radius1=r, radius2=0, depth=h,
            location=(x, y, z), vertices=7
        )
        cone = bpy.context.active_object
        cone.name = f"Pine_Layer_{z}"
        assign_material(cone, foliage_mat)

def make_sword(data):
    color_blade  = data.get("color_blade",  [0.7, 0.7, 0.75])
    color_handle = data.get("color_handle", [0.2, 0.1, 0.05])

    blade_mat  = make_material("Blade_Mat",  color_blade,  metallic=0.9, roughness=0.2)
    handle_mat = make_material("Handle_Mat", color_handle, roughness=0.9)
    gold_mat   = make_material("Guard_Mat",  [0.8, 0.6, 0.1], metallic=1.0, roughness=0.3)

    # Blade (tall thin cube)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1.0))
    blade = bpy.context.active_object
    blade.scale = (0.05, 0.015, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    blade.name = "Blade"
    assign_material(blade, blade_mat)

    # Guard (wide flat cube)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.08))
    guard = bpy.context.active_object
    guard.scale = (0.35, 0.04, 0.06)
    bpy.ops.object.transform_apply(scale=True)
    guard.name = "Guard"
    assign_material(guard, gold_mat)

    # Handle
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.045, depth=0.5, location=(0, 0, -0.22), vertices=8
    )
    handle = bpy.context.active_object
    handle.name = "Handle"
    assign_material(handle, handle_mat)

    # Pommel
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(0, 0, -0.5), segments=6, ring_count=4)
    pommel = bpy.context.active_object
    pommel.name = "Pommel"
    assign_material(pommel, gold_mat)

def make_street_lamp(data):
    color_metal = data.get("color_metal", [0.1, 0.1, 0.12])
    color_light = data.get("color_light", [1.0, 0.9, 0.5])

    metal_mat = make_material("Lamp_Metal_Mat", color_metal, metallic=0.85, roughness=0.4)
    glass_mat = make_material("Lamp_Glass_Mat", color_light, roughness=0.1, emission=color_light)

    # Pole
    bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=3.0, location=(0, 0, 1.5), vertices=8)
    pole = bpy.context.active_object
    pole.name = "Pole"
    assign_material(pole, metal_mat)

    # Arm
    bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=0.6, location=(0.3, 0, 3.1), vertices=6)
    arm = bpy.context.active_object
    arm.rotation_euler = (0, math.radians(90), 0)
    bpy.ops.object.transform_apply(rotation=True)
    arm.name = "Arm"
    assign_material(arm, metal_mat)

    # Lamp head (lantern box)
    bpy.ops.mesh.primitive_cube_add(size=0.3, location=(0.6, 0, 3.1))
    head = bpy.context.active_object
    head.scale = (1.0, 1.0, 1.4)
    bpy.ops.object.transform_apply(scale=True)
    head.name = "Lamp_Head"
    assign_material(head, glass_mat)

    # Base plate
    bpy.ops.mesh.primitive_cylinder_add(radius=0.15, depth=0.05, location=(0, 0, 0.025), vertices=8)
    base = bpy.context.active_object
    base.name = "Base"
    assign_material(base, metal_mat)

def make_mushroom(data):
    color_cap  = data.get("color_cap",  [0.8, 0.15, 0.1])
    color_stem = data.get("color_stem", [0.85, 0.75, 0.6])

    # Stem
    bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=1.2, location=(0, 0, 0.6), vertices=10)
    stem = bpy.context.active_object
    stem.name = "Mushroom_Stem"
    assign_material(stem, make_material("Stem_Mat", color_stem, roughness=0.85))

    # Cap (flattened sphere)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.9, location=(0, 0, 1.5), segments=10, ring_count=6)
    cap = bpy.context.active_object
    cap.scale = (1.0, 1.0, 0.5)
    bpy.ops.object.transform_apply(scale=True)
    cap.name = "Mushroom_Cap"
    assign_material(cap, make_material("Cap_Mat", color_cap, roughness=0.75))

    # Spots on cap
    spot_mat = make_material("Spot_Mat", [1.0, 1.0, 1.0], roughness=0.8)
    spot_positions = [(0.4, 0.3, 1.65), (-0.35, 0.4, 1.6), (0.1, -0.5, 1.55)]
    for sx, sy, sz in spot_positions:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(sx, sy, sz), segments=6, ring_count=4)
        spot = bpy.context.active_object
        spot.scale = (1.0, 1.0, 0.3)
        bpy.ops.object.transform_apply(scale=True)
        spot.name = "Spot"
        assign_material(spot, spot_mat)

def make_simple_house(data):
    color_wall = data.get("color_wall", [0.9, 0.85, 0.75])
    color_roof = data.get("color_roof", [0.55, 0.2, 0.1])

    wall_mat = make_material("Wall_Mat", color_wall, roughness=0.9)
    roof_mat = make_material("Roof_Mat", color_roof, roughness=0.85)
    door_mat = make_material("Door_Mat", [0.3, 0.18, 0.08], roughness=0.9)
    glass_mat = make_material("Window_Mat", [0.5, 0.7, 0.9], roughness=0.1, metallic=0.0)

    # Walls (box)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.7))
    walls = bpy.context.active_object
    walls.scale = (1.5, 1.2, 1.3)
    bpy.ops.object.transform_apply(scale=True)
    walls.name = "Walls"
    assign_material(walls, wall_mat)

    # Roof (prism via cone with 4 verts effectively a ridge)
    bpy.ops.mesh.primitive_cone_add(radius1=1.7, radius2=0.0, depth=0.9,
                                     location=(0, 0, 1.85), vertices=4)
    roof = bpy.context.active_object
    roof.rotation_euler = (0, 0, math.radians(45))
    bpy.ops.object.transform_apply(rotation=True)
    roof.name = "Roof"
    assign_material(roof, roof_mat)

    # Door
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1.22, 0.45))
    door = bpy.context.active_object
    door.scale = (0.25, 0.01, 0.45)
    bpy.ops.object.transform_apply(scale=True)
    door.name = "Door"
    assign_material(door, door_mat)

    # Windows (2 side panels)
    for wx in [-0.65, 0.65]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(wx, 1.22, 0.85))
        win = bpy.context.active_object
        win.scale = (0.2, 0.01, 0.2)
        bpy.ops.object.transform_apply(scale=True)
        win.name = "Window"
        assign_material(win, glass_mat)

    # Chimney
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.5, 0, 2.1))
    chimney = bpy.context.active_object
    chimney.scale = (0.2, 0.2, 0.35)
    bpy.ops.object.transform_apply(scale=True)
    chimney.name = "Chimney"
    assign_material(chimney, roof_mat)

# ─────────────────────────────────────────
# Studio Lighting (Photorealistic / Cycles)
# ─────────────────────────────────────────
def add_studio_lights():
    """Three-point studio lighting for photorealistic renders."""
    # Key light – warm, strong
    bpy.ops.object.light_add(type='AREA', location=(3, -3, 5))
    key = bpy.context.active_object
    key.name = "Key_Light"
    key.data.energy = 800
    key.data.size = 2.0
    key.data.color = (1.0, 0.95, 0.88)
    key.rotation_euler = (math.radians(50), 0, math.radians(45))

    # Fill light – cool, soft
    bpy.ops.object.light_add(type='AREA', location=(-4, 2, 3))
    fill = bpy.context.active_object
    fill.name = "Fill_Light"
    fill.data.energy = 200
    fill.data.size = 4.0
    fill.data.color = (0.7, 0.8, 1.0)

    # Rim light – back highlight
    bpy.ops.object.light_add(type='AREA', location=(0, 4, 4))
    rim = bpy.context.active_object
    rim.name = "Rim_Light"
    rim.data.energy = 400
    rim.data.size = 1.5
    rim.data.color = (1.0, 0.98, 0.95)
    rim.rotation_euler = (math.radians(-30), 0, 0)

def add_studio_world():
    """Neutral grey gradient world for photorealistic studio look."""
    world = bpy.data.worlds.new("StudioWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg  = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Color'].default_value = (0.06, 0.06, 0.07, 1.0)
    bg.inputs['Strength'].default_value = 0.5
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])

# ─────────────────────────────────────────
# High-Poly Photorealistic Material Helpers
# ─────────────────────────────────────────
def make_pbr_material(name, base_color, metallic=0.0, roughness=0.4,
                      specular=0.5, ior=1.45, emission=None,
                      noise_bump=0.0, use_glass=False):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out  = nt.nodes.new('ShaderNodeOutputMaterial')
    prin = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(prin.outputs['BSDF'], out.inputs['Surface'])

    prin.inputs['Base Color'].default_value    = (*base_color, 1.0)
    prin.inputs['Metallic'].default_value      = metallic
    prin.inputs['Roughness'].default_value     = roughness
    prin.inputs['IOR'].default_value           = ior

    if emission:
        prin.inputs['Emission Color'].default_value    = (*emission, 1.0)
        prin.inputs['Emission Strength'].default_value = 3.0

    if use_glass:
        prin.inputs['Transmission Weight'].default_value = 1.0
        prin.inputs['Roughness'].default_value           = 0.0
        mat.blend_method = 'BLEND'

    if noise_bump > 0:
        noise = nt.nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value     = 12.0
        noise.inputs['Detail'].default_value    = 8.0
        noise.inputs['Roughness'].default_value = 0.6
        bump  = nt.nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value   = noise_bump
        nt.links.new(noise.outputs['Fac'],    bump.inputs['Height'])
        nt.links.new(bump.outputs['Normal'],  prin.inputs['Normal'])
    return mat

def make_textured_pbr_material(name, material_name, scale=2.0, fallback_color=(0.5, 0.5, 0.5)):
    """
    Creates a realistic PBR material using downloaded texture maps (diffuse, roughness, normal).
    Falls back gracefully to procedural color if files are not found.
    """
    mat_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "materials", material_name)
    diff_path = os.path.join(mat_dir, "diffuse.jpg")
    rough_path = os.path.join(mat_dir, "roughness.jpg")
    nor_path = os.path.join(mat_dir, "normal.jpg")

    if not os.path.exists(diff_path):
        return make_pbr_material(name, fallback_color)

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new('ShaderNodeOutputMaterial')
    prin = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(prin.outputs['BSDF'], out.inputs['Surface'])

    # Texture coordinate & Mapping for tiling
    tex_coord = nt.nodes.new('ShaderNodeTexCoord')
    mapping = nt.nodes.new('ShaderNodeMapping')
    mapping.inputs['Scale'].default_value = (scale, scale, scale)
    nt.links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])

    # 1. Diffuse / Albedo Map
    diff_img = nt.nodes.new('ShaderNodeTexImage')
    diff_img.image = bpy.data.images.load(diff_path)
    nt.links.new(mapping.outputs['Vector'], diff_img.inputs['Vector'])
    nt.links.new(diff_img.outputs['Color'], prin.inputs['Base Color'])

    # 2. Roughness Map
    if os.path.exists(rough_path):
        rough_img = nt.nodes.new('ShaderNodeTexImage')
        rough_img.image = bpy.data.images.load(rough_path)
        rough_img.image.colorspace_settings.name = 'Non-Color'
        nt.links.new(mapping.outputs['Vector'], rough_img.inputs['Vector'])
        nt.links.new(rough_img.outputs['Color'], prin.inputs['Roughness'])

    # 3. Normal Map
    if os.path.exists(nor_path):
        nor_img = nt.nodes.new('ShaderNodeTexImage')
        nor_img.image = bpy.data.images.load(nor_path)
        nor_img.image.colorspace_settings.name = 'Non-Color'
        nor_node = nt.nodes.new('ShaderNodeNormalMap')
        nor_node.inputs['Strength'].default_value = 1.0
        nt.links.new(mapping.outputs['Vector'], nor_img.inputs['Vector'])
        nt.links.new(nor_img.outputs['Color'], nor_node.inputs['Color'])
        nt.links.new(nor_node.outputs['Normal'], prin.inputs['Normal'])

    return mat

def add_subsurf(obj, levels=3):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_add(type='SUBSURF')
    obj.modifiers['Subdivision'].levels          = levels
    obj.modifiers['Subdivision'].render_levels   = levels
    obj.modifiers['Subdivision'].subdivision_type = 'CATMULL_CLARK'

# ─────────────────────────────────────────
# High-Poly Model Builders
# ─────────────────────────────────────────

def make_hp_ceramic_vase(data):
    """Photorealistic high-poly ceramic vase."""
    color = data.get("color_base", [0.85, 0.75, 0.6])

    # Build vase via a lathe-like profile using a cylinder + taper modifiers
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.5, depth=2.0, location=(0, 0, 1.0), vertices=32)
    vase = bpy.context.active_object
    vase.name = "Vase_Body"

    # Taper top to narrow neck
    bpy.ops.object.modifier_add(type='SIMPLE_DEFORM')
    vase.modifiers['SimpleDeform'].deform_method = 'TAPER'
    vase.modifiers['SimpleDeform'].factor        = -0.4
    bpy.ops.object.modifier_apply(modifier='SimpleDeform')

    add_subsurf(vase, levels=3)

    vase_mat = make_pbr_material("Ceramic_Mat", color,
                                  metallic=0.0, roughness=0.15,
                                  ior=1.52, noise_bump=0.04)
    assign_material(vase, vase_mat)

    # Rim ring at top
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.22, minor_radius=0.04,
        major_segments=48, minor_segments=16,
        location=(0, 0, 2.05))
    rim = bpy.context.active_object
    rim.name = "Vase_Rim"
    assign_material(rim, vase_mat)

def make_hp_gem_crystal(data):
    """Photorealistic cut gem / crystal."""
    color = data.get("color_gem", [0.1, 0.4, 0.9])

    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=2, radius=0.7, location=(0, 0, 0.7))
    gem = bpy.context.active_object
    gem.name = "Gem"

    # Cast into a faceted diamond-ish shape
    bpy.ops.object.modifier_add(type='CAST')
    gem.modifiers['Cast'].cast_type = 'CUBOID'
    gem.modifiers['Cast'].factor    = 0.35
    bpy.ops.object.modifier_apply(modifier='Cast')

    gem_mat = make_pbr_material("Gem_Mat", color,
                                 metallic=0.0, roughness=0.0,
                                 ior=2.42, use_glass=True)
    assign_material(gem, gem_mat)

    # Gold base mount
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.55, depth=0.12, location=(0, 0, 0.06), vertices=24)
    mount = bpy.context.active_object
    mount.name = "Mount"
    assign_material(mount, make_pbr_material(
        "Gold_Mat", [0.95, 0.75, 0.2], metallic=1.0, roughness=0.12))

def make_hp_goblet(data):
    """Photorealistic metal goblet / chalice."""
    color_metal = data.get("color_metal", [0.85, 0.7, 0.2])

    metal_mat = make_pbr_material("Goblet_Metal", color_metal,
                                   metallic=1.0, roughness=0.1, noise_bump=0.02)

    # Cup bowl
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.4, depth=0.7, location=(0, 0, 1.45), vertices=32)
    cup = bpy.context.active_object
    cup.name = "Cup"
    bpy.ops.object.modifier_add(type='SIMPLE_DEFORM')
    cup.modifiers['SimpleDeform'].deform_method = 'TAPER'
    cup.modifiers['SimpleDeform'].factor = 0.45
    bpy.ops.object.modifier_apply(modifier='SimpleDeform')
    add_subsurf(cup, 3)
    assign_material(cup, metal_mat)

    # Stem
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.07, depth=0.9, location=(0, 0, 0.85), vertices=16)
    stem = bpy.context.active_object
    stem.name = "Stem"
    add_subsurf(stem, 2)
    assign_material(stem, metal_mat)

    # Base disc
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.45, depth=0.08, location=(0, 0, 0.04), vertices=32)
    base = bpy.context.active_object
    base.name = "Base"
    add_subsurf(base, 2)
    assign_material(base, metal_mat)

    # Knob on stem
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.13, location=(0, 0, 0.88), segments=24, ring_count=16)
    knob = bpy.context.active_object
    knob.name = "Knob"
    assign_material(knob, metal_mat)

def make_hp_wine_bottle(data):
    """Photorealistic glass wine bottle."""
    color_glass = data.get("color_glass", [0.05, 0.2, 0.05])

    glass_mat = make_pbr_material("Glass_Mat", color_glass,
                                   metallic=0.0, roughness=0.0,
                                   ior=1.52, use_glass=True)
    label_mat = make_pbr_material("Label_Mat", [0.95, 0.92, 0.82],
                                   metallic=0.0, roughness=0.5)

    # Body
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.35, depth=1.8, location=(0, 0, 0.9), vertices=32)
    body = bpy.context.active_object
    body.name = "Bottle_Body"
    add_subsurf(body, 3)
    assign_material(body, glass_mat)

    # Shoulder taper
    bpy.ops.mesh.primitive_cone_add(
        radius1=0.35, radius2=0.18, depth=0.5,
        location=(0, 0, 1.85), vertices=32)
    shoulder = bpy.context.active_object
    shoulder.name = "Shoulder"
    add_subsurf(shoulder, 2)
    assign_material(shoulder, glass_mat)

    # Neck
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.1, depth=0.55, location=(0, 0, 2.38), vertices=16)
    neck = bpy.context.active_object
    neck.name = "Neck"
    add_subsurf(neck, 2)
    assign_material(neck, glass_mat)

    # Label strip
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.355, depth=0.6, location=(0, 0, 0.85), vertices=32)
    label = bpy.context.active_object
    label.name = "Label"
    assign_material(label, label_mat)

    # Cork
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.08, depth=0.2, location=(0, 0, 2.72), vertices=16)
    cork = bpy.context.active_object
    cork.name = "Cork"
    assign_material(cork, make_pbr_material(
        "Cork_Mat", [0.72, 0.55, 0.35], roughness=0.9, noise_bump=0.08))

def make_hp_chess_king(data):
    """Photorealistic marble chess king piece."""
    color_piece = data.get("color_piece", [0.92, 0.90, 0.88])
    mat = make_textured_pbr_material("Chess_Marble", "marble", scale=2.0, fallback_color=color_piece)

    # Base disc
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.42, depth=0.12, location=(0, 0, 0.06), vertices=32)
    base = bpy.context.active_object; base.name = "Chess_Base"
    add_subsurf(base, 2); assign_material(base, mat)

    # Lower column
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.22, depth=0.5, location=(0, 0, 0.37), vertices=32)
    col = bpy.context.active_object; col.name = "Chess_Col"
    add_subsurf(col, 2); assign_material(col, mat)

    # Middle bulge
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.28, location=(0, 0, 0.75), segments=32, ring_count=24)
    bulge = bpy.context.active_object; bulge.name = "Chess_Bulge"
    bulge.scale.z = 0.65
    bpy.ops.object.transform_apply(scale=True)
    assign_material(bulge, mat)

    # Upper shaft
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.16, depth=0.6, location=(0, 0, 1.2), vertices=32)
    shaft = bpy.context.active_object; shaft.name = "Chess_Shaft"
    add_subsurf(shaft, 2); assign_material(shaft, mat)

    # Head ball
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.22, location=(0, 0, 1.65), segments=32, ring_count=24)
    head = bpy.context.active_object; head.name = "Chess_Head"
    assign_material(head, mat)

    # Cross (king symbol)
    for axis, loc, sc in [
        ('X', (0, 0, 1.97), (0.06, 0.06, 0.25)),
        ('Y', (0, 0, 2.1),  (0.25, 0.06, 0.06)),
    ]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        c = bpy.context.active_object; c.name = f"Cross_{axis}"
        c.scale = sc
        bpy.ops.object.transform_apply(scale=True)
        assign_material(c, mat)

def make_hp_apple(data):
    """Photorealistic red apple."""
    color_skin = data.get("color_skin", [0.75, 0.08, 0.04])

    # Apple body – squashed sphere
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.65, location=(0, 0, 0.65), segments=48, ring_count=32)
    apple = bpy.context.active_object
    apple.name = "Apple_Body"
    apple.scale = (1.0, 1.0, 0.88)
    bpy.ops.object.transform_apply(scale=True)
    add_subsurf(apple, 3)
    assign_material(apple, make_pbr_material(
        "Apple_Mat", color_skin, metallic=0.0, roughness=0.18,
        ior=1.4, noise_bump=0.02))

    # Stem
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.04, depth=0.35, location=(0, 0, 1.33), vertices=10)
    stem = bpy.context.active_object
    stem.name = "Apple_Stem"
    stem.rotation_euler = (math.radians(10), 0, 0)
    bpy.ops.object.transform_apply(rotation=True)
    add_subsurf(stem, 2)
    assign_material(stem, make_pbr_material(
        "Stem_Mat", [0.18, 0.1, 0.03], roughness=0.85, noise_bump=0.06))

    # Leaf
    bpy.ops.mesh.primitive_plane_add(size=0.35, location=(0.12, 0, 1.38))
    leaf = bpy.context.active_object
    leaf.name = "Leaf"
    leaf.rotation_euler = (math.radians(30), math.radians(20), 0)
    bpy.ops.object.transform_apply(rotation=True)
    add_subsurf(leaf, 2)
    assign_material(leaf, make_pbr_material(
        "Leaf_Mat", [0.12, 0.4, 0.08], roughness=0.6, noise_bump=0.03))

def make_hp_lantern(data):
    """Photorealistic hanging lantern."""
    color_metal = data.get("color_metal", [0.08, 0.07, 0.06])
    color_glass = data.get("color_glass", [0.9, 0.7, 0.3])

    metal_mat = make_pbr_material("Lantern_Metal", color_metal,
                                   metallic=0.9, roughness=0.35)
    glass_mat = make_pbr_material("Lantern_Glass", color_glass,
                                   metallic=0.0, roughness=0.05,
                                   ior=1.52, use_glass=True,
                                   emission=color_glass)

    # Outer cage – 4 thin pillars
    for angle in [0, 90, 180, 270]:
        rad = math.radians(angle)
        x = math.cos(rad) * 0.28
        y = math.sin(rad) * 0.28
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.025, depth=1.0, location=(x, y, 0.5), vertices=8)
        pillar = bpy.context.active_object
        pillar.name = f"Pillar_{angle}"
        add_subsurf(pillar, 2)
        assign_material(pillar, metal_mat)

    # Top cap
    bpy.ops.mesh.primitive_cone_add(
        radius1=0.35, radius2=0.05, depth=0.3,
        location=(0, 0, 1.15), vertices=16)
    top = bpy.context.active_object; top.name = "Lantern_Top"
    add_subsurf(top, 2); assign_material(top, metal_mat)

    # Bottom cap
    bpy.ops.mesh.primitive_cone_add(
        radius1=0.05, radius2=0.28, depth=0.18,
        location=(0, 0, 0.0), vertices=16)
    bot = bpy.context.active_object; bot.name = "Lantern_Bot"
    add_subsurf(bot, 2); assign_material(bot, metal_mat)

    # Glass panels (inner cylinders)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.27, depth=0.95, location=(0, 0, 0.5), vertices=32)
    glass = bpy.context.active_object; glass.name = "Lantern_Glass"
    assign_material(glass, glass_mat)

    # Hanging ring
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.08, minor_radius=0.015,
        major_segments=24, minor_segments=12,
        location=(0, 0, 1.34))
    ring = bpy.context.active_object; ring.name = "Hang_Ring"
    assign_material(ring, metal_mat)

def make_hp_crown(data):
    """Photorealistic golden crown with gems."""
    color_gold = data.get("color_gold", [0.95, 0.72, 0.15])
    color_gem  = data.get("color_gem",  [0.8, 0.1, 0.1])

    gold_mat = make_pbr_material("Crown_Gold", color_gold,
                                  metallic=1.0, roughness=0.08, noise_bump=0.01)
    gem_mat  = make_pbr_material("Crown_Gem",  color_gem,
                                  metallic=0.0, roughness=0.0,
                                  ior=2.0, use_glass=True)

    # Main band
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.55, minor_radius=0.10,
        major_segments=48, minor_segments=20,
        location=(0, 0, 0.1))
    band = bpy.context.active_object; band.name = "Crown_Band"
    assign_material(band, gold_mat)

    # 5 spikes
    for i in range(5):
        angle = math.radians(i * 72)
        x = math.cos(angle) * 0.55
        y = math.sin(angle) * 0.55
        bpy.ops.mesh.primitive_cone_add(
            radius1=0.12, radius2=0.01, depth=0.5,
            location=(x, y, 0.45), vertices=12)
        spike = bpy.context.active_object
        spike.name = f"Spike_{i}"
        add_subsurf(spike, 2)
        assign_material(spike, gold_mat)

        # Small gem on each spike
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=2, radius=0.07,
            location=(x * 0.98, y * 0.98, 0.15))
        gem = bpy.context.active_object
        gem.name = f"Gem_{i}"
        assign_material(gem, gem_mat)

def make_hp_modern_chair(data):
    """
    High-end contemporary Scandinavian designer armchair matching concept art.
    Features:
    - 100% Seamless sculpted ergonomic continuous shell (no stacked boxes)
    - Plump rounded organic seat cushion with smooth curvature
    - Splayed tapered black steel legs with crossbar undercarriage and floor gliders
    - Full shade-smooth on all surfaces with Catmull-Clark subdivision
    - Realistic textured bouclé fabric upholstery with micro-bump
    """
    color_fabric = data.get("color_fabric", [0.78, 0.70, 0.60])
    color_metal  = data.get("color_metal",  [0.05, 0.05, 0.05])

    fabric_mat = make_pbr_material(
        "Chair_Fabric", color_fabric,
        metallic=0.0, roughness=0.88, ior=1.45, noise_bump=0.05
    )
    metal_mat = make_pbr_material(
        "Chair_Metal", color_metal,
        metallic=0.85, roughness=0.32, noise_bump=0.01
    )

    # 1. CONTINUOUS SCULPTED ERGONOMIC SHELL (Quad-grid Parametric Surface)
    n_rings = 18
    n_segs = 36
    verts = []
    faces = []

    for r in range(n_rings):
        u = r / (n_rings - 1)  # 0 at bottom center, 1 at top rim
        # Smooth radial expansion
        rad_base = 0.44 * math.sin(u * math.pi * 0.5)

        for s in range(n_segs):
            theta = 2.0 * math.pi * s / n_segs
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)  # positive = back, negative = front

            # Modulate radius: wider at arms, deeper at back
            rx = rad_base * (1.0 + 0.12 * (cos_t**2))
            ry = rad_base * (1.0 + 0.18 * max(0.0, sin_t) - 0.08 * max(0.0, -sin_t))

            x = rx * cos_t
            y = ry * sin_t

            # Smooth organic height contour
            back_factor  = max(0.0, sin_t)
            arm_factor   = (1.0 - abs(sin_t)) * (0.8 + 0.2 * max(0.0, sin_t))
            front_factor = max(0.0, -sin_t)

            z_target = 0.38 + (
                0.64 * (back_factor**1.25) +
                0.28 * (arm_factor**1.4) +
                0.03 * front_factor
            )
            z = 0.38 + (z_target - 0.38) * u

            # Ergonomic recline: gently curve backwards as height increases
            if sin_t > 0:
                y += 0.13 * (u**1.6) * sin_t

            verts.append((x, y, z))

    for r in range(n_rings - 1):
        for s in range(n_segs):
            s_next = (s + 1) % n_segs
            v1 = r * n_segs + s
            v2 = r * n_segs + s_next
            v3 = (r + 1) * n_segs + s_next
            v4 = (r + 1) * n_segs + s
            faces.append((v1, v2, v3, v4))

    mesh = bpy.data.meshes.new('ChairShellMesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    shell = bpy.data.objects.new('Chair_Sculpted_Shell', mesh)
    bpy.context.collection.objects.link(shell)
    bpy.context.view_layer.objects.active = shell
    shell.select_set(True)

    # Shell thickness & curvature
    sol = shell.modifiers.new(name='Solidify', type='SOLIDIFY')
    sol.thickness = 0.038
    sol.offset = 0.0

    sub = shell.modifiers.new(name='Subdivision', type='SUBSURF')
    sub.levels = 3
    sub.render_levels = 3

    bpy.ops.object.shade_smooth()
    assign_material(shell, fabric_mat)

    # 2. PLUMP ORGANIC SEAT CUSHION (Curved Spheroid with Soft Indentation)
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=48, ring_count=32, radius=0.36, location=(0, -0.03, 0.44)
    )
    cushion = bpy.context.active_object
    cushion.name = "Plump_Seat_Cushion"
    cushion.scale = (1.02, 0.94, 0.34)
    bpy.ops.object.transform_apply(scale=True)
    add_subsurf(cushion, 2)
    bpy.ops.object.shade_smooth()
    assign_material(cushion, fabric_mat)

    # 3. SPLAYED TAPERED BLACK STEEL LEGS & UNDERCARRIAGE
    leg_configs = [
        ("Front_L", (-0.28, -0.25, 0.18), (math.radians(-11), math.radians(-9), 0)),
        ("Front_R", ( 0.28, -0.25, 0.18), (math.radians(-11), math.radians( 9), 0)),
        ("Back_L",  (-0.25,  0.25, 0.18), (math.radians( 13), math.radians(-8), 0)),
        ("Back_R",  ( 0.25,  0.25, 0.18), (math.radians( 13), math.radians( 8), 0)),
    ]
    for leg_name, loc, rot in leg_configs:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.017, depth=0.38, location=loc, vertices=24
        )
        leg = bpy.context.active_object
        leg.name = f"Leg_{leg_name}"
        leg.rotation_euler = rot
        bpy.ops.object.transform_apply(rotation=True)
        add_subsurf(leg, 2)
        bpy.ops.object.shade_smooth()
        assign_material(leg, metal_mat)

        # Floor glider feet
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.021, depth=0.022,
            location=(loc[0] * 1.07, loc[1] * 1.07, 0.011), vertices=20
        )
        glider = bpy.context.active_object
        glider.name = f"Glider_{leg_name}"
        bpy.ops.object.shade_smooth()
        assign_material(glider, metal_mat)

    # 4. WELDED STEEL CROSS-FRAME (Connecting the 4 legs securely)
    # Side crossbars
    for side, x in [("L", -0.26), ("R", 0.26)]:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.011, depth=0.48, location=(x, 0.0, 0.18), vertices=16
        )
        bar = bpy.context.active_object
        bar.name = f"Crossbar_Side_{side}"
        bar.rotation_euler = (math.radians(90), 0, 0)
        bpy.ops.object.transform_apply(rotation=True)
        add_subsurf(bar, 2)
        bpy.ops.object.shade_smooth()
        assign_material(bar, metal_mat)

    # Rear crossbar
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.011, depth=0.50, location=(0.0, 0.23, 0.18), vertices=16
    )
    rear_bar = bpy.context.active_object
    rear_bar.name = "Crossbar_Rear"
    rear_bar.rotation_euler = (0, math.radians(90), 0)
    bpy.ops.object.transform_apply(rotation=True)
    add_subsurf(rear_bar, 2)
    bpy.ops.object.shade_smooth()
    assign_material(rear_bar, metal_mat)

def make_hp_tactical_pistol(data):
    """
    High-end modern 9mm tactical combat pistol matching concept art.
    Overhauled V9 procedural architecture:
    - Seamless ergonomic polymer receiver with 20° tactical rake, finger grooves, and swept beavertail
    - 13mm narrowed combat trigger guard with finger rest
    - CNC machined slide with 45° top chamfers, front bull-nose taper, 26° chevron serrations, and ejection port
    - Threaded tactical barrel with knurled thread protector cap & 9mm crown bore
    - Three-dot combat iron sights with luminous green-white inserts
    - Integrated trigger shoe with red combat safety blade
    """
    color_metal   = data.get("color_metal",   [0.070, 0.075, 0.082])
    color_polymer = data.get("color_polymer", [0.022, 0.024, 0.026])

    slide_mat = make_pbr_material(
        "Pistol_Slide_Steel", color_metal,
        metallic=0.90, roughness=0.30, noise_bump=0.012
    )
    polymer_mat = make_pbr_material(
        "Pistol_Polymer_Frame", color_polymer,
        metallic=0.0, roughness=0.55, noise_bump=0.025
    )
    hardware_mat = make_pbr_material(
        "Pistol_Hardware_Steel", [0.028, 0.030, 0.033],
        metallic=0.96, roughness=0.20
    )
    sight_mat = make_pbr_material(
        "Pistol_Sight_Dots", [0.9, 1.0, 0.92],
        metallic=0.0, roughness=0.1, emission=(0.9, 1.0, 0.92, 1.0)
    )
    red_mat = make_pbr_material(
        "Pistol_Safety_Red", [0.75, 0.04, 0.04],
        metallic=0.05, roughness=0.35
    )

    # 1. UNIFIED ERGONOMIC LOWER FRAME
    curve_data = bpy.data.curves.new('PistolFrameCurve', type='CURVE')
    curve_data.dimensions = '2D'
    curve_data.extrude = 0.0135 # 27mm total frame width
    curve_data.bevel_depth = 0.0 # Solid manifold
    curve_data.fill_mode = 'BOTH'
    curve_data.resolution_u = 16

    outer = curve_data.splines.new('BEZIER')
    profile = [
        (+0.092, 0.072, 'VECTOR'), # 0: Front top of dust cover
        (+0.085, 0.052, 'VECTOR'), # 1: 45° front chamfer
        (+0.035, 0.052, 'VECTOR'), # 2: Picatinny rail rear limit
        (+0.026, 0.025, 'AUTO'),   # 3: Trigger guard front corner
        (+0.022, 0.021, 'AUTO'),   # 4: Combat front finger hook
        (+0.005, 0.020, 'AUTO'),   # 5: Trigger guard bottom
        (-0.020, 0.023, 'AUTO'),   # 6: Trigger guard rear bottom
        (-0.023, 0.032, 'AUTO'),   # 7: Front strap root under trigger
        (-0.028, 0.018, 'AUTO'),   # 8: Finger groove 1
        (-0.026, 0.006, 'AUTO'),   # 9: Finger ridge 1
        (-0.034, -0.010, 'AUTO'),  # 10: Finger groove 2
        (-0.032, -0.020, 'AUTO'),  # 11: Finger ridge 2
        (-0.043, -0.038, 'AUTO'),  # 12: Finger groove 3
        (-0.045, -0.050, 'AUTO'),  # 13: Grip front lip above magwell
        (-0.048, -0.056, 'VECTOR'),# 14: Magwell front base
        (-0.088, -0.056, 'VECTOR'),# 15: Magwell rear base
        (-0.090, -0.046, 'AUTO'),  # 16: Grip heel
        (-0.080, -0.012, 'AUTO'),  # 17: Backstrap palm swell
        (-0.062, 0.026, 'AUTO'),   # 18: Upper backstrap
        (-0.048, 0.048, 'AUTO'),   # 19: Beavertail throat (deep notch)
        (-0.086, 0.063, 'AUTO'),   # 20: Beavertail horn tip
        (-0.080, 0.072, 'VECTOR')  # 21: Frame rear top under slide
    ]
    outer.bezier_points.add(len(profile) - 1)
    for idx, (py, pz, htype) in enumerate(profile):
        bp = outer.bezier_points[idx]
        bp.co = (py, pz, 0.0)
        bp.handle_left_type = htype
        bp.handle_right_type = htype
    outer.use_cyclic_u = True

    # Inner cutout for trigger cavity
    inner = curve_data.splines.new('BEZIER')
    inner_profile = [
        (+0.020, 0.050, 'VECTOR'), # Under dust cover front
        (+0.020, 0.028, 'AUTO'),   # Trigger guard inside front
        (+0.005, 0.027, 'AUTO'),   # Trigger guard inside bottom
        (-0.014, 0.029, 'AUTO'),   # Trigger guard inside rear
        (-0.014, 0.050, 'VECTOR'), # Trigger cavity root
    ]
    inner.bezier_points.add(len(inner_profile) - 1)
    for idx, (py, pz, htype) in enumerate(inner_profile):
        bp = inner.bezier_points[idx]
        bp.co = (py, pz, 0.0)
        bp.handle_left_type = htype
        bp.handle_right_type = htype
    inner.use_cyclic_u = True

    frame_obj = bpy.data.objects.new("Pistol_Receiver", curve_data)
    bpy.context.collection.objects.link(frame_obj)
    frame_obj.rotation_euler = (math.radians(90), 0, math.radians(90))
    bpy.context.view_layer.objects.active = frame_obj
    frame_obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    assign_material(frame_obj, polymer_mat)

    # Frame bevel modifier
    bev = frame_obj.modifiers.new("FrameBevel", type='BEVEL')
    bev.width = 0.0016
    bev.segments = 3
    bev.limit_method = 'ANGLE'
    bev.angle_limit = math.radians(35)

    # Recess trigger guard sides to 13mm width
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cube_add(
            size=1.0, location=(side * 0.011, 0.005, 0.036),
            scale=(0.010, 0.050, 0.032)
        )
        tg_cut = bpy.context.active_object
        tg_cut.name = f"TGCut_{side}"
        bool_tg = frame_obj.modifiers.new(f"TGCutBool_{side}", type='BOOLEAN')
        bool_tg.operation = 'DIFFERENCE'
        bool_tg.object = tg_cut
        tg_cut.hide_render = True
        tg_cut.hide_viewport = True

    # Ergonomic thumb rest indents on upper frame
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=24, radius=0.007, depth=0.003,
            location=(side * 0.0135, 0.008, 0.057),
            rotation=(0, math.radians(90), 0),
            scale=(1.0, 1.8, 0.6)
        )
        thumb_cut = bpy.context.active_object
        thumb_cut.name = f"ThumbIndent_{side}"
        bool_ti = frame_obj.modifiers.new(f"ThumbIndentBool_{side}", type='BOOLEAN')
        bool_ti.operation = 'DIFFERENCE'
        bool_ti.object = thumb_cut
        thumb_cut.hide_render = True
        thumb_cut.hide_viewport = True

    # Picatinny rail slots
    for r in range(4):
        slot_y = 0.048 + r * 0.0095
        bpy.ops.mesh.primitive_cube_add(
            size=1.0, location=(0.0, slot_y, 0.052),
            scale=(0.032, 0.0046, 0.004)
        )
        slot_cut = bpy.context.active_object
        slot_cut.name = f"RailSlot_{r}"
        bool_r = frame_obj.modifiers.new(f"RailSlotBool_{r}", type='BOOLEAN')
        bool_r.operation = 'DIFFERENCE'
        bool_r.object = slot_cut
        slot_cut.hide_render = True
        slot_cut.hide_viewport = True

    # Tactical grip stippling side panels (20° rake)
    grip_rake = math.radians(-20)
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cube_add(
            size=1.0, location=(side * 0.0138, -0.058, -0.015),
            scale=(0.0015, 0.026, 0.066),
            rotation=(grip_rake, 0, 0)
        )
        stipple = bpy.context.active_object
        stipple.name = f"GripStipple_{side}"
        assign_material(stipple, polymer_mat)
        bev_s = stipple.modifiers.new("Bevel", type='BEVEL')
        bev_s.width = 0.001
        bev_s.segments = 2

    # Flared magazine basepad
    bpy.ops.mesh.primitive_cube_add(
        size=1.0, location=(0.0, -0.068, -0.060),
        scale=(0.033, 0.046, 0.010),
        rotation=(grip_rake, 0, 0)
    )
    mag = bpy.context.active_object
    mag.name = "Magazine_Basepad"
    assign_material(mag, polymer_mat)
    bev_m = mag.modifiers.new("Bevel", type='BEVEL')
    bev_m.width = 0.002
    bev_m.segments = 3

    # Trigger with center red safety blade
    bpy.ops.mesh.primitive_cube_add(
        size=1.0, location=(0.0, 0.003, 0.040),
        scale=(0.0055, 0.009, 0.018),
        rotation=(math.radians(20), 0, 0)
    )
    shoe = bpy.context.active_object
    shoe.name = "Trigger_Shoe"
    assign_material(shoe, hardware_mat)
    bev_tr = shoe.modifiers.new("Bevel", type='BEVEL')
    bev_tr.width = 0.001
    bev_tr.segments = 2

    bpy.ops.mesh.primitive_cube_add(
        size=1.0, location=(0.0, 0.005, 0.039),
        scale=(0.0018, 0.008, 0.014),
        rotation=(math.radians(22), 0, 0)
    )
    blade = bpy.context.active_object
    blade.name = "Trigger_SafetyBlade"
    assign_material(blade, red_mat)

    # Controls: slide stop & takedown catch
    bpy.ops.mesh.primitive_cube_add(
        size=1.0, location=(-0.0145, -0.016, 0.069),
        scale=(0.0025, 0.016, 0.0045)
    )
    slide_stop = bpy.context.active_object
    slide_stop.name = "Control_SlideStop"
    assign_material(slide_stop, hardware_mat)

    bpy.ops.mesh.primitive_cube_add(
        size=1.0, location=(0.0, 0.012, 0.065),
        scale=(0.029, 0.005, 0.0035)
    )
    takedown = bpy.context.active_object
    takedown.name = "Control_TakedownCatch"
    assign_material(takedown, hardware_mat)

    # Frame pins
    for py, pz in [(-0.002, 0.065), (-0.022, 0.062)]:
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=16, radius=0.002, depth=0.0285,
            location=(0.0, py, pz),
            rotation=(0, math.radians(90), 0)
        )
        pin = bpy.context.active_object
        pin.name = f"FramePin_{py}"
        assign_material(pin, hardware_mat)

    # 2. CNC MACHINED SLIDE
    length = 0.188
    width = 0.027
    height = 0.034
    hw = width / 2.0
    slide_base_z = 0.072
    slide_center_z = slide_base_z + height / 2.0
    slide_center_y = 0.002
    y_front = slide_center_y + length / 2.0
    y_rear = slide_center_y - length / 2.0

    bpy.ops.mesh.primitive_cube_add(
        size=1.0, location=(0.0, slide_center_y, slide_center_z),
        scale=(width, length, height)
    )
    slide = bpy.context.active_object
    slide.name = "Pistol_Slide"
    assign_material(slide, slide_mat)
    bev_s = slide.modifiers.new("Bevel", type='BEVEL')
    bev_s.width = 0.0030
    bev_s.segments = 3
    bev_s.limit_method = 'ANGLE'
    bev_s.angle_limit = math.radians(35)

    # Bull-nose front chamfers
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cube_add(
            size=1.0, location=(side * (hw + 0.004), y_front, slide_center_z),
            scale=(0.012, 0.026, height * 1.2),
            rotation=(0, 0, side * math.radians(32))
        )
        nose_cut = bpy.context.active_object
        nose_cut.name = f"NoseCutter_{side}"
        bool_n = slide.modifiers.new(f"NoseChamfer_{side}", type='BOOLEAN')
        bool_n.operation = 'DIFFERENCE'
        bool_n.object = nose_cut
        nose_cut.hide_render = True
        nose_cut.hide_viewport = True

    # Ejection port cutout & barrel hood
    bpy.ops.mesh.primitive_cube_add(
        size=1.0, location=(0.008, -0.012, slide_base_z + height - 0.006),
        scale=(0.022, 0.035, 0.022)
    )
    ej_cut = bpy.context.active_object
    ej_cut.name = "EjectionCutter"
    bool_e = slide.modifiers.new("EjectionPortCut", type='BOOLEAN')
    bool_e.operation = 'DIFFERENCE'
    bool_e.object = ej_cut
    ej_cut.hide_render = True
    ej_cut.hide_viewport = True

    bpy.ops.mesh.primitive_cube_add(
        size=1.0, location=(0.0, -0.012, slide_base_z + height * 0.46),
        scale=(width * 0.84, 0.033, height * 0.72)
    )
    hood = bpy.context.active_object
    hood.name = "Barrel_ChamberHood"
    assign_material(hood, hardware_mat)
    bev_h = hood.modifiers.new("Bevel", type='BEVEL')
    bev_h.width = 0.001
    bev_h.segments = 2

    # Angled 26° chevron cocking serrations
    chevron_angle = math.radians(26)
    # Rear Serrations
    for i in range(6):
        y_pos = y_rear + 0.018 + i * 0.0055
        for side in [-1, 1]:
            bpy.ops.mesh.primitive_cube_add(
                size=1.0,
                location=(side * (hw + 0.0005), y_pos, slide_center_z + 0.001),
                scale=(0.0035, 0.0026, height * 0.70),
                rotation=(chevron_angle, 0, 0)
            )
            scut = bpy.context.active_object
            scut.name = f"RearSerr_{i}_{side}"
            bool_sc = slide.modifiers.new(f"RearSerr_{i}_{side}", type='BOOLEAN')
            bool_sc.operation = 'DIFFERENCE'
            bool_sc.object = scut
            scut.hide_render = True
            scut.hide_viewport = True

    # Front Serrations
    for i in range(5):
        y_pos = y_front - 0.046 + i * 0.0055
        for side in [-1, 1]:
            bpy.ops.mesh.primitive_cube_add(
                size=1.0,
                location=(side * (hw + 0.0005), y_pos, slide_center_z + 0.001),
                scale=(0.0035, 0.0026, height * 0.70),
                rotation=(chevron_angle, 0, 0)
            )
            scut = bpy.context.active_object
            scut.name = f"FrontSerr_{i}_{side}"
            bool_sc = slide.modifiers.new(f"FrontSerr_{i}_{side}", type='BOOLEAN')
            bool_sc.operation = 'DIFFERENCE'
            bool_sc.object = scut
            scut.hide_render = True
            scut.hide_viewport = True

    # 3. THREADED BARREL & KNURLED CAP
    barrel_y_start = 0.040
    barrel_y_end = y_front + 0.024
    barrel_len = barrel_y_end - barrel_y_start
    barrel_center_y = (barrel_y_start + barrel_y_end) / 2.0
    barrel_z = slide_base_z + 0.0135

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32, radius=0.0075, depth=barrel_len,
        location=(0.0, barrel_center_y, barrel_z),
        rotation=(math.radians(90), 0, 0)
    )
    barrel = bpy.context.active_object
    barrel.name = "Barrel_Outer"
    assign_material(barrel, hardware_mat)

    # 9mm Bore Hole
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32, radius=0.0045, depth=0.035,
        location=(0.0, barrel_y_end - 0.010, barrel_z),
        rotation=(math.radians(90), 0, 0)
    )
    bore = bpy.context.active_object
    bore.name = "BoreCutter"
    bool_b = barrel.modifiers.new("BoreCut", type='BOOLEAN')
    bool_b.operation = 'DIFFERENCE'
    bool_b.object = bore
    bore.hide_render = True
    bore.hide_viewport = True

    # Thread Protector Collar (knurled cap)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32, radius=0.0092, depth=0.016,
        location=(0.0, barrel_y_end - 0.008, barrel_z),
        rotation=(math.radians(90), 0, 0)
    )
    cap = bpy.context.active_object
    cap.name = "Barrel_ThreadProtector"
    assign_material(cap, hardware_mat)
    bev_c = cap.modifiers.new("Bevel", type='BEVEL')
    bev_c.width = 0.001
    bev_c.segments = 2

    for k in range(3):
        bpy.ops.mesh.primitive_torus_add(
            major_segments=32, minor_segments=8,
            major_radius=0.0092, minor_radius=0.0006,
            location=(0.0, barrel_y_end - 0.013 + k * 0.0045, barrel_z),
            rotation=(math.radians(90), 0, 0)
        )
        t_ring = bpy.context.active_object
        t_ring.name = f"ThreadRing_{k}"
        assign_material(t_ring, hardware_mat)

    # 4. THREE-DOT COMBAT SIGHTS
    slide_top_z = slide_base_z + height

    # Rear Sight
    rear_sight_y = y_rear + 0.015
    bpy.ops.mesh.primitive_cube_add(
        size=1.0, location=(0.0, rear_sight_y, slide_top_z + 0.004),
        scale=(0.024, 0.012, 0.008)
    )
    rear_sight = bpy.context.active_object
    rear_sight.name = "Sight_Rear"
    assign_material(rear_sight, hardware_mat)
    bev_rs = rear_sight.modifiers.new("Bevel", type='BEVEL')
    bev_rs.width = 0.0008
    bev_rs.segments = 2

    bpy.ops.mesh.primitive_cube_add(
        size=1.0, location=(0.0, rear_sight_y, slide_top_z + 0.007),
        scale=(0.0035, 0.014, 0.005)
    )
    notch = bpy.context.active_object
    notch.name = "NotchCutter"
    bool_nc = rear_sight.modifiers.new("NotchCut", type='BOOLEAN')
    bool_nc.operation = 'DIFFERENCE'
    bool_nc.object = notch
    notch.hide_render = True
    notch.hide_viewport = True

    for s in [-1, 1]:
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=16, radius=0.0009, depth=0.001,
            location=(s * 0.0055, rear_sight_y - 0.0061, slide_top_z + 0.005),
            rotation=(math.radians(90), 0, 0)
        )
        rdot = bpy.context.active_object
        rdot.name = f"RearDot_{s}"
        assign_material(rdot, sight_mat)

    # Front Sight Blade
    front_sight_y = y_front - 0.014
    bpy.ops.mesh.primitive_cube_add(
        size=1.0, location=(0.0, front_sight_y, slide_top_z + 0.004),
        scale=(0.0042, 0.011, 0.0075)
    )
    front_sight = bpy.context.active_object
    front_sight.name = "Sight_Front"
    assign_material(front_sight, hardware_mat)
    bev_fs = front_sight.modifiers.new("Bevel", type='BEVEL')
    bev_fs.width = 0.0006
    bev_fs.segments = 2

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=16, radius=0.0009, depth=0.001,
        location=(0.0, front_sight_y - 0.0056, slide_top_z + 0.0055),
        rotation=(math.radians(90), 0, 0)
    )
    fdot = bpy.context.active_object
    fdot.name = "FrontDot"
    assign_material(fdot, sight_mat)

# ─────────────────────────────────────────
# Model dispatcher
# ─────────────────────────────────────────
MODEL_BUILDERS = {
    # Low-poly (EEVEE)
    "low_poly_oak_tree":   make_low_poly_oak_tree,
    "sci_fi_crate":        make_sci_fi_crate,
    "medieval_barrel":     make_medieval_barrel,
    "simple_rock_boulder": make_simple_rock,
    "wooden_chest":        make_wooden_chest,
    "pine_tree":           make_pine_tree,
    "sword_basic":         make_sword,
    "street_lamp":         make_street_lamp,
    "mushroom_giant":      make_mushroom,
    "simple_house":        make_simple_house,
    # High-poly photorealistic (Cycles)
    "hp_tactical_pistol":  make_hp_tactical_pistol,
    "hp_modern_chair":     make_hp_modern_chair,
    "hp_ceramic_vase":     make_hp_ceramic_vase,
    "hp_gem_crystal":      make_hp_gem_crystal,
    "hp_goblet":           make_hp_goblet,
    "hp_wine_bottle":      make_hp_wine_bottle,
    "hp_chess_king":       make_hp_chess_king,
    "hp_apple":            make_hp_apple,
    "hp_lantern":          make_hp_lantern,
    "hp_crown":            make_hp_crown,
}

# ─────────────────────────────────────────
# Export helpers
# ─────────────────────────────────────────
def select_model_objects():
    """Select all mesh objects (not camera, lights, empties)."""
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            obj.select_set(True)
    bpy.context.view_layer.objects.active = next(
        (o for o in bpy.context.scene.objects if o.type == 'MESH'), None
    )

def export_glb(path):
    select_model_objects()
    bpy.ops.export_scene.gltf(
        filepath=path,
        use_selection=True,
        export_format='GLB',
        export_materials='EXPORT',
        export_texcoords=True,
        export_normals=True,
    )

def export_fbx(path):
    select_model_objects()
    bpy.ops.export_scene.fbx(
        filepath=path,
        use_selection=True,
        apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_NONE',
        bake_space_transform=False,
        mesh_smooth_type='FACE',
    )

def export_obj(path):
    select_model_objects()
    bpy.ops.wm.obj_export(
        filepath=path,
        export_selected_objects=True,
        export_materials=True,
        export_uv=True,
    )

# ─────────────────────────────────────────
# Render from multiple angles with auto-framing
# ─────────────────────────────────────────
def get_scene_bounds():
    import mathutils
    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')
    has_mesh = False
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            has_mesh = True
            for corner in obj.bound_box:
                world_c = obj.matrix_world @ mathutils.Vector(corner)
                min_x = min(min_x, world_c.x)
                max_x = max(max_x, world_c.x)
                min_y = min(min_y, world_c.y)
                max_y = max(max_y, world_c.y)
                min_z = min(min_z, world_c.z)
                max_z = max(max_z, world_c.z)
    if not has_mesh:
        return (0.0, 0.0, 0.5), 1.5
    center = ((min_x + max_x) / 2, (min_y + max_y) / 2, (min_z + max_z) / 2)
    max_dim = max(max_x - min_x, max_y - min_y, max_z - min_z)
    return center, max(max_dim, 0.4)

def render_previews(output_dir, resolution, samples, render_mode='eevee'):
    # Remove any previous cameras
    for obj in bpy.context.scene.objects:
        if obj.type in ('CAMERA', 'EMPTY'):
            obj.select_set(True)
        else:
            obj.select_set(False)
    bpy.ops.object.delete()

    setup_render(resolution, samples, "", render_mode=render_mode)
    center, max_dim = get_scene_bounds()
    dist = max_dim * 2.3

    angles = [
        ("perspective", (center[0] + dist * 0.72, center[1] - dist * 0.72, center[2] + dist * 0.50), center),
        ("front",       (center[0],               center[1] - dist * 1.05, center[2] + dist * 0.15), center),
        ("side",        (center[0] + dist * 1.05, center[1],               center[2] + dist * 0.15), center),
        ("top",         (center[0],               center[1],               center[2] + dist * 1.30), center),
    ]

    for angle_name, cam_loc, target_loc in angles:
        add_camera(location=cam_loc, look_at=target_loc)
        out_path = os.path.join(output_dir, f"preview_{angle_name}.png")
        bpy.context.scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)

        # Remove camera + target for next iteration
        for obj in bpy.context.scene.objects:
            if obj.type in ('CAMERA', 'EMPTY'):
                obj.select_set(True)
            else:
                obj.select_set(False)
        bpy.ops.object.delete()

# ─────────────────────────────────────────
# Main
# ─────────────────────────────────────────
def main():
    args = get_args()

    with open(args.category_file, 'r', encoding='utf-8') as f:
        categories = json.load(f)

    idx = args.model_index % len(categories)
    model_data = categories[idx]
    model_name = model_data["name"]
    is_high_poly = model_data.get("style") in ("photorealistic", "high_poly") or model_name.startswith("hp_")

    print(f"\n=== Generating model: {model_data['display_name']} ({'High Poly / Cycles' if is_high_poly else 'Low Poly / Eevee'}) ===\n")

    os.makedirs(args.output_dir, exist_ok=True)

    # ── 1. Clear scene ──
    clear_scene()

    # ── 2. Build model ──
    builder = MODEL_BUILDERS.get(model_name)
    if not builder:
        print(f"ERROR: No builder found for '{model_name}'")
        sys.exit(1)
    builder(model_data)

    # ── 3. Apply transforms ──
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    # ── 4. Set up lights & world ──
    if is_high_poly:
        add_studio_lights()
        add_studio_world()
        render_mode = 'cycles'
        # For Cycles preview, 32 samples with denoiser is fast & ultra clean
        render_samples = min(args.samples, 32)
    else:
        add_lights()
        add_world_background()
        render_mode = 'eevee'
        render_samples = args.samples

    # ── 5. Render preview images ──
    render_previews(args.output_dir, args.resolution, render_samples, render_mode=render_mode)

    # ── 6. Export formats ──
    glb_path = os.path.join(args.output_dir, f"{model_name}.glb")
    fbx_path = os.path.join(args.output_dir, f"{model_name}.fbx")
    obj_path = os.path.join(args.output_dir, f"{model_name}.obj")

    print("Exporting GLB...")
    export_glb(glb_path)
    print("Exporting FBX...")
    export_fbx(fbx_path)
    print("Exporting OBJ...")
    export_obj(obj_path)

    print(f"\nDone! Files saved to: {args.output_dir}")

main()

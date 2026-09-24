"""
Tactical Combat Pistol V5 - High Fidelity Organic Receiver & Precision Slide
Recreates the exact silhouette, mechanical features, and studio lighting of the concept art:
- Seamless single-mesh polymer frame with continuous trigger guard, finger grooves, flared magwell, and swept beavertail
- CNC slide with 45° top chamfers, tactical bull-nose taper, angled chevron serrations, and ejection port
- Threaded barrel with knurled cap
- Combat sights with 3 luminous dots
- Dual-tone PBR materials (matte nitride steel & stippled polymer)
- Heroic 3/4 front angle & studio lighting
"""

import bpy
import bmesh
import math
from mathutils import Vector, Euler, Matrix
import os

def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if not bpy.data.scenes:
        bpy.data.scenes.new("Scene")

def create_materials():
    # 1. Slide Nitride Matte Steel (dark charcoal slate)
    mat_slide = bpy.data.materials.new(name="Mat_SlideSteel")
    mat_slide.use_nodes = True
    nodes = mat_slide.node_tree.nodes
    links = mat_slide.node_tree.links
    nodes.clear()
    
    out_node = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.04, 0.042, 0.045, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.92
    bsdf.inputs['Roughness'].default_value = 0.35
    links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])
    
    # 2. Polymer Frame (Matte dark grey/black with micro roughness)
    mat_frame = bpy.data.materials.new(name="Mat_PolymerFrame")
    mat_frame.use_nodes = True
    nodes = mat_frame.node_tree.nodes
    links = mat_frame.node_tree.links
    nodes.clear()
    
    out_node = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.03, 0.032, 0.035, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.02
    bsdf.inputs['Roughness'].default_value = 0.55
    links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])
    
    # 3. Grip Stippling Panel (Tactical non-slip stipple)
    mat_stipple = bpy.data.materials.new(name="Mat_GripStipple")
    mat_stipple.use_nodes = True
    nodes = mat_stipple.node_tree.nodes
    links = mat_stipple.node_tree.links
    nodes.clear()
    
    out_node = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.02, 0.02, 0.022, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.0
    bsdf.inputs['Roughness'].default_value = 0.8
    
    tex_voronoi = nodes.new(type='ShaderNodeTexVoronoi')
    tex_voronoi.inputs['Scale'].default_value = 400.0
    bump = nodes.new(type='ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.15
    bump.inputs['Distance'].default_value = 0.003
    links.new(tex_voronoi.outputs['Distance'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])
    
    # 4. Hardware Steel (Barrel, pins, controls, sights)
    mat_hardware = bpy.data.materials.new(name="Mat_Hardware")
    mat_hardware.use_nodes = True
    nodes = mat_hardware.node_tree.nodes
    links = mat_hardware.node_tree.links
    nodes.clear()
    
    out_node = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.03, 0.032, 0.035, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.96
    bsdf.inputs['Roughness'].default_value = 0.22
    links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])
    
    # 5. Night Sight Dots (Crisp white luminescence)
    mat_dots = bpy.data.materials.new(name="Mat_SightDots")
    mat_dots.use_nodes = True
    nodes = mat_dots.node_tree.nodes
    links = mat_dots.node_tree.links
    nodes.clear()
    
    out_node = nodes.new(type='ShaderNodeOutputMaterial')
    emit = nodes.new(type='ShaderNodeEmission')
    emit.inputs['Color'].default_value = (0.95, 1.0, 0.95, 1.0)
    emit.inputs['Strength'].default_value = 5.0
    links.new(emit.outputs['Emission'], out_node.inputs['Surface'])

    # 6. Safety Trigger Blade (Red combat accent)
    mat_red = bpy.data.materials.new(name="Mat_SafetyRed")
    mat_red.use_nodes = True
    nodes = mat_red.node_tree.nodes
    links = mat_red.node_tree.links
    nodes.clear()
    out_node = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.6, 0.05, 0.05, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.1
    bsdf.inputs['Roughness'].default_value = 0.4
    links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])
    
    return {
        'slide': mat_slide,
        'frame': mat_frame,
        'stipple': mat_stipple,
        'hardware': mat_hardware,
        'dots': mat_dots,
        'red': mat_red
    }


def build_unified_frame(materials):
    """
    Creates the complete ergonomic lower frame as a single continuous piece
    with seamless trigger guard, finger grooves, flared magwell, and beavertail.
    """
    curve_data = bpy.data.curves.new('PistolFrameCurve', type='CURVE')
    curve_data.dimensions = '2D'
    curve_data.extrude = 0.0135 # Full thickness 27mm
    curve_data.bevel_depth = 0.0018
    curve_data.bevel_resolution = 4
    curve_data.resolution_u = 16

    # Outer silhouette (in Curve X-Y plane: X = Gun Y length, Y = Gun Z height)
    outer = curve_data.splines.new('BEZIER')
    
    pts = [
        # (Gun Y, Gun Z)
        (+0.088, 0.072),  # 0: Front top of dust cover
        (+0.088, 0.051),  # 1: Front bottom lip of dust cover
        (+0.038, 0.049),  # 2: Rail end
        (+0.028, 0.026),  # 3: Trigger guard front corner
        (+0.023, 0.022),  # 4: Combat front finger hook
        (+0.005, 0.021),  # 5: Trigger guard bottom
        (-0.018, 0.024),  # 6: Trigger guard rear bottom
        (-0.021, 0.032),  # 7: Transition into front strap
        (-0.025, 0.018),  # 8: Finger groove 1
        (-0.023, 0.008),  # 9: Finger ridge 1
        (-0.030, -0.006), # 10: Finger groove 2
        (-0.028, -0.016), # 11: Finger ridge 2
        (-0.038, -0.035), # 12: Finger groove 3
        (-0.037, -0.048), # 13: Grip front lip above magwell
        (-0.040, -0.054), # 14: Magwell front base
        (-0.076, -0.054), # 15: Magwell rear base
        (-0.078, -0.046), # 16: Grip heel
        (-0.072, -0.010), # 17: Backstrap palm swell
        (-0.058, 0.028),  # 18: Upper backstrap
        (-0.046, 0.048),  # 19: Beavertail throat (deep notch)
        (-0.082, 0.063),  # 20: Beavertail horn tip
        (-0.078, 0.072)   # 21: Frame rear top under slide
    ]
    
    outer.bezier_points.add(len(pts) - 1)
    for idx, (py, pz) in enumerate(pts):
        bp = outer.bezier_points[idx]
        bp.co = (py, pz, 0.0)
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'
    outer.use_cyclic_u = True

    # Inner cutout for trigger opening
    inner = curve_data.splines.new('BEZIER')
    inner_pts = [
        (+0.021, 0.048), # Under dust cover front
        (+0.021, 0.028), # Trigger guard inside front
        (+0.005, 0.027), # Trigger guard inside bottom
        (-0.013, 0.030), # Trigger guard inside rear
        (-0.013, 0.048), # Trigger cavity root
    ]
    inner.bezier_points.add(len(inner_pts) - 1)
    for idx, (py, pz) in enumerate(inner_pts):
        bp = inner.bezier_points[idx]
        bp.co = (py, pz, 0.0)
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'
    inner.use_cyclic_u = True

    frame_obj = bpy.data.objects.new("Pistol_Receiver", curve_data)
    bpy.context.collection.objects.link(frame_obj)
    
    # Orient to world: X is width, Y is length, Z is height
    frame_obj.rotation_euler = (math.radians(90), 0, math.radians(90))
    frame_obj.data.materials.append(materials['frame'])

    # Convert curve to mesh so we can cut rails, add modifiers, etc.
    bpy.context.view_layer.objects.active = frame_obj
    frame_obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    
    # 2. Picatinny Rail Cross-Slots under dust cover
    for r in range(4):
        slot_y = 0.045 + r * 0.010
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(0.0, slot_y, 0.049),
            scale=(0.032, 0.0046, 0.004)
        )
        slot_cut = bpy.context.active_object
        slot_cut.name = f"RailSlot_{r}"
        bool_r = frame_obj.modifiers.new(f"RailSlotBool_{r}", type='BOOLEAN')
        bool_r.operation = 'DIFFERENCE'
        bool_r.object = slot_cut
        slot_cut.hide_render = True
        slot_cut.hide_viewport = True

    # 3. Tactical Grip Stippling Panels (Left & Right side inserts)
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(side * 0.0138, -0.052, -0.014),
            scale=(0.0015, 0.026, 0.065),
            rotation=(math.radians(-16), 0, 0)
        )
        stipple = bpy.context.active_object
        stipple.name = f"GripStipple_{side}"
        stipple.data.materials.append(materials['stipple'])
        bev_s = stipple.modifiers.new("Bevel", type='BEVEL')
        bev_s.width = 0.001
        bev_s.segments = 2

    # 4. Flared Magazine Basepad
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, -0.058, -0.058),
        scale=(0.032, 0.044, 0.010),
        rotation=(math.radians(-16), 0, 0)
    )
    mag = bpy.context.active_object
    mag.name = "Magazine_Basepad"
    mag.data.materials.append(materials['frame'])
    bev_m = mag.modifiers.new("Bevel", type='BEVEL')
    bev_m.width = 0.002
    bev_m.segments = 3

    # 5. Realistic Trigger with Safety Blade
    # Main trigger shoe
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.004, 0.040),
        scale=(0.0055, 0.009, 0.018),
        rotation=(math.radians(20), 0, 0)
    )
    shoe = bpy.context.active_object
    shoe.name = "Trigger_Shoe"
    shoe.data.materials.append(materials['hardware'])
    bev_tr = shoe.modifiers.new("Bevel", type='BEVEL')
    bev_tr.width = 0.001
    bev_tr.segments = 2
    
    # Red safety blade in center of trigger
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.006, 0.039),
        scale=(0.0018, 0.008, 0.014),
        rotation=(math.radians(22), 0, 0)
    )
    blade = bpy.context.active_object
    blade.name = "Trigger_SafetyBlade"
    blade.data.materials.append(materials['red'])

    # 6. Mechanical Controls: Slide Lock Lever & Takedown Latch
    # Slide stop lever (left side)
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(-0.0145, -0.016, 0.069),
        scale=(0.0025, 0.016, 0.0045)
    )
    slide_stop = bpy.context.active_object
    slide_stop.name = "Control_SlideStop"
    slide_stop.data.materials.append(materials['hardware'])

    # Takedown catch (above trigger)
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.012, 0.065),
        scale=(0.029, 0.005, 0.0035)
    )
    takedown = bpy.context.active_object
    takedown.name = "Control_TakedownCatch"
    takedown.data.materials.append(materials['hardware'])

    # Frame pins
    for py, pz in [( -0.002, 0.065 ), ( -0.022, 0.062 )]:
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=16,
            radius=0.002,
            depth=0.0285,
            location=(0.0, py, pz),
            rotation=(0, math.radians(90), 0)
        )
        pin = bpy.context.active_object
        pin.name = f"FramePin_{py}"
        pin.data.materials.append(materials['hardware'])

    return frame_obj


def build_slide_and_barrel(materials):
    """
    Builds the precision CNC slide with 45° chamfers, tactical bull-nose taper,
    chevron cocking serrations, ejection port, barrel hood, threaded barrel, and sights.
    """
    length = 0.190
    width = 0.027
    height = 0.035
    hw = width / 2.0
    slide_base_z = 0.072
    slide_center_z = slide_base_z + height / 2.0
    slide_center_y = 0.006
    y_front = slide_center_y + length / 2.0
    y_rear = slide_center_y - length / 2.0
    
    # 1. Main Slide Block
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, slide_center_y, slide_center_z),
        scale=(width, length, height)
    )
    slide = bpy.context.active_object
    slide.name = "Pistol_Slide"
    slide.data.materials.append(materials['slide'])
    
    bev_s = slide.modifiers.new("Bevel", type='BEVEL')
    bev_s.width = 0.0028 # 45-degree chamfers on top edges
    bev_s.segments = 3
    bev_s.limit_method = 'ANGLE'
    bev_s.angle_limit = math.radians(35)
    
    # 2. Bull-nose Chamfers at Front
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(side * (hw + 0.004), y_front, slide_center_z),
            scale=(0.012, 0.026, height * 1.2),
            rotation=(0, 0, side * math.radians(30))
        )
        nose_cut = bpy.context.active_object
        nose_cut.name = f"NoseCutter_{side}"
        bool_n = slide.modifiers.new(f"NoseChamfer_{side}", type='BOOLEAN')
        bool_n.operation = 'DIFFERENCE'
        bool_n.object = nose_cut
        nose_cut.hide_render = True
        nose_cut.hide_viewport = True

    # 3. Ejection Port Cutout (right side & top)
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.008, -0.012, slide_base_z + height - 0.006),
        scale=(0.022, 0.035, 0.022)
    )
    ej_cut = bpy.context.active_object
    ej_cut.name = "EjectionCutter"
    bool_e = slide.modifiers.new("EjectionPortCut", type='BOOLEAN')
    bool_e.operation = 'DIFFERENCE'
    bool_e.object = ej_cut
    ej_cut.hide_render = True
    ej_cut.hide_viewport = True

    # 4. Chamber / Barrel Hood (visible in ejection port)
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, -0.012, slide_base_z + height * 0.46),
        scale=(width * 0.84, 0.033, height * 0.72)
    )
    hood = bpy.context.active_object
    hood.name = "Barrel_ChamberHood"
    hood.data.materials.append(materials['hardware'])
    bev_h = hood.modifiers.new("Bevel", type='BEVEL')
    bev_h.width = 0.001
    bev_h.segments = 2

    # 5. Angled Chevron Cocking Serrations (Front and Rear, 20° forward rake)
    # Rear Serrations
    for i in range(6):
        y_pos = y_rear + 0.016 + i * 0.0055
        for side in [-1, 1]:
            bpy.ops.mesh.primitive_cube_add(
                size=1.0,
                location=(side * hw, y_pos, slide_center_z + 0.002),
                scale=(0.0025, 0.0022, height * 0.65),
                rotation=(0, side * math.radians(20), 0)
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
        y_pos = y_front - 0.052 + i * 0.0055
        for side in [-1, 1]:
            bpy.ops.mesh.primitive_cube_add(
                size=1.0,
                location=(side * hw, y_pos, slide_center_z + 0.002),
                scale=(0.0025, 0.0022, height * 0.65),
                rotation=(0, side * math.radians(20), 0)
            )
            scut = bpy.context.active_object
            scut.name = f"FrontSerr_{i}_{side}"
            bool_sc = slide.modifiers.new(f"FrontSerr_{i}_{side}", type='BOOLEAN')
            bool_sc.operation = 'DIFFERENCE'
            bool_sc.object = scut
            scut.hide_render = True
            scut.hide_viewport = True

    # 6. Extended Threaded Barrel & Knurled Thread Protector
    barrel_y_start = 0.040
    barrel_y_end = y_front + 0.024
    barrel_len = barrel_y_end - barrel_y_start
    barrel_center_y = (barrel_y_start + barrel_y_end) / 2.0
    barrel_z = slide_base_z + 0.0135
    
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=0.0075,
        depth=barrel_len,
        location=(0.0, barrel_center_y, barrel_z),
        rotation=(math.radians(90), 0, 0)
    )
    barrel = bpy.context.active_object
    barrel.name = "Barrel_Outer"
    barrel.data.materials.append(materials['hardware'])
    
    # 9mm Bore Hole
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=0.0045,
        depth=0.035,
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

    # Thread Protector Collar (knurled muzzle cap)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=0.0092,
        depth=0.016,
        location=(0.0, barrel_y_end - 0.008, barrel_z),
        rotation=(math.radians(90), 0, 0)
    )
    cap = bpy.context.active_object
    cap.name = "Barrel_ThreadProtector"
    cap.data.materials.append(materials['hardware'])
    bev_c = cap.modifiers.new("Bevel", type='BEVEL')
    bev_c.width = 0.001
    bev_c.segments = 2
    
    # Knurling rings on thread cap
    for k in range(3):
        bpy.ops.mesh.primitive_torus_add(
            major_segments=32,
            minor_segments=8,
            major_radius=0.0092,
            minor_radius=0.0006,
            location=(0.0, barrel_y_end - 0.013 + k * 0.0045, barrel_z),
            rotation=(math.radians(90), 0, 0)
        )
        t_ring = bpy.context.active_object
        t_ring.name = f"ThreadRing_{k}"
        t_ring.data.materials.append(materials['hardware'])

    # 7. Combat Iron Sights
    slide_top_z = slide_base_z + height
    
    # Rear Sight (Dovetail notch with 2 white dots)
    rear_sight_y = y_rear + 0.015
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, rear_sight_y, slide_top_z + 0.004),
        scale=(0.024, 0.012, 0.008)
    )
    rear_sight = bpy.context.active_object
    rear_sight.name = "Sight_Rear"
    rear_sight.data.materials.append(materials['hardware'])
    bev_rs = rear_sight.modifiers.new("Bevel", type='BEVEL')
    bev_rs.width = 0.0008
    bev_rs.segments = 2
    
    # U-Notch cutter
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, rear_sight_y, slide_top_z + 0.007),
        scale=(0.0035, 0.014, 0.005)
    )
    notch = bpy.context.active_object
    notch.name = "NotchCutter"
    bool_nc = rear_sight.modifiers.new("NotchCut", type='BOOLEAN')
    bool_nc.operation = 'DIFFERENCE'
    bool_nc.object = notch
    notch.hide_render = True
    notch.hide_viewport = True

    # Rear white dots
    for s in [-1, 1]:
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=16,
            radius=0.0009,
            depth=0.001,
            location=(s * 0.0055, rear_sight_y - 0.0061, slide_top_z + 0.005),
            rotation=(math.radians(90), 0, 0)
        )
        rdot = bpy.context.active_object
        rdot.name = f"RearDot_{s}"
        rdot.data.materials.append(materials['dots'])

    # Front Sight Blade (with 1 white dot)
    front_sight_y = y_front - 0.014
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, front_sight_y, slide_top_z + 0.004),
        scale=(0.0042, 0.011, 0.0075)
    )
    front_sight = bpy.context.active_object
    front_sight.name = "Sight_Front"
    front_sight.data.materials.append(materials['hardware'])
    bev_fs = front_sight.modifiers.new("Bevel", type='BEVEL')
    bev_fs.width = 0.0006
    bev_fs.segments = 2
    
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=16,
        radius=0.0009,
        depth=0.001,
        location=(0.0, front_sight_y - 0.0056, slide_top_z + 0.0055),
        rotation=(math.radians(90), 0, 0)
    )
    fdot = bpy.context.active_object
    fdot.name = "FrontDot"
    fdot.data.materials.append(materials['dots'])

    return slide


def setup_studio_lighting():
    """
    Photorealistic studio lighting tailored to gun product showcase:
    - Neutral light grey background with subtle vignette
    - Polished slate tabletop with reflective ground contact
    - Balanced 3-point studio lighting (Soft Key, Directional Rim, Crisp Fill)
    """
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        # Subtle light studio background gradient
        bg.inputs['Color'].default_value = (0.75, 0.78, 0.82, 1.0)
        bg.inputs['Strength'].default_value = 0.35

    # Studio Tabletop
    mat_table = bpy.data.materials.new(name="Mat_Tabletop")
    mat_table.use_nodes = True
    nodes = mat_table.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.20, 0.22, 0.25, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.25
        bsdf.inputs['Metallic'].default_value = 0.1
        
    bpy.ops.mesh.primitive_plane_add(
        size=10.0,
        location=(0.0, 0.0, -0.063) # Just under the magazine basepad
    )
    table = bpy.context.active_object
    table.name = "Studio_Table"
    table.data.materials.append(mat_table)

    # 1. Key Light (Broad overhead softbox at 45°)
    key_data = bpy.data.lights.new(name="Light_Key", type='AREA')
    key_data.energy = 45.0
    key_data.size = 0.7
    key_data.color = (1.0, 0.98, 0.95)
    key_obj = bpy.data.objects.new("Light_Key", key_data)
    bpy.context.collection.objects.link(key_obj)
    key_obj.location = (-0.45, 0.25, 0.55)
    key_obj.rotation_euler = (math.radians(45), math.radians(-30), math.radians(-50))

    # 2. Fill Light (Soft cool fill from the right side)
    fill_data = bpy.data.lights.new(name="Light_Fill", type='AREA')
    fill_data.energy = 20.0
    fill_data.size = 0.9
    fill_data.color = (0.9, 0.95, 1.0)
    fill_obj = bpy.data.objects.new("Light_Fill", fill_data)
    bpy.context.collection.objects.link(fill_obj)
    fill_obj.location = (0.50, -0.20, 0.35)
    fill_obj.rotation_euler = (math.radians(40), math.radians(40), math.radians(130))

    # 3. Rim / Edge Strip Light (creates high-contrast highlight along the top chamfers and slide)
    rim_data = bpy.data.lights.new(name="Light_Rim", type='AREA')
    rim_data.energy = 65.0
    rim_data.size = 0.1
    rim_data.size_y = 1.0
    rim_data.color = (1.0, 1.0, 1.0)
    rim_obj = bpy.data.objects.new("Light_Rim", rim_data)
    bpy.context.collection.objects.link(rim_obj)
    rim_obj.location = (0.25, -0.50, 0.50)
    rim_obj.rotation_euler = (math.radians(-40), math.radians(25), math.radians(150))


def render_studio_views(output_dir):
    """
    Renders 4 camera perspectives:
    - preview_perspective.png (Matching the concept art beauty 3/4 angle!)
    - preview_side.png (Side technical profile)
    - preview_front.png (Front muzzle & sight view)
    - preview_top.png (Top slide & ejection port)
    """
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'RenderSettings') and 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.film_transparent = False
    
    # Camera
    cam_data = bpy.data.cameras.new("StudioCamera")
    cam_data.lens = 70 # 70mm lens gives cinematic weapon focal length
    cam_obj = bpy.data.objects.new("StudioCamera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # Target tracking empty at center of gun
    target = bpy.data.objects.new("CamTarget", None)
    target.location = (0.0, 0.015, 0.035)
    bpy.context.collection.objects.link(target)
    
    const = cam_obj.constraints.new(type='TRACK_TO')
    const.target = target
    const.track_axis = 'TRACK_NEGATIVE_Z'
    const.up_axis = 'UP_Y'

    # 1. Perspective View - MATCHING CONCEPT ART EXACTLY!
    # Looking from front-left towards center-rear, slightly elevated
    cam_obj.location = (-0.38, 0.32, 0.18)
    bpy.context.view_layer.update()
    scene.render.filepath = os.path.join(output_dir, "preview_perspective.png")
    print("Rendering perspective view (Heroic 3/4)...")
    bpy.ops.render.render(write_still=True)

    # 2. Side View
    cam_obj.location = (-0.52, 0.015, 0.035)
    bpy.context.view_layer.update()
    scene.render.filepath = os.path.join(output_dir, "preview_side.png")
    print("Rendering side view...")
    bpy.ops.render.render(write_still=True)

    # 3. Front View (Muzzle focus)
    cam_obj.location = (-0.25, 0.46, 0.12)
    bpy.context.view_layer.update()
    scene.render.filepath = os.path.join(output_dir, "preview_front.png")
    print("Rendering front view...")
    bpy.ops.render.render(write_still=True)

    # 4. Top View (Slide & sight alignment)
    cam_obj.location = (-0.10, -0.15, 0.52)
    bpy.context.view_layer.update()
    scene.render.filepath = os.path.join(output_dir, "preview_top.png")
    print("Rendering top view...")
    bpy.ops.render.render(write_still=True)


def export_assets(output_dir, model_name="hp_tactical_pistol"):
    """
    Exports GLB, FBX, and OBJ formats.
    """
    table = bpy.data.objects.get("Studio_Table")
    if table:
        bpy.data.objects.remove(table, do_unlink=True)
        
    bpy.ops.object.select_all(action='DESELECT')
    mesh_count = 0
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            mesh_count += 1
            
    print(f"Exporting {mesh_count} meshes to GLB, FBX, and OBJ...")
    
    glb_path = os.path.join(output_dir, f"{model_name}.glb")
    bpy.ops.export_scene.gltf(
        filepath=glb_path,
        export_format='GLB',
        use_selection=True,
        export_apply=True
    )
    
    fbx_path = os.path.join(output_dir, f"{model_name}.fbx")
    bpy.ops.export_scene.fbx(
        filepath=fbx_path,
        use_selection=True,
        apply_scale_options='FBX_SCALE_ALL'
    )
    
    obj_path = os.path.join(output_dir, f"{model_name}.obj")
    bpy.ops.wm.obj_export(
        filepath=obj_path,
        export_selected_objects=True
    )
    print(f"[SUCCESS] Exported 3D assets to {output_dir}")


def main():
    output_dir = r"c:\Users\Sunu\Documents\home\zaigopc\Desktop\personal\automate\output\2026-09-21_hp_tactical_pistol"
    os.makedirs(output_dir, exist_ok=True)
    
    clean_scene()
    mats = create_materials()
    build_unified_frame(mats)
    build_slide_and_barrel(mats)
    setup_studio_lighting()
    render_studio_views(output_dir)
    export_assets(output_dir)
    print("[COMPLETE] Tactical Pistol V5 generation and rendering finished successfully!")

if __name__ == "__main__":
    main()

import bpy
import bmesh
import math
import os

def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if not bpy.data.scenes:
        bpy.data.scenes.new("Scene")

def create_materials():
    mat_titanium = bpy.data.materials.new(name="Mat_NaturalTitanium")
    mat_titanium.use_nodes = True
    nodes = mat_titanium.node_tree.nodes
    links = mat_titanium.node_tree.links
    nodes.clear()
    out_node = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.35, 0.355, 0.36, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.98
    bsdf.inputs['Roughness'].default_value = 0.24
    tex_noise = nodes.new(type='ShaderNodeTexNoise')
    tex_noise.inputs['Scale'].default_value = 500.0
    tex_noise.inputs['Detail'].default_value = 5.0
    bump = nodes.new(type='ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.012
    bump.inputs['Distance'].default_value = 0.001
    links.new(tex_noise.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])

    mat_backglass = bpy.data.materials.new(name="Mat_FrostedBackGlass")
    mat_backglass.use_nodes = True
    nodes = mat_backglass.node_tree.nodes
    links = mat_backglass.node_tree.links
    nodes.clear()
    out_node = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.08, 0.085, 0.09, 1.0) # Darker, moodier matte titanium
    bsdf.inputs['Metallic'].default_value = 0.35
    bsdf.inputs['Roughness'].default_value = 0.42
    links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])

    mat_plateau = bpy.data.materials.new(name="Mat_CameraPlateau")
    mat_plateau.use_nodes = True
    nodes = mat_plateau.node_tree.nodes
    links = mat_plateau.node_tree.links
    nodes.clear()
    out_node = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.05, 0.055, 0.06, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.30
    bsdf.inputs['Roughness'].default_value = 0.05
    links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])

    mat_lensring = bpy.data.materials.new(name="Mat_LensTrimRing")
    mat_lensring.use_nodes = True
    nodes = mat_lensring.node_tree.nodes
    links = mat_lensring.node_tree.links
    nodes.clear()
    out_node = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.50, 0.51, 0.53, 1.0)
    bsdf.inputs['Metallic'].default_value = 1.0
    bsdf.inputs['Roughness'].default_value = 0.12
    links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])

    mat_lensglass = bpy.data.materials.new(name="Mat_SapphireLens")
    mat_lensglass.use_nodes = True
    nodes = mat_lensglass.node_tree.nodes
    links = mat_lensglass.node_tree.links
    nodes.clear()
    out_node = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.015, 0.02, 0.025, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.05
    bsdf.inputs['Roughness'].default_value = 0.01
    bsdf.inputs['Transmission Weight'].default_value = 0.90
    bsdf.inputs['IOR'].default_value = 1.55
    links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])

    mat_pupil = bpy.data.materials.new(name="Mat_CameraPupil")
    mat_pupil.use_nodes = True
    nodes = mat_pupil.node_tree.nodes
    links = mat_pupil.node_tree.links
    nodes.clear()
    out_node = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.008, 0.008, 0.012, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.8
    bsdf.inputs['Roughness'].default_value = 0.15
    links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])

    mat_oled = bpy.data.materials.new(name="Mat_OLEDDisplay")
    mat_oled.use_nodes = True
    nodes = mat_oled.node_tree.nodes
    links = mat_oled.node_tree.links
    nodes.clear()
    out_node = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.005, 0.006, 0.007, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.05
    bsdf.inputs['Roughness'].default_value = 0.015
    links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])

    mat_flash = bpy.data.materials.new(name="Mat_Flash")
    mat_flash.use_nodes = True
    nodes = mat_flash.node_tree.nodes
    links = mat_flash.node_tree.links
    nodes.clear()
    out_node = nodes.new(type='ShaderNodeOutputMaterial')
    emit = nodes.new(type='ShaderNodeEmission')
    emit.inputs['Color'].default_value = (1.0, 0.96, 0.88, 1.0)
    emit.inputs['Strength'].default_value = 3.0
    links.new(emit.outputs['Emission'], out_node.inputs['Surface'])

    mat_dark = bpy.data.materials.new(name="Mat_DarkResin")
    mat_dark.use_nodes = True
    nodes = mat_dark.node_tree.nodes
    links = mat_dark.node_tree.links
    nodes.clear()
    out_node = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.04, 0.04, 0.045, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.0
    bsdf.inputs['Roughness'].default_value = 0.5
    links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])

    return {
        'titanium': mat_titanium,
        'backglass': mat_backglass,
        'plateau': mat_plateau,
        'lensring': mat_lensring,
        'lensglass': mat_lensglass,
        'pupil': mat_pupil,
        'oled': mat_oled,
        'flash': mat_flash,
        'dark': mat_dark
    }

def create_rounded_chassis(w, h, d, corner_radius, bev_radius, name, material):
    bm = bmesh.new()
    segments = 16
    pts = []
    cx_max = w/2.0 - corner_radius
    cx_min = -w/2.0 + corner_radius
    cz_max = h - corner_radius
    cz_min = corner_radius
    
    corners = [
        (cx_max, cz_max, 0.0, math.pi/2.0),
        (cx_min, cz_max, math.pi/2.0, math.pi),
        (cx_min, cz_min, math.pi, 3*math.pi/2.0),
        (cx_max, cz_min, 3*math.pi/2.0, 2*math.pi),
    ]
    
    for cx, cz, a_start, a_end in corners:
        for i in range(segments):
            angle = a_start + (a_end - a_start) * (i / segments)
            px = cx + corner_radius * math.cos(angle)
            pz = cz + corner_radius * math.sin(angle)
            pts.append((px, pz))
            
    y_front = d / 2.0
    y_back = -d / 2.0
    front_verts = [bm.verts.new((x, y_front, z)) for x, z in pts]
    back_verts = [bm.verts.new((x, y_back, z)) for x, z in pts]
    bm.verts.ensure_lookup_table()
    
    num_pts = len(pts)
    for i in range(num_pts):
        next_i = (i + 1) % num_pts
        bm.faces.new([front_verts[i], front_verts[next_i], back_verts[next_i], back_verts[i]])
        
    bm.faces.new(front_verts)
    bm.faces.new(reversed(back_verts))
    
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    
    if bev_radius > 0:
        bev = obj.modifiers.new("PerimeterBevel", type='BEVEL')
        bev.width = bev_radius
        bev.segments = 4
        bev.limit_method = 'ANGLE'
        bev.angle_limit = math.radians(45)
        
    for poly in obj.data.polygons:
        poly.use_smooth = True
        
    return obj

def build_iphone_17_pro(materials):
    w = 0.0715
    h = 0.1496
    d = 0.00825
    r_corner = 0.011
    
    chassis = create_rounded_chassis(w, h, d, r_corner, 0.0009, "iPhone_TitaniumChassis", materials['titanium'])
    
    back_glass = create_rounded_chassis(w - 0.0016, h - 0.0016, 0.0006, r_corner - 0.0008, 0.0002, "iPhone_BackGlass", materials['backglass'])
    back_glass.location = (0, -d/2.0 - 0.0001, 0.0008)
    
    front_screen = create_rounded_chassis(w - 0.0016, h - 0.0016, 0.0006, r_corner - 0.0008, 0.0002, "iPhone_DisplayScreen", materials['oled'])
    front_screen.location = (0, d/2.0 + 0.0001, 0.0008)
    
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, d/2.0 + 0.0005, h - 0.012), scale=(0.018, 0.0004, 0.0055))
    island = bpy.context.active_object
    island.name = "Display_DynamicIsland"
    island.data.materials.append(materials['dark'])
    bev_di = island.modifiers.new("PillBevel", type='BEVEL')
    bev_di.width = 0.0024
    bev_di.segments = 6
    
    for az in [0.032, 0.118]:
        for side_x in [-w/2.0, w/2.0]:
            bpy.ops.mesh.primitive_cube_add(size=1.0, location=(side_x, 0.0, az), scale=(0.0006, d * 1.02, 0.0012))
            ant = bpy.context.active_object
            ant.name = f"AntennaBand_{side_x}_{az}"
            ant.data.materials.append(materials['dark'])
            
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-w/2.0 - 0.0004, 0.0, 0.115), scale=(0.0008, 0.0022, 0.010))
    b_act = bpy.context.active_object
    b_act.name = "Button_Action"
    b_act.data.materials.append(materials['titanium'])
    b_act.modifiers.new("Bv", type='BEVEL').width = 0.0004
    
    for vy, vname in [(0.096, "VolumeUp"), (0.076, "VolumeDown")]:
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-w/2.0 - 0.0004, 0.0, vy), scale=(0.0008, 0.0022, 0.014))
        b_vol = bpy.context.active_object
        b_vol.name = f"Button_{vname}"
        b_vol.data.materials.append(materials['titanium'])
        b_vol.modifiers.new("Bv", type='BEVEL').width = 0.0004

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(w/2.0 + 0.0004, 0.0, 0.098), scale=(0.0008, 0.0022, 0.020))
    b_pwr = bpy.context.active_object
    b_pwr.name = "Button_Power"
    b_pwr.data.materials.append(materials['titanium'])
    b_pwr.modifiers.new("Bv", type='BEVEL').width = 0.0004

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(w/2.0 + 0.0002, 0.0, 0.046), scale=(0.0005, 0.0026, 0.017))
    b_cam = bpy.context.active_object
    b_cam.name = "Button_CameraControl"
    b_cam.data.materials.append(materials['titanium'])

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0008), scale=(0.0085, 0.0028, 0.0018))
    usbc = bpy.context.active_object
    usbc.name = "Port_USBC"
    usbc.data.materials.append(materials['dark'])
    
    island_x = -0.0180
    island_z = 0.1260 # Moved up slightly to be proportional
    island_y = -d/2.0 - 0.0025 # Inset into backplate
    island_w = 0.0385
    island_h = 0.0385
    island_thick = 0.0028
    
    # Since create_rounded_chassis makes it facing Y, we don't need to rotate it!
    # Just translate it so it sits on the backplate.
    plateau = create_rounded_chassis(island_w, island_h, island_thick, 0.0085, 0.0006, "Camera_IslandPlateau", materials['plateau'])
    plateau.location = (island_x, island_y, island_z - island_h/2.0)

    
    lenses = [("MainWide", island_x - 0.0090, island_z + 0.0090), ("UltraWide", island_x - 0.0090, island_z - 0.0090), ("Telephoto", island_x + 0.0090, island_z + 0.0000)]
    lens_r = 0.0078
    lens_protrusion = 0.0025
    lens_center_y = island_y - island_thick/2.0 - lens_protrusion/2.0
    
    for name, lx, lz in lenses:
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=lens_r, depth=lens_protrusion, location=(lx, lens_center_y, lz), rotation=(math.radians(90), 0, 0))
        ring = bpy.context.active_object
        ring.name = f"CameraRing_{name}"
        ring.data.materials.append(materials['lensring'])
        ring.modifiers.new("Bevel", type='BEVEL').width = 0.0006

        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=lens_r * 0.88, depth=lens_protrusion * 1.05, location=(lx, lens_center_y + 0.0001, lz), rotation=(math.radians(90), 0, 0))
        collar = bpy.context.active_object
        collar.name = f"CameraCollar_{name}"
        collar.data.materials.append(materials['dark'])

        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=lens_r * 0.80, depth=0.0006, location=(lx, lens_center_y - lens_protrusion/2.0 + 0.0003, lz), rotation=(math.radians(90), 0, 0))
        glass = bpy.context.active_object
        glass.name = f"CameraGlass_{name}"
        glass.data.materials.append(materials['lensglass'])

        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=lens_r * 0.45, depth=0.0004, location=(lx, lens_center_y + 0.0008, lz), rotation=(math.radians(90), 0, 0))
        pupil = bpy.context.active_object
        pupil.name = f"CameraPupil_{name}"
        pupil.data.materials.append(materials['pupil'])

    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.0036, depth=0.0006, location=(island_x + 0.0090, island_y - island_thick/2.0, island_z + 0.0105), rotation=(math.radians(90), 0, 0))
    flash = bpy.context.active_object
    flash.name = "Camera_Flash"
    flash.data.materials.append(materials['flash'])

    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.0028, depth=0.0005, location=(island_x + 0.0090, island_y - island_thick/2.0, island_z - 0.0110), rotation=(math.radians(90), 0, 0))
    lidar = bpy.context.active_object
    lidar.name = "Camera_LiDAR"
    lidar.data.materials.append(materials['dark'])

    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.0007, depth=0.0004, location=(island_x + 0.0035, island_y - island_thick/2.0, island_z + 0.0055), rotation=(math.radians(90), 0, 0))
    mic = bpy.context.active_object
    mic.name = "Camera_RearMic"
    mic.data.materials.append(materials['dark'])

    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
    root = bpy.context.active_object
    root.name = "iPhone_17_Pro_Root"
    
    for obj in bpy.context.scene.objects:
        if obj != root and obj.type == 'MESH':
            obj.parent = root
            
    return root

def setup_studio():
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs['Color'].default_value = (0.02, 0.022, 0.025, 1.0)
        bg.inputs['Strength'].default_value = 0.2

    mat_table = bpy.data.materials.new(name="Mat_MirrorTable")
    mat_table.use_nodes = True
    bsdf = mat_table.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.012, 0.013, 0.015, 1.0)
        bsdf.inputs['Metallic'].default_value = 0.4
        bsdf.inputs['Roughness'].default_value = 0.04
        
    bpy.ops.mesh.primitive_plane_add(size=10.0, location=(0.0, 0.0, 0.0))
    table = bpy.context.active_object
    table.name = "Studio_MirrorTable"
    table.data.materials.append(mat_table)

    key = bpy.data.lights.new(name="KeyLight", type='AREA')
    key.energy = 45.0
    key.size = 0.8
    key.size_y = 1.0
    key.color = (0.96, 0.98, 1.0)
    key_obj = bpy.data.objects.new("KeyLight", key)
    bpy.context.collection.objects.link(key_obj)
    key_obj.location = (-0.35, -0.45, 0.28)
    key_obj.rotation_euler = (math.radians(60), math.radians(-15), math.radians(-35))

    rim = bpy.data.lights.new(name="RimLight", type='AREA')
    rim.energy = 75.0
    rim.size = 0.05
    rim.size_y = 1.2
    rim.color = (1.0, 1.0, 1.0)
    rim_obj = bpy.data.objects.new("RimLight", rim)
    bpy.context.collection.objects.link(rim_obj)
    rim_obj.location = (-0.28, 0.20, 0.16)
    rim_obj.rotation_euler = (math.radians(-30), math.radians(20), math.radians(110))

    fill = bpy.data.lights.new(name="FillLight", type='AREA')
    fill.energy = 20.0
    fill.size = 1.0
    fill.color = (0.85, 0.92, 1.0)
    fill_obj = bpy.data.objects.new("FillLight", fill)
    bpy.context.collection.objects.link(fill_obj)
    fill_obj.location = (0.45, -0.30, 0.22)
    fill_obj.rotation_euler = (math.radians(50), math.radians(25), math.radians(55))

    back_light = bpy.data.lights.new(name="BackdropLight", type='SPOT')
    back_light.energy = 35.0
    back_light.spot_size = math.radians(65)
    back_light.spot_blend = 0.8
    back_light.color = (0.35, 0.40, 0.50)
    bl_obj = bpy.data.objects.new("BackdropLight", back_light)
    bpy.context.collection.objects.link(bl_obj)
    bl_obj.location = (0.0, 0.60, 0.20)
    bl_obj.rotation_euler = (math.radians(-90), 0, 0)

def render_previews(output_dir, root):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    if hasattr(scene, 'eevee'):
        scene.eevee.use_raytracing = True
        scene.eevee.taa_render_samples = 64
        
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    
    root.rotation_euler = (0, 0, math.radians(22))
    
    cam_data = bpy.data.cameras.new("HeroCamera")
    cam_data.lens = 85
    cam_obj = bpy.data.objects.new("HeroCamera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    
    target = bpy.data.objects.new("CamTarget", None)
    target.location = (0.0, 0.0, 0.075)
    bpy.context.collection.objects.link(target)
    
    const = cam_obj.constraints.new(type='TRACK_TO')
    const.target = target
    const.track_axis = 'TRACK_NEGATIVE_Z'
    const.up_axis = 'UP_Y' # Crucial fix for gimbal lock!
    
    # 1. Perspective Hero View (Match concept art)
    cam_obj.location = (-0.12, -0.34, 0.09)
    bpy.context.view_layer.update()
    scene.render.filepath = os.path.join(output_dir, "preview_perspective.png")
    print("Rendering perspective view...")
    bpy.ops.render.render(write_still=True)
    
    # 2. Side View
    root.rotation_euler = (0, 0, math.radians(-90))
    cam_obj.location = (0.0, -0.38, 0.075)
    bpy.context.view_layer.update()
    scene.render.filepath = os.path.join(output_dir, "preview_side.png")
    print("Rendering side view...")
    bpy.ops.render.render(write_still=True)
    
    # 3. Front View
    root.rotation_euler = (0, 0, 0)
    cam_obj.location = (0.0, 0.38, 0.075)
    bpy.context.view_layer.update()
    scene.render.filepath = os.path.join(output_dir, "preview_front.png")
    print("Rendering front view...")
    bpy.ops.render.render(write_still=True)
    
    # 4. Top/Camera Detail View
    root.rotation_euler = (0, 0, math.radians(10))
    cam_obj.location = (-0.08, -0.16, 0.13)
    target.location = (-0.015, -0.005, 0.118) # Look at camera bump
    bpy.context.view_layer.update()
    scene.render.filepath = os.path.join(output_dir, "preview_top.png")
    print("Rendering top/camera detail view...")
    bpy.ops.render.render(write_still=True)

def main():
    output_dir = r"c:\Users\Sunu\Documents\home\zaigopc\Desktop\personal\automate\output\2026-09-21_hp_iphone_17_pro"
    os.makedirs(output_dir, exist_ok=True)
    clean_scene()
    mats = create_materials()
    root = build_iphone_17_pro(mats)
    setup_studio()
    render_previews(output_dir, root)
    # NOTE: Turntable and exports are intentionally omitted from this initial pass.
    # The workflow dictates we review the preview images first before investing compute
    # in heavy turntable rendering and mesh exports.
    
    # Save the blender file so we can resume later for turntable/exports
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(output_dir, "iphone_17_pro.blend"))

if __name__ == "__main__":
    main()

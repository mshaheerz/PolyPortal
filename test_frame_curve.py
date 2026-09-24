"""
Prototype clean weapon frame silhouette using Blender Curves
"""
import bpy
import math
from mathutils import Vector

def test_frame():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if not bpy.data.scenes:
        bpy.data.scenes.new("Scene")

    curve_data = bpy.data.curves.new('PistolFrameCurve', type='CURVE')
    curve_data.dimensions = '2D'
    curve_data.extrude = 0.013 # Half width -> total width 0.026m (26mm)
    curve_data.bevel_depth = 0.002 # Rounded edges
    curve_data.bevel_resolution = 4
    curve_data.resolution_u = 12

    # Outer silhouette (in local X-Y plane of curve, which we will rotate to Y-Z in 3D)
    # X corresponds to Gun Y (length: +Y front, -Y rear)
    # Y corresponds to Gun Z (height: +Z up, -Z down)
    outer = curve_data.splines.new('BEZIER')
    
    # Define key profile control points (Gun Y, Gun Z)
    # 0: Muzzle dust cover top: (+0.082, 0.072)
    # 1: Dust cover front lip: (+0.082, 0.052)
    # 2: Rail bottom front: (+0.035, 0.050)
    # 3: Trigger guard front: (+0.026, 0.024)
    # 4: Trigger guard bottom: (+0.005, 0.020)
    # 5: Trigger guard rear bottom: (-0.016, 0.022)
    # 6: Grip front strap top: (-0.019, 0.028)
    # 7: Finger groove 1: (-0.024, 0.014)
    # 8: Finger ridge 1: (-0.022, 0.004)
    # 9: Finger groove 2: (-0.029, -0.010)
    # 10: Finger ridge 2: (-0.027, -0.020)
    # 11: Grip front bottom lip: (-0.038, -0.046)
    # 12: Magwell base front: (-0.036, -0.052)
    # 13: Magwell base rear: (-0.076, -0.052)
    # 14: Grip backstrap heel: (-0.078, -0.044)
    # 15: Grip backstrap palm swell: (-0.072, -0.010)
    # 16: Grip backstrap upper: (-0.058, 0.026)
    # 17: Beavertail throat (deep notch): (-0.046, 0.048)
    # 18: Beavertail tip (swept back/up): (-0.082, 0.063)
    # 19: Frame rear under slide: (-0.078, 0.072)

    pts = [
        (+0.082, 0.072),
        (+0.082, 0.052),
        (+0.035, 0.050),
        (+0.026, 0.024),
        (+0.005, 0.020),
        (-0.016, 0.022),
        (-0.019, 0.028),
        (-0.024, 0.014),
        (-0.022, 0.004),
        (-0.029, -0.010),
        (-0.027, -0.020),
        (-0.038, -0.046),
        (-0.036, -0.052),
        (-0.076, -0.052),
        (-0.078, -0.044),
        (-0.072, -0.010),
        (-0.058, 0.026),
        (-0.046, 0.048),
        (-0.082, 0.063),
        (-0.078, 0.072)
    ]
    
    outer.bezier_points.add(len(pts) - 1)
    for idx, (py, pz) in enumerate(pts):
        bp = outer.bezier_points[idx]
        bp.co = (py, pz, 0.0)
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'
    outer.use_cyclic_u = True

    # Inner cutout for trigger hole
    inner = curve_data.splines.new('BEZIER')
    inner_pts = [
        (+0.020, 0.050), # Under dust cover
        (+0.020, 0.028), # Inside trigger guard front
        (+0.005, 0.026), # Inside trigger guard bottom
        (-0.012, 0.028), # Inside trigger guard rear
        (-0.012, 0.050), # Inside trigger root
    ]
    inner.bezier_points.add(len(inner_pts) - 1)
    for idx, (py, pz) in enumerate(inner_pts):
        bp = inner.bezier_points[idx]
        bp.co = (py, pz, 0.0)
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'
    inner.use_cyclic_u = True

    frame_obj = bpy.data.objects.new("PistolFrame", curve_data)
    bpy.context.collection.objects.link(frame_obj)
    
    # Rotate curve from X-Y into Y-Z
    frame_obj.rotation_euler = (math.radians(90), 0, math.radians(90))
    
    # Save blend file for inspection
    bpy.ops.wm.save_as_mainfile(filepath="frame_test.blend")
    print("[SUCCESS] Created pistol frame curve!")

test_frame()

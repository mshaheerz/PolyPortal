"""
blender_client.py
Interactive Client for Blender MCP Server (localhost:9876)

Allows real-time code execution, scene inspection, and interactive modeling
directly inside an active Blender GUI session or headless server.
"""

import socket
import json
import subprocess
import os
import sys
import time

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9876
BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"

def is_mcp_running(host=DEFAULT_HOST, port=DEFAULT_PORT, timeout=1.0):
    """Check if the Blender MCP socket server is listening."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False

def execute_in_blender(code, host=DEFAULT_HOST, port=DEFAULT_PORT, timeout=30.0):
    """
    Send Python code to Blender MCP server and return response dict.
    Returns: {"status": "ok"|"error", "result": ..., "stdout": ..., "stderr": ...}
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((host, port))
    
    req = {
        "type": "execute",
        "code": code,
        "strict_json": True
    }
    s.sendall((json.dumps(req) + "\0").encode("utf-8"))
    
    data = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        data += chunk
        if b"\0" in data:
            break
            
    s.close()
    resp_str = data.split(b"\0")[0].decode("utf-8")
    return json.loads(resp_str)

def launch_blender_gui():
    """Launch Blender in GUI mode with MCP server autostarted."""
    print("[*] Launching Blender in GUI mode...")
    proc = subprocess.Popen([BLENDER_PATH], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Wait for server to bind
    for _ in range(20):
        time.sleep(1.0)
        if is_mcp_running():
            print("[+] Blender MCP server is live on localhost:9876!")
            return proc
    print("[!] Blender launched, waiting for user to start MCP or check sidebar.")
    return proc

def get_scene_summary():
    """Query live Blender scene for objects, mesh count, and active camera."""
    code = """
import bpy
objs = [{"name": o.name, "type": o.type, "location": list(o.location)} for o in bpy.context.scene.objects]
result["objects"] = objs
result["object_count"] = len(objs)
result["active_camera"] = bpy.context.scene.camera.name if bpy.context.scene.camera else None
result["render_engine"] = bpy.context.scene.render.engine
"""
    return execute_in_blender(code)

if __name__ == "__main__":
    print("="*55)
    print("  Blender MCP Live Interactive Client")
    print("="*55)
    
    if not is_mcp_running():
        print("[-] Blender MCP server is not currently listening on localhost:9876")
        print("    You can launch Blender GUI, and MCP will auto-start,")
        print("    or run: blender --background --command blender_mcp")
    else:
        print("[+] Connected to Blender MCP Server!")
        res = get_scene_summary()
        print("\nLive Scene Status:")
        print(json.dumps(res, indent=2))

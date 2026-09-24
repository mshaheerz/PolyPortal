import os
import subprocess
import sys

def install_local_triposr():
    print("Setting up Local TripoSR (CPU Mode) in ai_3d_env...")
    venv_python = r"c:\Users\Sunu\Documents\home\zaigopc\Desktop\personal\automate\ai_3d_env\Scripts\python.exe"
    
    commands = [
        # 1. Install CPU version of PyTorch (AMD integrated graphics doesn't support CUDA)
        [venv_python, "-m", "pip", "install", "torch", "torchvision", "--index-url", "https://download.pytorch.org/whl/cpu"],
        
        # 2. Clone TripoSR repo if it doesn't exist
        ["git", "clone", "https://github.com/VAST-AI-Research/TripoSR.git"],
        
        # 3. Install requirements
        [venv_python, "-m", "pip", "install", "-r", "TripoSR/requirements.txt"],
        
        # 4. Install Gradio client for the Colab fallback
        [venv_python, "-m", "pip", "install", "gradio_client"]
    ]
    
    for cmd in commands:
        if cmd[0] == 'git' and os.path.exists("TripoSR"):
            print("TripoSR already cloned, skipping...")
            continue
            
        print(f"Running: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error during installation: {e}")
            print("This might be due to Python 3.13 compatibility with some ML packages.")
            print("Don't worry, we will primarily rely on the Colab GPU server which is much faster!")
            break

    print("Setup attempt finished.")

if __name__ == "__main__":
    install_local_triposr()

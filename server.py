from flask import Flask, request, jsonify
import os
import re
import ctypes
import subprocess
import psutil
import shutil
import pyttsx3
from configparser import ConfigParser
from typing import Tuple
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# -------------------- Configuration --------------------
class CommandConfig:
    def __init__(self):
        self.config = ConfigParser()
        self.config.read('config.ini')
        self.allowed_commands = [cmd.strip().lower() for cmd in 
            self.config.get('DEFAULT', 'AllowedCommands', 
            fallback='process,shut down,restart,show files,create file,create folder,remove file,remove folder,copy file,copy folder,open file,open folder,read file,network').split(',')]

# -------------------- Command Execution --------------------
class SystemCommander:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))  # Server path for file operations
    
    REQUIRED_ARGS = {
        'process': ['target'],
        'open file': ['target'],
        'open folder': ['target'],
        'show files': ['target'],
        'create file': ['target'],
        'create folder': ['target'],
        'remove file': ['target'],
        'remove folder': ['target'],
        'copy file': ['source', 'destination'],
        'copy folder': ['source', 'destination'],
        'read file': ['target'],
        'shut down': [],
        'restart': [],
        'network': []
    }

    @staticmethod
    def execute(command_type: str, args: dict) -> Tuple[bool, str]:
        handlers = {
            'process': lambda: SystemCommander._kill_process(args.get('target')),
            'shut down': lambda: SystemCommander._power_action('shut down'),
            'restart': lambda: SystemCommander._power_action('restart'),
            'show files': lambda: SystemCommander._show_files(args.get('target', '')),
            'create file': lambda: SystemCommander._create_file(args.get('target')),
            'create folder': lambda: SystemCommander._create_folder(args.get('target')),
            'remove file': lambda: SystemCommander._remove_file(args.get('target')),
            'remove folder': lambda: SystemCommander._remove_folder(args.get('target')),
            'copy file': lambda: SystemCommander._copy_file(args.get('source'), args.get('destination')),
            'copy folder': lambda: SystemCommander._copy_folder(args.get('source'), args.get('destination')),
            'open file': lambda: SystemCommander._open_file(args.get('target')),
            'open folder': lambda: SystemCommander._open_folder(args.get('target')),
            'read file': lambda: SystemCommander._read_file(args.get('target')),
            'network': lambda: SystemCommander._check_network()
        }
        
        if command_type not in handlers:
            return False, "Invalid command type"
        
        required = SystemCommander.REQUIRED_ARGS.get(command_type, [])
        missing = [arg for arg in required if arg not in args]
        if missing:
            return False, f"Missing arguments: {', '.join(missing)}"
        
        success, message = handlers[command_type]()
        return success, f"Computer: {message}"

    @staticmethod
    def _kill_process(name: str) -> Tuple[bool, str]:
        try:
            name = name.lower().strip()
            if not name.endswith('.exe'):
                name += '.exe'

            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == name:
                    proc.kill()
                    return True, f"Terminated {name}"
            return False, f"Process {name} not found"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _power_action(action: str) -> Tuple[bool, str]:
        try:
            if not ctypes.windll.shell32.IsUserAnAdmin():
                return False, "Admin rights required"
            
            subprocess.run(
                ["shutdown", f"/{action[0]}", "/t", "0"],
                check=True,
                shell=True
            )
            return True, f"Initiating {action}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _show_files(target: str) -> Tuple[bool, str]:
        try:
            path = os.path.join(SystemCommander.BASE_PATH, target.strip())
            if not os.path.exists(path):
                return False, f"Path {path} not found"
            files = os.listdir(path)
            return True, f"Files in {path}: {', '.join(files)}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _create_file(target: str) -> Tuple[bool, str]:
        try:
            path = os.path.join(SystemCommander.BASE_PATH, target.strip())
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                f.write('')
            return True, f"Created file {target}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _create_folder(target: str) -> Tuple[bool, str]:
        try:
            path = os.path.join(SystemCommander.BASE_PATH, target.strip())
            os.makedirs(path, exist_ok=True)
            return True, f"Created folder {target}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _remove_file(target: str) -> Tuple[bool, str]:
        try:
            path = os.path.join(SystemCommander.BASE_PATH, target.strip())
            if os.path.exists(path):
                os.remove(path)
                return True, f"Removed file {target}"
            return False, f"File {target} not found"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _remove_folder(target: str) -> Tuple[bool, str]:
        try:
            path = os.path.join(SystemCommander.BASE_PATH, target.strip())
            if os.path.exists(path):
                shutil.rmtree(path)
                return True, f"Removed folder {target}"
            return False, f"Folder {target} not found"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _copy_file(source: str, destination: str) -> Tuple[bool, str]:
        try:
            src_path = os.path.join(SystemCommander.BASE_PATH, source.strip())
            dst_path = os.path.join(SystemCommander.BASE_PATH, destination.strip())
            if not os.path.exists(src_path):
                return False, f"Source file {source} not found"
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.copy2(src_path, dst_path)
            return True, f"Copied file from {source} to {destination}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _copy_folder(source: str, destination: str) -> Tuple[bool, str]:
        try:
            src_path = os.path.join(SystemCommander.BASE_PATH, source.strip())
            dst_path = os.path.join(SystemCommander.BASE_PATH, destination.strip())
            if not os.path.exists(src_path):
                return False, f"Source folder {source} not found"
            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            return True, f"Copied folder from {source} to {destination}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _open_file(target: str) -> Tuple[bool, str]:
        try:
            path = os.path.join(SystemCommander.BASE_PATH, target.strip())
            if os.path.exists(path):
                os.startfile(path)
                return True, f"Opened file {target}"
            return False, f"File {target} not found"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _open_folder(target: str) -> Tuple[bool, str]:
        try:
            path = os.path.join(SystemCommander.BASE_PATH, target.strip())
            if os.path.exists(path):
                os.startfile(path)
                return True, f"Opened folder {target}"
            return False, f"Folder {target} not found"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _read_file(target: str) -> Tuple[bool, str]:
        try:
            path = os.path.join(SystemCommander.BASE_PATH, target.strip())
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Use text-to-speech to read content
                engine = pyttsx3.init()
                engine.say(content)
                engine.runAndWait()
                return True, f"Reading content of {target}"
            return False, f"File {target} not found"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _check_network() -> Tuple[bool, str]:
        try:
            result = subprocess.run(["ping", "-n", "1", "8.8.8.8"], 
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  shell=True)
            return (True, "Network active") if result.returncode == 0 else (False, "Network issues")
        except Exception as e:
            return False, str(e)

# -------------------- API Endpoints --------------------
@app.route('/commands', methods=['POST'])
def handle_command():
    data = request.json
    if not data or 'command' not in data:
        return jsonify({"error": "Invalid request"}), 400
    
    config = CommandConfig()
    command_type = data['command'].lower()
    
    if command_type not in config.allowed_commands:
        return jsonify({"error": "Command not allowed"}), 403
    
    success, message = SystemCommander.execute(command_type, data.get('args', {}))
    status_code = 200 if success else 500
    
    return jsonify({
        "command": command_type,
        "success": success,
        "message": message
    }), status_code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  
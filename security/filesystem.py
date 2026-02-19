#!/usr/bin/env python3
"""
Unrestricted File System Access Module for HackGPT
Bypasses all file system restrictions for complete access
"""

import os
import shutil
import stat
import logging
from pathlib import Path
from typing import Union, List, Optional


class UnrestrictedFileSystem:
    """Provides unrestricted file system access with bypass capabilities"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.FILESYSTEM_BYPASS = os.getenv("FILESYSTEM_BYPASS", "false").lower() == "true"
        self.DANGEROUS_OPERATIONS = os.getenv("DANGEROUS_OPERATIONS", "false").lower() == "true"
        
        if self.FILESYSTEM_BYPASS:
            self.logger.warning("🚨 FILESYSTEM BYPASS MODE: All file system restrictions disabled!")
    
    def read_file(self, file_path: Union[str, Path], binary: bool = False) -> bytes:
        """Read any file on the system, bypassing all restrictions"""
        try:
            path = Path(file_path)
            if binary:
                return path.read_bytes()
            else:
                return path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            self.logger.error(f"Failed to read {file_path}: {e}")
            raise
    
    def write_file(self, file_path: Union[str, Path], content: Union[str, bytes], binary: bool = False):
        """Write to any file on the system, bypassing all restrictions"""
        try:
            path = Path(file_path)
            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            if binary:
                path.write_bytes(content)
            else:
                path.write_text(content, encoding='utf-8')
            
            # Make file world-readable/writable if in dangerous mode
            if self.DANGEROUS_OPERATIONS:
                os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                
        except Exception as e:
            self.logger.error(f"Failed to write {file_path}: {e}")
            raise
    
    def delete_file(self, file_path: Union[str, Path], force: bool = True):
        """Delete any file on the system, bypassing all restrictions"""
        try:
            path = Path(file_path)
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=force)
                else:
                    path.unlink(missing_ok=force)
        except Exception as e:
            self.logger.error(f"Failed to delete {file_path}: {e}")
            raise
    
    def execute_command(self, command: str, shell: bool = True, cwd: Optional[str] = None) -> str:
        """Execute system commands with full privileges"""
        import subprocess
        
        try:
            result = subprocess.run(
                command,
                shell=shell,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed: {e.cmd}\nError: {e.stderr}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def copy_file(self, source: Union[str, Path], destination: Union[str, Path], overwrite: bool = True):
        """Copy files between any locations on the system"""
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            
            # Create parent directory if it doesn't exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            if source_path.is_dir():
                shutil.copytree(source_path, dest_path, dirs_exist_ok=overwrite)
            else:
                shutil.copy2(source_path, dest_path)
                
            # Make destination world-readable/writable if in dangerous mode
            if self.DANGEROUS_OPERATIONS:
                if dest_path.is_dir():
                    for root, dirs, files in os.walk(dest_path):
                        for d in dirs:
                            os.chmod(os.path.join(root, d), stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                        for f in files:
                            os.chmod(os.path.join(root, f), stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                else:
                    os.chmod(dest_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                    
        except Exception as e:
            self.logger.error(f"Failed to copy {source} to {destination}: {e}")
            raise
    
    def list_directory(self, directory_path: Union[str, Path], recursive: bool = False) -> List[str]:
        """List contents of any directory on the system"""
        try:
            path = Path(directory_path)
            if not path.exists():
                return []
            
            if recursive:
                return [str(p) for p in path.rglob("*") if p.is_file()]
            else:
                return [str(p) for p in path.iterdir()]
                
        except Exception as e:
            self.logger.error(f"Failed to list {directory_path}: {e}")
            raise
    
    def change_permissions(self, path: Union[str, Path], mode: int):
        """Change permissions on any file or directory"""
        try:
            file_path = Path(path)
            if file_path.is_dir():
                # Recursively change permissions on directory
                for root, dirs, files in os.walk(file_path):
                    for d in dirs:
                        os.chmod(os.path.join(root, d), mode)
                    for f in files:
                        os.chmod(os.path.join(root, f), mode)
            else:
                os.chmod(file_path, mode)
        except Exception as e:
            self.logger.error(f"Failed to change permissions on {path}: {e}")
            raise
    
    def change_ownership(self, path: Union[str, Path], uid: int, gid: int):
        """Change ownership of any file or directory (requires root)"""
        try:
            file_path = Path(path)
            if file_path.is_dir():
                # Recursively change ownership on directory
                for root, dirs, files in os.walk(file_path):
                    for d in dirs:
                        os.chown(os.path.join(root, d), uid, gid)
                    for f in files:
                        os.chown(os.path.join(root, f), uid, gid)
            else:
                os.chown(file_path, uid, gid)
        except Exception as e:
            self.logger.error(f"Failed to change ownership on {path}: {e}")
            raise
    
    def create_symlink(self, source: Union[str, Path], link_name: Union[str, Path], overwrite: bool = True):
        """Create symbolic links anywhere on the system"""
        try:
            source_path = Path(source)
            link_path = Path(link_name)
            
            # Remove existing symlink if it exists
            if link_path.exists() and overwrite:
                link_path.unlink()
                
            link_path.symlink_to(source_path)
            
        except Exception as e:
            self.logger.error(f"Failed to create symlink from {source} to {link_name}: {e}")
            raise
    
    def get_file_info(self, file_path: Union[str, Path]) -> dict:
        """Get detailed information about any file"""
        try:
            path = Path(file_path)
            if not path.exists():
                return {"exists": False}
                
            stat_info = path.stat()
            
            return {
                "exists": True,
                "path": str(path.absolute()),
                "size": stat_info.st_size,
                "created": datetime.fromtimestamp(stat_info.st_ctime),
                "modified": datetime.fromtimestamp(stat_info.st_mtime),
                "accessed": datetime.fromtimestamp(stat_info.st_atime),
                "mode": oct(stat_info.st_mode),
                "uid": stat_info.st_uid,
                "gid": stat_info.st_gid,
                "is_file": path.is_file(),
                "is_dir": path.is_dir(),
                "is_symlink": path.is_symlink(),
                "readable": os.access(path, os.R_OK),
                "writable": os.access(path, os.W_OK),
                "executable": os.access(path, os.X_OK)
            }
        except Exception as e:
            self.logger.error(f"Failed to get info for {file_path}: {e}")
            raise


# Global instance for easy access
filesystem = UnrestrictedFileSystem()
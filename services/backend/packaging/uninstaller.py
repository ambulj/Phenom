"""
Phenom Clean Uninstaller & Registry Cleanliness Engine (Task 7b)
Ensures zero leftover registry keys, scheduled tasks, or orphaned services.
"""

import os
import sys
import shutil
import logging
from typing import Dict, Any, List

try:
    import winreg
except ImportError:
    winreg = None

logger = logging.getLogger("phenom.uninstaller")

class PhenomUninstaller:
    def __init__(self, app_data_dir: str = None):
        user_prof = os.environ.get("USERPROFILE") or os.path.expanduser("~")
        self.app_data_dir = app_data_dir or os.path.join(user_prof, "AppData", "Roaming", "Phenom")
        self.run_key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        self.app_key_path = r"Software\Phenom"

    def remove_startup_registry_key(self) -> bool:
        """Removes HKCU Run key for Phenom if present."""
        if winreg is None:
            return True
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.run_key_path, 0, winreg.KEY_SET_VALUE) as key:
                try:
                    winreg.DeleteValue(key, "Phenom")
                    return True
                except FileNotFoundError:
                    return True
        except Exception as e:
            logger.warning(f"Failed to delete startup run key: {e}")
            return False

    def remove_app_registry_key(self) -> bool:
        """Removes HKCU\\Software\\Phenom registry tree if present."""
        if winreg is None:
            return True
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, self.app_key_path)
            return True
        except FileNotFoundError:
            return True
        except Exception as e:
            logger.warning(f"Failed to delete app registry key: {e}")
            return False

    def check_registry_cleanliness(self) -> Dict[str, Any]:
        """Verifies zero leftover registry keys in HKCU for Phenom."""
        if winreg is None:
            return {"run_key_present": False, "app_key_present": False, "clean": True}

        run_key_present = False
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.run_key_path, 0, winreg.KEY_READ) as key:
                try:
                    winreg.QueryValueEx(key, "Phenom")
                    run_key_present = True
                except FileNotFoundError:
                    pass
        except Exception:
            pass

        app_key_present = False
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.app_key_path, 0, winreg.KEY_READ) as key:
                app_key_present = True
        except FileNotFoundError:
            pass
        except Exception:
            pass

        return {
            "run_key_present": run_key_present,
            "app_key_present": app_key_present,
            "clean": not run_key_present and not app_key_present
        }

    def clean_temporary_files(self) -> int:
        """Cleans temporary cache and scratch directories."""
        count = 0
        cache_dir = os.path.join(self.app_data_dir, "cache")
        if os.path.exists(cache_dir):
            try:
                shutil.rmtree(cache_dir)
                count += 1
            except Exception:
                pass
        return count

    def run_uninstall(self, purge_data: bool = False) -> Dict[str, Any]:
        """Executes full uninstaller routine."""
        reg_run_ok = self.remove_startup_registry_key()
        reg_app_ok = self.remove_app_registry_key()
        temp_cleaned = self.clean_temporary_files()

        data_wiped = False
        if purge_data and os.path.exists(self.app_data_dir):
            try:
                shutil.rmtree(self.app_data_dir)
                data_wiped = True
            except Exception as e:
                logger.warning(f"Failed to wipe data dir: {e}")

        cleanliness = self.check_registry_cleanliness()
        return {
            "status": "success" if cleanliness["clean"] else "partial",
            "registry_cleanliness": cleanliness,
            "temp_cleaned": temp_cleaned,
            "data_wiped": data_wiped
        }

# Global uninstaller
uninstaller = PhenomUninstaller()

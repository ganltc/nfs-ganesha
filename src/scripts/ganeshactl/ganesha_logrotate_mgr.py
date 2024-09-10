#!/usr/bin/python3
# SPDX-License-Identifier: LGPL-3.0-or-later
#-------------------------------------------------------------------------------
#
# Copyright IBM Corporation, 2024
#  Contributor: Prabhu Murugesan <prabhu.murugesan1@ibm.com>
#
#
# This software is a server that implements the NFS protocol.
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
#-------------------------------------------------------------------------------
#
# ganesha_logrotate_mgr - A script to manage log rotation for Ganesha logs.
#
# This script provides functionalities to enable, disable, list, and
# change log rotation configurations for Ganesha logs.  It also allows
# setting a crontab entry  to manage log rotation automatically.
# The script supports specifying different FSAL types # to determine
# the log file location and provides default values for size and
# rotation settings.

import os
import sys
import subprocess
import platform
import shutil

# Constants for configuration files and default values
LOGROTATE_CONFIG_FILE = "/etc/logrotate.d/ganesha"
DEFAULT_LOGROTATE_CONFIG_FILE = "/etc/logrotate.d/ganesha.default"
DEFAULT_CRONTAB_ENTRY = "*/1 * * * * /usr/sbin/logrotate /etc/logrotate.d/ganesha"
CRONTAB_CMD = "crontab -l | grep -v '/etc/logrotate.d/ganesha' | crontab -"

DEFAULT_SIZE_GB = 2
DEFAULT_ROTATE = 10
DEFAULT_FSAL_LOG_PATH = "/var/log/ganesha/nfs-ganesha.log"
FSAL_LOG_PATHS = {
    "gpfs": "/var/log/ganesha.log",
    "nfs": "/var/log/ganesha/nfs-ganesha.log",
    # Add more FSAL types if needed
}

class LogRotateManager:
    """
    Manages Ganesha log rotation: enabling, disabling, updating, and listing configs.
    """

    def __init__(self, fsal=None):
        """
        Initialize with FSAL type.

        :param fsal: FSAL type for log file path (default is None).
        """
        self.os_type = self.get_os_type()
        self.fsal = fsal.lower() if fsal else None
        self.log_file_path = FSAL_LOG_PATHS.get(self.fsal, DEFAULT_FSAL_LOG_PATH)

    def get_os_type(self):
        """
        Get OS type (Ubuntu, RHEL, or Other).

        :return: OS type as a string.
        """
        try:
            # Check for /etc/os-release
            if os.path.isfile('/etc/os-release'):
                with open('/etc/os-release') as f:
                    content = f.read().lower()
                    if 'ubuntu' in content:
                        return 'ubuntu'
                    elif 'centos' in content or 'red hat' in content or 'rhel' in content:
                        return 'rhel'

            # Check for /etc/*release files if /etc/os-release is not present
            for release_file in ['/etc/redhat-release', '/etc/centos-release', '/etc/lsb-release']:
                if os.path.isfile(release_file):
                    with open(release_file) as f:
                        content = f.read().lower()
                        if 'ubuntu' in content:
                            return 'ubuntu'
                        elif 'centos' in content or 'red hat' in content or 'rhel' in content:
                            return 'rhel'

        except Exception:
            pass

        return 'other'

    def is_crontab_entry_present(self):
        """
        Check if the crontab entry exists.

        :return: True if present, otherwise False.
        """
        result = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        return "/etc/logrotate.d/ganesha" in result.stdout

    def backup_default_config(self):
        """
        Backup the current logrotate config.
        """
        if os.path.exists(LOGROTATE_CONFIG_FILE):
            shutil.copy(LOGROTATE_CONFIG_FILE, DEFAULT_LOGROTATE_CONFIG_FILE)
        else:
            print(f"Warning: {LOGROTATE_CONFIG_FILE} not found. Cannot backup.")

    def restore_default_config(self):
        """
        Restore the default logrotate config.
        """
        if os.path.exists(DEFAULT_LOGROTATE_CONFIG_FILE):
            shutil.copy(DEFAULT_LOGROTATE_CONFIG_FILE, LOGROTATE_CONFIG_FILE)
        else:
            print(f"Warning: {DEFAULT_LOGROTATE_CONFIG_FILE} not found. Cannot restore.")

    def add_crontab_entry(self, entry):
        """
        Add a crontab entry.

        :param entry: Crontab entry to add.
        """
        subprocess.run(f'(crontab -l 2>/dev/null; echo "{entry}") | crontab -', shell=True)

    def remove_crontab_entry(self):
        """
        Remove the crontab entry.
        """
        subprocess.run(CRONTAB_CMD, shell=True)

    def list_config(self):
        """
        List current logrotate config and crontab entry.
        """
        if self.is_crontab_entry_present():
            print(f"Ganesha Logrotate Configuration ({LOGROTATE_CONFIG_FILE}):")
            with open(LOGROTATE_CONFIG_FILE, 'r') as file:
                print(file.read())

            print("\nGanesha Crontab Entry:")
            result = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            entries = [line for line in result.stdout.splitlines() if "/etc/logrotate.d/ganesha" in line]
            print("\n".join(entries) if entries else "No crontab entry found.")
        else:
            print("Ganesha logrotate is not enabled.")

    def generate_logrotate_config(self, size_gb, rotate_count):
        """
        Generate a new logrotate config.

        :param size_gb: Log file size in GB.
        :param rotate_count: Number of rotations.
        """
        config = f"""
{self.log_file_path} {{
    size {size_gb}G
    rotate {rotate_count}
    copytruncate
    dateformat -%Y%m%d%H%M%S
    compress
    missingok
}}
"""
        if self.os_type == "ubuntu":
            config = config.replace("{", "{\n    su root syslog\n")
        with open(LOGROTATE_CONFIG_FILE, "w") as file:
            file.write(config)

    def update_logrotate_config(self, size_gb, rotate_count):
        """
        Update existing logrotate config with new size and rotate values.

        :param size_gb: New log file size in GB.
        :param rotate_count: New number of rotations.
        """
        if not os.path.exists(LOGROTATE_CONFIG_FILE):
            print(f"Error: {LOGROTATE_CONFIG_FILE} not found. Cannot update.")
            sys.exit(1)

        with open(LOGROTATE_CONFIG_FILE, 'r') as file:
            config_lines = file.readlines()

        new_config_lines = []
        for line in config_lines:
            if line.strip().startswith("size"):
                new_config_lines.append(f"    size {size_gb}G\n")
            elif line.strip().startswith("rotate"):
                new_config_lines.append(f"    rotate {rotate_count}\n")
            else:
                new_config_lines.append(line)

        with open(LOGROTATE_CONFIG_FILE, 'w') as file:
            file.writelines(new_config_lines)

    def change_config(self, size=DEFAULT_SIZE_GB, rotate=DEFAULT_ROTATE):
        """
        Change logrotate config if enabled.

        :param size: New size in GB.
        :param rotate: New rotate count.
        """
        if not self.is_crontab_entry_present():
            print("Error: Ganesha logrotate is not enabled. Enable it first.")
            sys.exit(1)

        self.update_logrotate_config(size, rotate)
        self.restart_cron_service()
        print("Ganesha logrotate configuration updated.")

    def restart_cron_service(self):
        """
        Restart cron service based on OS type.
        """
        if self.os_type == "ubuntu":
            subprocess.run(["systemctl", "restart", "cron"], check=True)
        else:
            subprocess.run(["systemctl", "restart", "crond"], check=True)

    def enable(self):
        """
        Enable log rotation: backup config, generate new config, and add crontab entry.
        """
        if not self.is_crontab_entry_present():
            self.backup_default_config()
            self.generate_logrotate_config(DEFAULT_SIZE_GB, DEFAULT_ROTATE)
            self.add_crontab_entry(DEFAULT_CRONTAB_ENTRY)
            print("Ganesha logrotate enabled.")
        else:
            print("Ganesha logrotate is already enabled.")

    def disable(self):
        """
        Disable log rotation: remove crontab entry and restore default config.
        """
        if self.is_crontab_entry_present():
            self.remove_crontab_entry()
            self.restore_default_config()
            print("Ganesha logrotate removed.")
        else:
            print("Ganesha logrotate is not enabled.")

    def set_crontab(self, new_entry):
        """
        Set a new crontab entry and force logrotate.

        :param new_entry: New crontab entry.
        """
        if self.is_crontab_entry_present():
            self.remove_crontab_entry()
        self.add_crontab_entry(new_entry)
        subprocess.run("/usr/sbin/logrotate -f /etc/logrotate.d/ganesha", shell=True)
        print("Crontab entry updated and logrotate forced.")

def show_help():
    """
    Show the help text for script usage.
    """
    help_text = """
Usage: ganesha_logrotate_mgr <enable|disable|list|change|set-crontab> [options]

Commands:
  enable            Enable log rotation.
                    Options:
                      fsal=<type>  FSAL type (optional, default uses /var/log/ganesha/nfs-ganesha.log).
  disable           Disable log rotation.
  list              List current log rotation configuration and crontab entry.
  change [options]  Change log rotation configuration.
                    Options:
                      size=<int>   Log file size in GB (default is 2GB).
                      rotate=<int> Number of rotations (default is 10).
  set-crontab <entry> Set a new crontab entry.
                    Options:
                      <entry> Crontab entry to set.

Examples:
  ganesha_logrotate_mgr enable
  ganesha_logrotate_mgr enable fsal=gpfs
  ganesha_logrotate_mgr disable
  ganesha_logrotate_mgr list
  ganesha_logrotate_mgr change size=5 rotate=10
  ganesha_logrotate_mgr set-crontab "*/5 * * * * /usr/sbin/logrotate /etc/logrotate.d/ganesha"
"""
    print(help_text)

def main():
    """
    Main function to handle command-line arguments and invoke the appropriate actions.
    """
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)

    action = sys.argv[1].lower()
    fsal = None

    if action == "enable":
        if len(sys.argv) > 2 and 'fsal=' in sys.argv[2]:
            fsal = sys.argv[2].split('=')[1]
        manager = LogRotateManager(fsal=fsal)
        manager.enable()

    elif action == "disable":
        manager = LogRotateManager()
        manager.disable()

    elif action == "list":
        manager = LogRotateManager()
        manager.list_config()

    elif action == "change":
        size = DEFAULT_SIZE_GB
        rotate = DEFAULT_ROTATE
        for arg in sys.argv[2:]:
            if arg.startswith("size="):
                size = int(arg.split('=')[1])
            elif arg.startswith("rotate="):
                rotate = int(arg.split('=')[1])
        manager = LogRotateManager()
        manager.change_config(size=size, rotate=rotate)

    elif action == "set-crontab":
        if len(sys.argv) < 3:
            print("Error: Crontab entry is required.")
            show_help()
            sys.exit(1)
        new_entry = sys.argv[2]
        manager = LogRotateManager()
        manager.set_crontab(new_entry)

    else:
        show_help()
        sys.exit(1)

if __name__ == "__main__":
    main()

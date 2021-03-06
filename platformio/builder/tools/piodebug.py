# Copyright 2014-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import sys
from fnmatch import fnmatch
from os.path import isfile
from platform import system

from platformio import util


def ProcessDebug(env):
    env.Append(
        BUILD_FLAGS=["-Og", "-ggdb"],
        BUILD_UNFLAGS=["-Os", "-O0", "-O1", "-O2", "-O3"])


def DebugToolSettings(env):
    if "BOARD" not in env:
        return
    board_debug = env.BoardConfig().get("debug", {})
    if not board_debug or not board_debug.get("tools"):
        return
    debug_tools = board_debug.get("tools")
    tool_name = (env.subst("$DEBUG_TOOL") or
                 board_debug.get("default_tool", debug_tools.keys()[0]))
    settings = debug_tools.get(tool_name)
    if not settings:
        return
    settings.update({"name": tool_name})
    return settings


def AutodetectDebugPort(env):

    def _get_pattern():
        if "DEBUG_PORT" not in env:
            return None
        if set(["*", "?", "[", "]"]) & set(env['DEBUG_PORT']):
            return env['DEBUG_PORT']
        return None

    def _is_match_pattern(port):
        pattern = _get_pattern()
        if not pattern:
            return True
        return fnmatch(port, pattern)

    def _look_for_serial_port(hwids):
        port = None
        for item in util.get_serialports(filter_hwid=True):
            if not _is_match_pattern(item['port']):
                continue
            if "GDB" in item['port']:
                return item['port']
            for hwid in hwids:
                hwid_str = ("%s:%s" % (hwid[0], hwid[1])).replace("0x", "")
                if hwid_str in item['hwid']:
                    return port
        return port

    if "BOARD" not in env or ("DEBUG_PORT" in env and not _get_pattern()):
        return

    tool_settings = env.DebugToolSettings()
    if not tool_settings:
        return
    if not tool_settings.get("require_debug_port"):
        return

    need_openocd_rules = [
        system() == "Linux",
        "openocd" in tool_settings.get("server", {}).get("package", ""),
        not any([
            isfile("/etc/udev/rules.d/98-openocd-udev.rules"),
            isfile("/lib/udev/rules.d/98-openocd-udev.rules")
        ])
    ]
    if all(need_openocd_rules):
        sys.stderr.write(
            "\nWarning! Please install `98-openocd-udev.rules` and check "
            "that your debug adapter's PID and VID are listed in the rules."
            "\n https://raw.githubusercontent.com/platformio/platformio"
            "/develop/scripts/98-openocd-udev.rules\n")

    env.Replace(
        DEBUG_PORT=_look_for_serial_port(tool_settings.get("hwids", [])))

    if not env.subst("$DEBUG_PORT"):
        sys.stderr.write(
            "Error: Please specify `debug_port` for environment.\n")
        env.Exit(1)


def exists(_):
    return True


def generate(env):
    env.AddMethod(ProcessDebug)
    env.AddMethod(DebugToolSettings)
    env.AddMethod(AutodetectDebugPort)
    return env

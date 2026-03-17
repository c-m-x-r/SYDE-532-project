"""
Run NetLogo models via pyNetLogo (NetLogo 6.4.0 + JPype).

Workaround: NetLogo 6.4.0's vid extension bundles asm-4.0.jar which conflicts
with the asm-9.4.jar used by the main app. We patch find_jars to exclude it.
"""

import os
import pynetlogo
import pynetlogo.core as _core
from pathlib import Path

NETLOGO_HOME = str(Path(__file__).parent / "NetLogo-6.4.0-64")
MODEL_PATH = Path(__file__).parent / "desertification-toy.nlogo"


def _find_jars_patched(path):
    """find_jars with asm-4.0.jar excluded to avoid classpath conflict."""
    jars = []
    for root, _, files in os.walk(path):
        for f in files:
            if f == "asm-4.0.jar":
                continue  # conflicts with asm-9.4.jar in lib/app
            if f == "NetLogo.jar":
                jars.insert(0, os.path.join(root, f))
            elif f.endswith(".jar"):
                jars.append(os.path.join(root, f))
    return jars


_core.find_jars = _find_jars_patched


def make_link():
    return pynetlogo.NetLogoLink(netlogo_home=NETLOGO_HOME, gui=False)


if __name__ == "__main__":
    nl = make_link()
    print("Connected to NetLogo OK")

    nl.load_model(str(MODEL_PATH))
    print("Model loaded")

    nl.command("setup")
    for _ in range(100):
        nl.command("go")

    veg = nl.report("vegetation-count")
    deg = nl.report("degraded-count")
    des = nl.report("desert-count")
    print(f"After 100 ticks: vegetation={veg:.0f}  degraded={deg:.0f}  desert={des:.0f}")

    nl.kill_workspace()

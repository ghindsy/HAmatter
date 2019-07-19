#!/usr/bin/env python3
"""Generate an updated requirements_all.txt."""
import difflib
import importlib
import os
from pathlib import Path
import pkgutil
import re
import sys

from script.hassfest.model import Integration

COMMENT_REQUIREMENTS = (
    "Adafruit_BBIO",
    "Adafruit-DHT",
    "avion",
    "beacontools",
    "blinkt",
    "bluepy",
    "bme680",
    "credstash",
    "decora",
    "envirophat",
    "evdev",
    "face_recognition",
    "fritzconnection",
    "i2csense",
    "opencv-python-headless",
    "py_noaa",
    "pybluez",
    "pycups",
    "PySwitchbot",
    "pySwitchmate",
    "python-eq3bt",
    "python-lirc",
    "pyuserinput",
    "raspihats",
    "rpi-rf",
    "RPi.GPIO",
    "smbus-cffi",
    "tensorflow",
    "VL53L1X2",
)

TEST_REQUIREMENTS = (
    "adguardhome",
    "aio_geojson_geonetnz_quakes",
    "aioambient",
    "aioautomatic",
    "aiobotocore",
    "aioesphomeapi",
    "aiohttp_cors",
    "aiohue",
    "aionotion",
    "aioswitcher",
    "aiounifi",
    "aiowwlln",
    "ambiclimate",
    "androidtv",
    "apns2",
    "aprslib",
    "av",
    "axis",
    "bellows-homeassistant",
    "caldav",
    "coinmarketcap",
    "defusedxml",
    "dsmr_parser",
    "eebrightbox",
    "emulated_roku",
    "enocean",
    "ephem",
    "evohomeclient",
    "feedparser-homeassistant",
    "foobot_async",
    "geojson_client",
    "geopy",
    "georss_generic_client",
    "georss_ign_sismologia_client",
    "georss_qld_bushfire_alert_client",
    "getmac",
    "google-api-python-client",
    "gTTS-token",
    "ha-ffmpeg",
    "hangups",
    "HAP-python",
    "hass-nabucasa",
    "haversine",
    "hbmqtt",
    "hdate",
    "herepy",
    "hole",
    "holidays",
    "home-assistant-frontend",
    "homekit[IP]",
    "homematicip",
    "httplib2",
    "huawei-lte-api",
    "iaqualink",
    "influxdb",
    "jsonpath",
    "libpurecool",
    "libsoundtouch",
    "luftdaten",
    "mbddns",
    "mficlient",
    "minio",
    "netdisco",
    "nokia",
    "numpy",
    "oauth2client",
    "paho-mqtt",
    "pexpect",
    "pilight",
    "pillow",
    "plexapi",
    "pmsensor",
    "prometheus_client",
    "ptvsd",
    "pushbullet.py",
    "py-canary",
    "py17track",
    "pyblackbird",
    "pychromecast",
    "pydeconz",
    "pydispatcher",
    "pyheos",
    "pyhomematic",
    "pyHS100",
    "pyiqvia",
    "pylinky",
    "pylitejet",
    "pyMetno",
    "pymfy",
    "pymonoprice",
    "PyNaCl",
    "pynws",
    "pynx584",
    "pyopenuv",
    "pyotp",
    "pyps4-homeassistant",
    "pyqwikswitch",
    "PyRMVtransport",
    "pysma",
    "pysmartapp",
    "pysmartthings",
    "pysonos",
    "pyspcwebgw",
    "python_awair",
    "python-ecobee-api",
    "python-forecastio",
    "python-izone",
    "python-lyric",
    "python-nest",
    "python-velbus",
    "pythonwhois",
    "pytradfri[async]",
    "PyTransportNSW",
    "pyunifi",
    "pyupnp-async",
    "pyvesync",
    "pywebpush",
    "regenmaschine",
    "restrictedpython",
    "rflink",
    "ring_doorbell",
    "ruamel.yaml",
    "rxv",
    "simplisafe-python",
    "sleepyq",
    "smhi-pkg",
    "solaredge",
    "somecomfort",
    "sqlalchemy",
    "srpenergy",
    "statsd",
    "toonapilib",
    "transmissionrpc",
    "twentemilieu",
    "uvcclient",
    "vsure",
    "vultr",
    "wakeonlan",
    "warrant",
    "YesssSMS",
    "zeroconf",
    "zigpy-homeassistant",
)

IGNORE_PIN = ("colorlog>2.1,<3", "keyring>=9.3,<10.0", "urllib3")

URL_PIN = (
    "https://developers.home-assistant.io/docs/"
    "creating_platform_code_review.html#1-requirements"
)


CONSTRAINT_PATH = os.path.join(
    os.path.dirname(__file__), "../homeassistant/package_constraints.txt"
)
CONSTRAINT_BASE = """
pycryptodome>=3.6.6

# Breaks Python 3.6 and is not needed for our supported Python versions
enum34==1000000000.0.0

# This is a old unmaintained library and is replaced with pycryptodome
pycrypto==1000000000.0.0
"""


def has_tests(module: str):
    """Test if a module has tests.

    Module format: homeassistant.components.hue
    Test if exists: tests/components/hue
    """
    path = Path(module.replace(".", "/").replace("homeassistant", "tests"))
    if not path.exists():
        return False

    if not path.is_dir():
        return True

    # Dev environments might have stale directories around
    # from removed tests. Check for that.
    content = [f.name for f in path.glob("*")]

    # Directories need to contain more than `__pycache__`
    # to exist in Git and so be seen by CI.
    return content != ["__pycache__"]


def explore_module(package, explore_children):
    """Explore the modules."""
    module = importlib.import_module(package)

    found = []

    if not hasattr(module, "__path__"):
        return found

    for _, name, _ in pkgutil.iter_modules(module.__path__, package + "."):
        found.append(name)

        if explore_children:
            found.extend(explore_module(name, False))

    return found


def core_requirements():
    """Gather core requirements out of setup.py."""
    reqs_raw = re.search(
        r"REQUIRES = \[(.*?)\]", Path("setup.py").read_text(), re.S
    ).group(1)
    return [x[1] for x in re.findall(r"(['\"])(.*?)\1", reqs_raw)]


def gather_recursive_requirements(domain, seen=None):
    """Recursively gather requirements from a module."""
    if seen is None:
        seen = set()

    seen.add(domain)
    integration = Integration(Path(f"homeassistant/components/{domain}"))
    integration.load_manifest()
    reqs = set(integration.manifest["requirements"])
    for dep_domain in integration.manifest["dependencies"]:
        reqs.update(gather_recursive_requirements(dep_domain, seen))
    return reqs


def comment_requirement(req):
    """Comment out requirement. Some don't install on all systems."""
    return any(ign in req for ign in COMMENT_REQUIREMENTS)


def gather_modules():
    """Collect the information."""
    reqs = {}

    errors = []

    gather_requirements_from_manifests(errors, reqs)
    gather_requirements_from_modules(errors, reqs)

    for key in reqs:
        reqs[key] = sorted(reqs[key], key=lambda name: (len(name.split(".")), name))

    if errors:
        print("******* ERROR")
        print("Errors while importing: ", ", ".join(errors))
        return None

    return reqs


def gather_requirements_from_manifests(errors, reqs):
    """Gather all of the requirements from manifests."""
    integrations = Integration.load_dir(Path("homeassistant/components"))
    for domain in sorted(integrations):
        integration = integrations[domain]

        if not integration.manifest:
            errors.append(f"The manifest for integration {domain} is invalid.")
            continue

        process_requirements(
            errors,
            integration.manifest["requirements"],
            f"homeassistant.components.{domain}",
            reqs,
        )


def gather_requirements_from_modules(errors, reqs):
    """Collect the requirements from the modules directly."""
    for package in sorted(
        explore_module("homeassistant.scripts", True)
        + explore_module("homeassistant.auth", True)
    ):
        try:
            module = importlib.import_module(package)
        except ImportError as err:
            print("{}: {}".format(package.replace(".", "/") + ".py", err))
            errors.append(package)
            continue

        if getattr(module, "REQUIREMENTS", None):
            process_requirements(errors, module.REQUIREMENTS, package, reqs)


def process_requirements(errors, module_requirements, package, reqs):
    """Process all of the requirements."""
    for req in module_requirements:
        if "://" in req:
            errors.append(f"{package}[Only pypi dependencies are allowed: {req}]")
        if req.partition("==")[1] == "" and req not in IGNORE_PIN:
            errors.append(f"{package}[Please pin requirement {req}, see {URL_PIN}]")
        reqs.setdefault(req, []).append(package)


def generate_requirements_list(reqs):
    """Generate a pip file based on requirements."""
    output = []
    for pkg, requirements in sorted(reqs.items(), key=lambda item: item[0]):
        for req in sorted(requirements):
            output.append(f"\n# {req}")

        if comment_requirement(pkg):
            output.append(f"\n# {pkg}\n")
        else:
            output.append(f"\n{pkg}\n")
    return "".join(output)


def requirements_all_output(reqs):
    """Generate output for requirements_all."""
    output = []
    output.append("# Home Assistant core")
    output.append("\n")
    output.append("\n".join(core_requirements()))
    output.append("\n")
    output.append(generate_requirements_list(reqs))

    return "".join(output)


def requirements_test_output(reqs):
    """Generate output for test_requirements."""
    output = []
    output.append("# Home Assistant test")
    output.append("\n")
    output.append(Path("requirements_test.txt").read_text())
    output.append("\n")

    filtered = {
        requirement: modules
        for requirement, modules in reqs.items()
        if any(
            # Always install requirements that are not part of integrations
            not mdl.startswith("homeassistant.components.") or
            # Install tests for integrations that have tests
            has_tests(mdl)
            for mdl in modules
        )
    }
    output.append(generate_requirements_list(filtered))

    return "".join(output)


def gather_constraints():
    """Construct output for constraint file."""
    return (
        "\n".join(
            sorted(
                core_requirements()
                + list(gather_recursive_requirements("default_config"))
            )
            + [""]
        )
        + CONSTRAINT_BASE
    )


def diff_file(filename, content):
    """Diff a file."""
    return list(
        difflib.context_diff(
            [line + "\n" for line in Path(filename).read_text().split("\n")],
            [line + "\n" for line in content.split("\n")],
            filename,
            "generated",
        )
    )


def main(validate):
    """Run the script."""
    if not os.path.isfile("requirements_all.txt"):
        print("Run this from HA root dir")
        return 1

    data = gather_modules()

    if data is None:
        return 1

    reqs_file = requirements_all_output(data)
    reqs_test_file = requirements_test_output(data)
    constraints = gather_constraints()

    files = (
        ("requirements_all.txt", reqs_file),
        ("requirements_test_all.txt", reqs_test_file),
        ("homeassistant/package_constraints.txt", constraints),
    )

    if validate:
        errors = []

        for filename, content in files:
            diff = diff_file(filename, content)
            if diff:
                errors.append("".join(diff))

        if errors:
            print("ERROR - FOUND THE FOLLOWING DIFFERENCES")
            print()
            print()
            print("\n\n".join(errors))
            print()
            print("Please run python3 -m script.gen_requirements_all")
            return 1

        return 0

    for filename, content in files:
        Path(filename).write_text(content)

    return 0


if __name__ == "__main__":
    _VAL = sys.argv[-1] == "validate"
    sys.exit(main(_VAL))

"""Tests for the Fjäråskupan integration."""


from bleak.backends.device import BLEDevice

from spencerassistant.components.bluetooth import BluetoothServiceInfoBleak

from tests.components.bluetooth import generate_advertisement_data

COOKER_SERVICE_INFO = BluetoothServiceInfoBleak(
    name="COOKERHOOD_FJAR",
    address="AA:BB:CC:DD:EE:FF",
    rssi=-60,
    manufacturer_data={},
    service_uuids=[],
    service_data={},
    source="local",
    device=BLEDevice(address="AA:BB:CC:DD:EE:FF", name="COOKERHOOD_FJAR"),
    advertisement=generate_advertisement_data(),
    time=0,
    connectable=True,
)

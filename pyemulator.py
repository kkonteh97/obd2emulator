import sys
import logging
import asyncio
import random
from typing import Any, Union

from bless import BlessServer # type: ignore
from bless.backends.characteristic import GATTCharacteristicProperties
from bless.backends.characteristic import GATTAttributePermissions

from typing import Any, Dict, Union
from command_processor import OBDCommandProcessor
from ecu_settings import ECUSettings

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("OBD2Emulator")

class OBD2Adapter:
    SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
    CHAR_UUID    = "0000ffe1-0000-1000-8000-00805f9b34fb"

    def __init__(self):
        self.ecu = ECUSettings()
        self.server = BlessServer("OBD2 Emulator")
        self.processor = OBDCommandProcessor(self.ecu)
        self.gatt: Dict = {
        self.SERVICE_UUID : {
            self.CHAR_UUID: {
                "Properties": (
                    GATTCharacteristicProperties.read
                    | GATTCharacteristicProperties.write
                    | GATTCharacteristicProperties.notify
                ),
                "Permissions": (
                    GATTAttributePermissions.readable
                    | GATTAttributePermissions.writeable
                ),
                "Value": bytearray(b""),
            }
        },
    }
        
    async def start(self):
        logger.info("Starting BLE OBD2 Adapter…")
        # Create the service and characteristic
        await self._setup_gatt()
        await self.server.start()
        logger.info("BLE OBD2 Adapter started successfully.")

    async def _setup_gatt(self):
        await self.server.add_gatt(self.gatt)
        self.server.read_request_func = self._on_read
        self.server.write_request_func = self._on_write
        logger.info("GATT service and characteristic set up.")
        
    async def stop(self):
        logger.info("Stopping BLE OBD2 Adapter…")
        await self.server.stop()

    def _on_read(self, characteristic, **kwargs):
        return characteristic.value

    def _on_write(self, characteristic, value: bytes, **kwargs):
        cmd = value.decode(errors='ignore').strip()
        logger.info(f"Recieved command: {cmd}")

        responses = self.processor.handle_command(cmd)
        out = responses.encode()
        characteristic.value = out
        self.server.update_value(self.SERVICE_UUID, self.CHAR_UUID)
        logger.debug(f"Responding with:\n{out!r}")    



if __name__ == "__main__":
    adapter = OBD2Adapter()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(adapter.start())
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(adapter.stop())
    finally:
        loop.close()
import asyncio
import random
from BLEClient import BLEClient
import datetime
import os


DEVICE_NAME = "Smart Lock [Group 11]"
PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]

AUTH = [0x00] + PASSCODE
OPEN = [0x01]
CLOSE = [0x02]
SECRET = [0xAA]

async def send_command_and_log(ble, label, command):
    print(f"\n[Client] Sending {label} command: {command}")
    ble.read_new_logs() #clear old logs, this resets last len index

    res = await ble.write_command(command)
    print(f"[Bluetooth Lock] Response: {res}")

    await asyncio.sleep(2.5) #allow logs to accumulate

    logs = ble.read_new_logs()
    print(f"BLE Logs for {label}:")
    for line in logs:
        print(f"[ESP] {line}")

async def test_sequence():
    ble = BLEClient()
    await ble.connect(DEVICE_NAME)
    ble.init_logs()
    print("[*] Connected and initialized BLE log stream. Begin testing")
    try:
            await send_command_and_log(ble, "AUTH", AUTH)
            await send_command_and_log(ble, "OPEN", OPEN)
            await send_command_and_log(ble, "CLOSE", CLOSE)
            await send_command_and_log(ble, "SECRET", SECRET)
            await send_command_and_log(ble, "OPEN", OPEN)
            await send_command_and_log(ble, "CLOSE", CLOSE)
            await send_command_and_log(ble, "SECRET", SECRET)
            await send_command_and_log(ble, "OPEN", OPEN)
            await send_command_and_log(ble, "OPEN", OPEN)
            await send_command_and_log(ble, "CLOSE", CLOSE)
            await send_command_and_log(ble, "CLOSE", CLOSE)

    finally:
        await ble.disconnect()
        print("\n[✓] Disconnected from Smart Lock.")

if __name__ == "__main__":
    asyncio.run(test_sequence())

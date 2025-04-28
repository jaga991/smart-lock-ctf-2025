#!/usr/bin/env python3
import sys
import asyncio
from BLEClient import BLEClient
import datetime
import contextlib
import io

DEVICE_NAME = "Smart Lock [Group 11]"

# Commands
# AUTH = [0x00]
# OPEN = [0x01]
# CLOSE = [0x02]
# PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]

async def run_test():
    ble = BLEClient()
    ble.init_logs()

    session_output = io.StringIO()
    logs = []

    with contextlib.redirect_stdout(session_output):
        print(f'[1] Connecting to "{DEVICE_NAME}"...')
        await ble.connect(DEVICE_NAME)
        print("[!] Connected.")

        try:
            print("runnin test")
            # ---------------------------------
            #  PLACE YOUR TEST HERE 

            # e.g., flood attack or anything

            #  END TEST BLOCK 
            # ---------------------------------

        except Exception as e:
            print(f"\n[!] Exception during test: {e}")

        finally:
            print("[!] Disconnecting...")
            await ble.disconnect()

            logs = ble.read_logs()
            print("\n[ Full ESP32 Logs from this session]")
            if logs:
                for line in logs:
                    print(" ", line)
            else:
                print(" No logs were captured.")

        #  Write all output to log file after stdout redirection block
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"test_logs_{timestamp}.txt"

        with open(log_filename, "w") as f:
            f.write("[ Full Console Output + ESP32 Logs]\n\n")
            f.write(session_output.getvalue())

        print(f"\n Logs saved to {log_filename}")



if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        print("\nProgram Exited by User!")

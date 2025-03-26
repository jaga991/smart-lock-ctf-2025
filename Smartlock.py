#!/usr/bin/env python3
import sys
import asyncio
from BLEClient import BLEClient
from UserInterface import ShowUserInterface
import datetime

DEVICE_NAME = "Smart Lock [Group 11]"

# Commands
AUTH = [0x00]
OPEN = [0x01]
CLOSE = [0x02]
PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]


async def manual_cli():
    ble = BLEClient()
    ble.init_logs()

    print(f'[1] Connecting to "{DEVICE_NAME}"...')
    await ble.connect(DEVICE_NAME)
    print("[!] Connected. Type 'help' for available commands.")

    try:
        while True:
            user_input = input("smartlock> ").strip().lower()

            if user_input == "help":
                print("Commands:")
                print("  auth         - authenticate with passcode")
                print("  open         - open the lock")
                print("  close        - close the lock")
                print("  send <hex>   - send raw hex bytes (e.g., send 01 ff 10)")
                print("  logs         - show recent logs")
                print("  exit         - disconnect and quit")
            
            elif user_input == "auth":
                res = await ble.write_command(AUTH + PASSCODE)
                print("[<] Response:", res)

            elif user_input == "open":
                res = await ble.write_command(OPEN)
                print("[<] Response:", res)

            elif user_input == "close":
                res = await ble.write_command(CLOSE)
                print("[<] Response:", res)

            elif user_input.startswith("send "):
                try:
                    raw = user_input[5:].split()
                    bytes_to_send = [int(b, 16) for b in raw]
                    res = await ble.write_command(bytes_to_send)
                    print("[<] Response:", res)
                except ValueError:
                    print("[!] Invalid hex format. Use: send 01 ff ab ...")

            elif user_input == "logs":
                logs = ble.read_logs()
                if logs:
                    print("[📜 Logs]")
                    for line in logs[-10:]:
                        print(" ", line)
                else:
                    print("[!] No logs yet.")

            elif user_input in ("exit", "quit"):
                break

            else:
                print("[!] Unknown command. Type 'help'.")

    except KeyboardInterrupt:
        print("\n[!] Ctrl+C pressed. Exiting...")

    except Exception as e:
        print(f"\n[!] Unexpected exception: {e}")

    finally:
        print("[!] Disconnecting...")
        await ble.disconnect()

        # Dump all logs after crash/exit
        logs = ble.read_logs()
        print("\n[🔚 Full ESP32 Logs from this session]")
        if logs:
            for line in logs:
                print(" ", line)
        else:
            print(" No logs were captured.")

        # Optional: Save to file
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"cli_session_logs_{timestamp}.txt"
        with open(log_filename, "w") as f:
            for line in logs:
                f.write(line + "\n")
        print(f"\n[✔] Logs saved to {log_filename}")

# Entrypoint
if len(sys.argv) > 1 and sys.argv[1] == "--gui":
    ShowUserInterface()
else:
    try:
        asyncio.run(manual_cli())
    except KeyboardInterrupt:
        print("\nProgram Exited by User!")

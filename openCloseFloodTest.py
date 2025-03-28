# #!/usr/bin/env python3
# import sys
# import asyncio
# from BLEClient import BLEClient
# import datetime
# import io

# DEVICE_NAME = "Smart Lock [Group 11]"
# AUTH = [0x00]
# OPEN = [0x01]
# CLOSE = [0x02]
# PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]

# class TeeLogger:
#     def __init__(self):
#         self.buffer = io.StringIO()
#         self.stdout = sys.stdout

#     def write(self, msg):
#         self.buffer.write(msg)
#         self.stdout.write(msg)
#         self.stdout.flush()

#     def flush(self):
#         self.stdout.flush()

#     def getvalue(self):
#         return self.buffer.getvalue()

# async def run_test():
#     logger = TeeLogger()
#     sys.stdout = logger  # redirect stdout to both console and buffer

#     ble = BLEClient()
#     ble.init_logs()

#     print(f'[1] Connecting to "{DEVICE_NAME}"...')
#     await ble.connect(DEVICE_NAME)
#     print("[!] Connected.")

#     try:
#         print("[2] Authenticating...")
#         res = await ble.write_command(AUTH + PASSCODE)
#         print(f"[AUTH] Response: {res}")

#         if not res or res[0] != 0:
#             print("[X] Authentication failed. Cannot proceed with flooding.")
#             return

#         print("[✔] Authenticated successfully.\n")
#         print("[3] Starting command flood (OPEN + CLOSE)...")

#         delay = 0.01
#         iterations = 1000
#         success = 0
#         failure = 0
#         error = 0

#         for i in range(1, iterations + 1):
#             now = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
#             cmd = OPEN if i % 2 == 1 else CLOSE
#             label = "OPEN" if cmd == OPEN else "CLOSE"

#             try:
#                 res = await ble.write_command(cmd)
#                 print(f"[{now}] [#{i:03}] {label} → Response: {res}")
#                 if res and res[0] == 0:
#                     success += 1
#                 else:
#                     failure += 1
#             except Exception as e:
#                 print(f"[{now}] [#{i:03}] {label} → Exception: {e}")
#                 error += 1

#             await asyncio.sleep(delay)

#         print("\n[Flood Summary]")
#         print(f"  Success responses:   {success}")
#         print(f"  Failure responses:   {failure}")
#         print(f"  Exceptions occurred: {error}")

#     except Exception as e:
#         print(f"\n[!] Unexpected exception: {e}")

#     finally:
#         print("[!] Disconnecting...")
#         await ble.disconnect()

#         logs = ble.read_logs()
#         print("\n[ Full ESP32 Logs from this session]")
#         if logs:
#             for line in logs:
#                 log_time = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
#                 print(f"[{log_time}]  ESP → {line}")
#         else:
#             print(" No logs were captured.")

#         timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
#         log_filename = f"postauth_flood_{timestamp}.txt"
#         with open(log_filename, "w", encoding="utf-8") as f:
#             f.write("[ Full Console Output + ESP32 Logs ]\n\n")
#             f.write(logger.getvalue())

#         print(f"\n[✔] Logs saved to {log_filename}")


# if __name__ == "__main__":
#     try:
#         asyncio.run(run_test())
#     except KeyboardInterrupt:
#         print("\nProgram Exited by User!")
#!/usr/bin/env python3
import sys
import asyncio
from BLEClient import BLEClient
import datetime
import io
import random

DEVICE_NAME = "Smart Lock [Group 11]"
AUTH = [0x00]
PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]

class TeeLogger:
    def __init__(self):
        self.buffer = io.StringIO()
        self.stdout = sys.stdout

    def write(self, msg):
        self.buffer.write(msg)
        self.stdout.write(msg)
        self.stdout.flush()

    def flush(self):
        self.stdout.flush()

    def getvalue(self):
        return self.buffer.getvalue()

async def run_test():
    logger = TeeLogger()
    sys.stdout = logger

    ble = BLEClient()
    ble.init_logs()

    print(f'[1] Connecting to "{DEVICE_NAME}"...')
    await ble.connect(DEVICE_NAME)
    print("[!] Connected.")

    try:
        print("[2] Authenticating...")
        res = await ble.write_command(AUTH + PASSCODE)
        print(f"[AUTH] Response: {res}")

        if not res or res[0] != 0:
            print("[X] Authentication failed. Cannot proceed with fuzzing.")
            return

        print("[✔] Authenticated successfully.\n")
        print("[3] Starting random command flood...")

        delay = 0.1
        iterations = 200
        success = 0
        failure = 0
        error = 0

        for i in range(1, iterations + 1):
            now = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]

            # Generate random command: random length between 1 and 20
            length = random.randint(1, 100)
            cmd = [random.randint(0x00, 0xFF) for _ in range(length)]

            try:
                res = await ble.write_command(cmd)
                print(f"[{now}] [#{i:04}] SENT → {cmd} → RESP: {res}")
                if res and res[0] == 0:
                    success += 1
                else:
                    failure += 1
            except Exception as e:
                print(f"[{now}] [#{i:04}] SENT → {cmd} → EXCEPTION: {e}")
                error += 1

            await asyncio.sleep(delay)

        print("\n[Fuzz Summary]")
        print(f"  Success responses:   {success}")
        print(f"  Failure responses:   {failure}")
        print(f"  Exceptions occurred: {error}")

    except Exception as e:
        print(f"\n[!] Unexpected exception: {e}")

    finally:
        print("[!] Disconnecting...")
        await ble.disconnect()

        logs = ble.read_logs()
        print("\n[ Full ESP32 Logs from this session]")
        if logs:
            for line in logs:
                log_time = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
                print(f"[{log_time}]  ESP → {line}")
        else:
            print(" No logs were captured.")

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"postauth_randomfuzz_{timestamp}.txt"
        with open(log_filename, "w", encoding="utf-8") as f:
            f.write("[ Full Console Output + ESP32 Logs ]\n\n")
            f.write(logger.getvalue())

        print(f"\n[✔] Logs saved to {log_filename}")

if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        print("\nProgram Exited by User!")

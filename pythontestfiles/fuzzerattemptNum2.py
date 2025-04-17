import asyncio
import random
from BLEClient import BLEClient
import datetime
import os

DEVICE_NAME = "Smart Lock [Group 11]"
PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]
AUTH = [0x00]

MAX_ITERATIONS = 500
LOG_DIR = "afl_ble_fuzz"
os.makedirs(LOG_DIR, exist_ok=True)

def assign_energy():
    return random.randint(3, 5)

def generate_sequence():
    """Create a random sequence of opcodes"""
    length = random.randint(2, 5)
    return [random.randint(0, 255) for _ in range(length)]

def map_opcode_to_command(opcode):
    if opcode == 0x00:
        return AUTH + PASSCODE
    elif opcode == 0x01:
        return [0x01]  # OPEN
    elif opcode == 0x02:
        return [0x02]  # CLOSE
    else:
        return [opcode]  # Fuzzed/unknown

def save_test_case(seq, reason):
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    file = os.path.join(LOG_DIR, f"{reason}_{ts}.txt")
    with open(file, "w") as f:
        f.write(" ".join(f"{b:#04x}" for b in seq))
    print(f"[Saved] {reason.upper()} → {file}")

async def run_afl_style_fuzzer():
    ble = BLEClient()
    await ble.connect(DEVICE_NAME)
    ble.init_logs()

    print("[*] Fuzzer started...\n")

    try:
        for i in range(1, MAX_ITERATIONS + 1):
            energy = assign_energy()
            seed_seq = generate_sequence()

            for e in range(energy):
                full_sequence = seed_seq.copy()
                current_state = "UNAUTHENTICATED"
                print(f"\n[#{i}.{e}] Sequence: {[hex(c) for c in full_sequence]}")

                for opcode in full_sequence:
                    command = map_opcode_to_command(opcode)
                    try:
                        res = await ble.write_command(command)
                        logs = ble.read_logs()
                        logs_str = " ".join(logs).lower()

                        print(f"[>] Sent: {command}")
                        print(f"[<] Response: {res}")

                        # Update state if needed
                        if res and res[0] == 0 and opcode == 0x00:
                            current_state = "AUTHENTICATED"
                        elif res and res[0] != 0:
                            current_state = "ERROR"

                        if "guru meditation" in logs_str or "rebooting" in logs_str:
                            save_test_case(full_sequence, "crash")
                            break  # stop further commands

                        elif not res or res[0] != 0:
                            save_test_case(full_sequence, "nonsuccess")
                            break

                    except Exception as e:
                        print(f"[!] Exception: {e}")
                        save_test_case(full_sequence, "exception")
                        break

                    await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n[!] Fuzzing interrupted.")

    finally:
        await ble.disconnect()
        print("\n[✓] Fuzzing completed.")

if __name__ == "__main__":
    asyncio.run(run_afl_style_fuzzer())

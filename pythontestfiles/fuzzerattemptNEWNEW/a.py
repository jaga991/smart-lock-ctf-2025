import asyncio
import random
import os
import datetime
import sys
from BLEClient import BLEClient

# === Configuration ===
DEVICE_NAME = "Smart Lock [Group 11]"
PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]
AUTH_OPCODE = 0x00

SEED_INPUTS = [
    [0x00],
    [0x00, 0x01],
    [0x00, 0x01, 0x02],
    [0xAA],  # Example hidden command
]

MAX_ITERATIONS = 50
SLEEP_BETWEEN_COMMANDS = 1.5
SLEEP_AFTER_RECONNECT = 4.0

timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
OUTPUT_DIR = os.path.join("AFL_Fuzz_Outputs", f"session_{timestamp}")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === Globals for log tracking ===
seen_log_lines = set()

# === Mutation ===
def mutate_input(seed):
    # TODO: Implement mutation logic (flip, insert, replace, etc.)
    return seed.copy()

# === Energy Assignment ===
def assign_energy(seed):
    # TODO: Assign how many mutations a seed should get
    return 1

# === Queue Selection ===
def choose_next(queue):
    # TODO: Add smarter queue logic if desired
    return random.choice(queue)

# === Interestingness Heuristic ===
def is_interesting(responses, logs):
    # TODO: Replace with your heuristic (e.g., unique logs, special codes)
    return False

# === Save interesting test case ===
def save_input(input_seq, logs, label="interesting"):
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = os.path.join(OUTPUT_DIR, f"{label}_{ts}.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("Input: " + " ".join(hex(x) for x in input_seq) + "\n")
        f.write("Logs:\n")
        for l in logs:
            f.write("  " + l.strip() + "\n")
    print(f"[✓] Saved {label} input to {filepath}")

# === Send input to target ===
async def run_target(ble, input_seq):
    responses = []
    logs = []

    for opcode in input_seq:
        command = [opcode]
        if opcode == AUTH_OPCODE:
            command += PASSCODE

        ble.read_new_logs()
        try:
            res = await ble.write_command(command)
            await asyncio.sleep(SLEEP_BETWEEN_COMMANDS)
            new_logs = ble.read_new_logs()
        except Exception as e:
            res = [999]
            new_logs = [f"Exception: {e}"]

        responses.append(res)
        logs.extend(new_logs)

    return responses, logs

# === Optional: Reboot wait logic ===
async def wait_for_esp_reboot_logs(ble, timeout=5):
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        logs = ble.read_new_logs()
        if any("boot:" in line.lower() or "esp-rom" in line.lower() for line in logs):
            return True
        await asyncio.sleep(0.5)
    return False

# === Main fuzz loop ===
async def afl_fuzz():
    queue = SEED_INPUTS[:]

    try:
        for i in range(MAX_ITERATIONS):
            print(f"\n[#{i:03}] Starting test cycle...")
            ble = BLEClient()

            try:
                await ble.connect(DEVICE_NAME)
                ble.init_logs()
                await asyncio.sleep(SLEEP_AFTER_RECONNECT)
                await wait_for_esp_reboot_logs(ble)

                seed = choose_next(queue)
                energy = assign_energy(seed)

                for _ in range(energy):
                    mutated = mutate_input(seed)
                    responses, logs = await run_target(ble, mutated)

                    if is_interesting(responses, logs):
                        save_input(mutated, logs)
                        queue.append(mutated)

                await ble.disconnect()
                await asyncio.sleep(SLEEP_AFTER_RECONNECT)

            except Exception as e:
                print(f"[!] Error in cycle #{i}: {e}")
                await ble.disconnect()

    except KeyboardInterrupt:
        print("\n[!] Fuzzing interrupted.")

    print("\n[✓] Fuzzing complete.")
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(afl_fuzz())

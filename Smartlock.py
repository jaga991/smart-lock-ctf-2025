import asyncio
import random
import os
import datetime
import sys
import json
from BLEClient import BLEClient

# === Configuration ===
DEVICE_NAME = "Smart Lock [Group 11]"
PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]
AUTH_OPCODE = 0x00

SEED_INPUTS = [
    [0x00],
    [0x00, 0x01],
    [0x00, 0x01, 0x02],
    [0x00, 0xAA],
    [0x00, 0xA],
    [0x00, 0xB],
    [0x00, 0x3F],
]

MAX_ITERATIONS = 20
SLEEP_BETWEEN_COMMANDS = 2.0
SLEEP_AFTER_RECONNECT = 4.0
WEIGHT_DECAY = 0.9
HIGH_WEIGHT = 3.0
LOW_WEIGHT = 0.5

timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
OUTPUT_DIR = os.path.join("AFL_Fuzz_Outputs", f"session_{timestamp}")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === Globals for tracking ===
seen_log_lines = set()
seen_responses = set()
seen_inputs = set()

# === Mutation ===
def mutate_input(seed):
    m = seed.copy()
    num_mutations = random.randint(1, 4)  # 1-4 mutations now

    for _ in range(num_mutations):
        mutation_type = random.choice(['flip', 'insert', 'delete', 'replace', 'duplicate', 'lengthen'])

        if mutation_type == 'flip' and len(m) > 0:
            idx = random.randint(0, len(m) - 1)
            m[idx] ^= 1 << random.randint(0, 7)

        elif mutation_type == 'insert':
            idx = random.randint(0, len(m))
            m.insert(idx, random.randint(0, 255))

        elif mutation_type == 'delete' and len(m) > 1:
            idx = random.randint(0, len(m) - 1)
            del m[idx]

        elif mutation_type == 'replace' and len(m) > 0:
            idx = random.randint(0, len(m) - 1)
            m[idx] = random.randint(0, 255)

        elif mutation_type == 'duplicate' and len(m) > 0:
            idx = random.randint(0, len(m) - 1)
            m.insert(idx, m[idx])

        elif mutation_type == 'lengthen':
            idx = random.randint(0, len(m))
            m.insert(idx, random.randint(0, 255))  # Insert random byte, making input longer

    return m[:256]  # limit length just in case

# === Energy Assignment ===
def assign_energy(seed):
    base_energy = 5
    bonus = min(len(seed) // 2, 5)
    return base_energy + bonus

# === Queue Selection ===
def choose_next(queue):
    total_weight = sum(w for _, w in queue)
    choice = random.uniform(0, total_weight)
    upto = 0
    for seq, weight in queue:
        if upto + weight >= choice:
            return seq
        upto += weight
    return random.choice(queue)[0]

# === Interestingness Heuristic ===
def is_interesting(responses, logs):
    global seen_log_lines, seen_responses
    interesting = False

    for line in logs:
        normalized_line = line.strip().lower()
        if normalized_line not in seen_log_lines:
            seen_log_lines.add(normalized_line)
            interesting = True

    for res in responses:
        tuple_res = tuple(res)
        if tuple_res not in seen_responses:
            seen_responses.add(tuple_res)
            interesting = True

    return interesting

# === Save and Load Queue (JSON version) ===
def save_queue(queue):
    filepath = os.path.join(OUTPUT_DIR, "saved_queue.json")
    serializable = [{"input": seq, "weight": weight} for seq, weight in queue]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2)
    print(f"[✓] Queue saved to {filepath}")

def load_queue(path):
    with open(path, "r", encoding="utf-8") as f:
        loaded_serialized = json.load(f)
    loaded_queue = [(entry["input"], entry["weight"]) for entry in loaded_serialized]

    # Rebuild seen_inputs
    for input_seq, _ in loaded_queue:
        seen_inputs.add(tuple(input_seq))

    print(f"[✓] Loaded {len(loaded_queue)} inputs from {path}")
    return loaded_queue

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

# === Run Input ===
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
            print("  [ESP LOGS]")
            for line in new_logs:
                print("   ", line)
        except Exception as e:
            res = [999]
            new_logs = [f"Exception: {e}"]

        responses.append(res)
        logs.extend(new_logs)
    return responses, logs

# === Wait for ESP reboot ===
async def wait_for_esp_reboot_logs(ble, timeout=5):
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        logs = ble.read_new_logs()
        if any("boot:" in line.lower() or "esp-rom" in line.lower() for line in logs):
            return True
        await asyncio.sleep(0.5)
    return False

# === Print Queue Debug Overview ===
def print_queue_overview(queue, top_n=5):
    print("\n[Queue Overview]")
    sorted_q = sorted(queue, key=lambda x: -x[1])
    for idx, (seq, weight) in enumerate(sorted_q[:top_n]):
        print(f" {idx+1:02d}. Weight={weight:.2f} | Input={seq}")
    print(f" [Total entries: {len(queue)}]\n")

# === Main fuzz loop ===
async def afl_fuzz(queue):
    try:
        for i in range(MAX_ITERATIONS):
            print(f"\n[#{i:03}] Starting test cycle...")
            ble = BLEClient()
            ble.init_logs()

            try:
                seed = choose_next(queue)
                energy = assign_energy(seed)

                for _ in range(energy):
                    await ble.connect(DEVICE_NAME)
                    await asyncio.sleep(SLEEP_AFTER_RECONNECT)
                    await wait_for_esp_reboot_logs(ble)

                    mutated = mutate_input(seed)
                    mutated_tuple = tuple(mutated)

                    # Duplicate detection
                    if mutated_tuple in seen_inputs:
                        print("[!] Skipping duplicate mutated input.")
                        await ble.disconnect()
                        await asyncio.sleep(SLEEP_AFTER_RECONNECT)
                        continue

                    print("Currently testing mutated input:", mutated)
                    responses, logs = await run_target(ble, mutated)

                    is_interesting_case = is_interesting(responses, logs)
                    new_weight = HIGH_WEIGHT if is_interesting_case else LOW_WEIGHT
                    queue.append((mutated, new_weight))
                    seen_inputs.add(mutated_tuple)

                    if is_interesting_case:
                        save_input(mutated, logs)

                    await ble.disconnect()
                    await asyncio.sleep(SLEEP_AFTER_RECONNECT)

                # Decay existing weights
                for idx in range(len(queue)):
                    seq, w = queue[idx]
                    queue[idx] = (seq, w * WEIGHT_DECAY)

                print_queue_overview(queue)

            except Exception as e:
                print(f"[!] Error in cycle #{i}: {e}")
                await ble.disconnect()

    except KeyboardInterrupt:
        print("\n[!] Fuzzing interrupted.")

    finally:
        save_queue(queue)
        print("\n[✓] Fuzzing complete.")
        sys.exit(0)

# === Entrypoint ===
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", type=str, help="Path to previous saved_queue.json")
    args = parser.parse_args()

    if args.resume:
        if os.path.exists(args.resume):
            queue = load_queue(args.resume)
        else:
            print(f"[X] Queue file not found: {args.resume}")
            sys.exit(1)
    else:
        queue = [(seed, 1.0) for seed in SEED_INPUTS]
        for seed in SEED_INPUTS:
            seen_inputs.add(tuple(seed))

    asyncio.run(afl_fuzz(queue))

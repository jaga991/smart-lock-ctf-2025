import asyncio
import random
from BLEClient import BLEClient
import datetime
import os

DEVICE_NAME = "Smart Lock [Group 11]"
PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]
AUTH = [0x00]

# AFL-like configuration
SEED_QUEUE = [
    AUTH + PASSCODE,
    [0x01],  # OPEN
    [0x02],  # CLOSE
]

FailureQ = []
InterestingQ = []

MAX_MUTATION_LEN = 20
MAX_ITERATIONS = 1000
LOG_DIR = "fuzz_logs"

os.makedirs(LOG_DIR, exist_ok=True)

def assign_energy(input_seq):
    # Fixed energy value; could be adjusted based on length or input hash
    return 5

def mutate(input_seq):
    m = input_seq.copy()
    for _ in range(random.randint(1, 5)):
        if len(m) > 0 and random.random() < 0.5:
            idx = random.randint(0, len(m) - 1)
            m[idx] = random.randint(0, 255)
        else:
            m.append(random.randint(0, 255))
    return m[:MAX_MUTATION_LEN]

def save_crash(input_bytes, reason="crash"):
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(LOG_DIR, f"{reason}_{ts}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(" ".join(f"{b:#04x}" for b in input_bytes))
    print(f"[Saved] Input saved to {path} due to: {reason}")

async def run_fuzz():
    ble = BLEClient()
    await ble.connect(DEVICE_NAME)
    ble.init_logs()

    try:
        for iteration in range(MAX_ITERATIONS):
            seed = random.choice(SEED_QUEUE)
            energy = assign_energy(seed)

            for i in range(energy):
                fuzz_input = mutate(seed)

                try:
                    res = await ble.write_command(fuzz_input)
                    print(f"[{iteration:04}] Input: {fuzz_input} → Response: {res}")

                    logs = ble.read_logs()
                    logs_str = " ".join(logs).lower()

                    # Check for ESP32 crash indicators
                    if "guru meditation" in logs_str or "rebooting" in logs_str:
                        print("Crash detected from ESP32 logs")
                        FailureQ.append(fuzz_input)
                        save_crash(fuzz_input, "guru")

                    # Flag any unexpected or non-success responses
                    if not res or res[0] != 0:
                        InterestingQ.append(fuzz_input)
                        print("Non-success response detected")
                        save_crash(fuzz_input, "nonsuccess")

                except Exception as e:
                    print(f"Exception occurred: {e}")
                    FailureQ.append(fuzz_input)
                    save_crash(fuzz_input, "exception")

                await asyncio.sleep(1.0)

    except KeyboardInterrupt:
        print("\nFuzzing interrupted by user.")

    finally:
        await ble.disconnect()
        print("\nFuzzing session completed.")
        print(f"Total failures: {len(FailureQ)}")
        print(f"Interesting responses: {len(InterestingQ)}")

if __name__ == "__main__":
    asyncio.run(run_fuzz())

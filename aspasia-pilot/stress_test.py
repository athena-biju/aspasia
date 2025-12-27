import requests
import time
import random
import uuid
import statistics

# Configuration
API_URL = "http://127.0.0.1:8000/enforce"
NUM_TRANSACTIONS = 100  # How many to simulate

print(f"--- STARTING ASPASIA STRESS TEST ({NUM_TRANSACTIONS} txs) ---")
print(f"Targeting Intelligence Layer at: {API_URL}\n")

latencies = []
decisions = {"BLOCK": 0, "FLAG": 0, "ALLOW": 0}

start_time = time.time()

for i in range(NUM_TRANSACTIONS):
    # 1. Randomize the Data (Simulate real traffic)
    is_sketchy = random.random() < 0.2  # 20% chance of no KYC
    is_high_value = random.random() < 0.3 # 30% chance of > 100k
    
    amount = 250000 if is_high_value else random.randint(100, 90000)
    kyc_status = False if is_sketchy else True
    
    payload = {
        "id": f"tx_{uuid.uuid4().hex[:8]}",
        "originator": {"kyc": kyc_status, "id": "bank_gen"},
        "beneficiary": {},
        "amount": amount,
        "currency": "EUR"
    }

    # 2. Measure the API Call (The "Speed" Promise)
    req_start = time.time()
    try:
        response = requests.post(API_URL, json=payload)
        latency = (time.time() - req_start) * 1000 # Convert to ms
        latencies.append(latency)
        
        # 3. Record the Decision
        data = response.json()
        decision = data["decision"]
        decisions[decision] += 1
        
        # Visual feedback (dots)
        symbol = "✅" if decision == "ALLOW" else ("⛔" if decision == "BLOCK" else "🚩")
        print(symbol, end="", flush=True)
        
    except Exception as e:
        print("X", end="", flush=True)

total_time = time.time() - start_time

print(f"\n\n--- PERFORMANCE REPORT ---")
print(f"Total Transactions: {NUM_TRANSACTIONS}")
print(f"Total Time:         {total_time:.2f} seconds")
print(f"Avg Latency:        {statistics.mean(latencies):.2f} ms")
print(f"Max Latency:        {max(latencies):.2f} ms")
print(f"Throughput:         {NUM_TRANSACTIONS / total_time:.0f} tx/sec")

print(f"\n--- COMPLIANCE BREAKDOWN ---")
print(f"Strict Liability Blocks: {decisions['BLOCK']} (Ex-Ante Enforcement)")
print(f"Risk Flags:              {decisions['FLAG']}")
print(f"Settled Instantly:       {decisions['ALLOW']}")
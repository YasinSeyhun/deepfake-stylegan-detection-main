import subprocess
import time
import sys
import os
import signal

def run_simulation():
    print("Starting Federated Learning Simulation...")
    print("-----------------------------------------")
    
    # 1. Start Server
    print("🚀 Starting Server...")
    server_process = subprocess.Popen(
        [sys.executable, "server/server.py"],
        cwd=os.getcwd(),
        env=os.environ.copy()
    )
    
    # Give server time to start
    time.sleep(5)
    
    clients = []
    num_clients = 2
    
    # 2. Start Clients
    for i in range(num_clients):
        client_id = f"client_{i+1}"
        print(f"🚀 Starting {client_id}...")
        client_process = subprocess.Popen(
            [sys.executable, "client_machine/client.py", client_id],
            cwd=os.getcwd(),
            env=os.environ.copy()
        )
        clients.append(client_process)
        time.sleep(2) # Stagger starts
        
    print(f"\n✅ Simulation running with 1 server and {num_clients} clients.")
    print("Press Ctrl+C to stop everything.")
    
    try:
        while True:
            # Check if server is still alive
            if server_process.poll() is not None:
                print("Server exited unexpectedly!")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping simulation...")
        
    # Cleanup
    server_process.terminate()
    for c in clients:
        c.terminate()
        
    print("Cleaned up.")

if __name__ == "__main__":
    run_simulation()

import threading
import time
import pandas as pd

def read_demo_data(csv_file, update_interval, stop_event):
    df = pd.read_csv(csv_file)
    while not stop_event.is_set():
        for _, row in df.iterrows():
            if stop_event.is_set():
                break
            print("Publishing demo data", row.to_dict())  # Replace with actual data handling logic
            time.sleep(update_interval)

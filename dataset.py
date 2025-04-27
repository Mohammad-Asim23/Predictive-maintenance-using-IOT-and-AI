import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

# Define parameters
num_samples = 10000
failure_rate = 0.15  # 15% of samples will be failures
assets = ['A1', 'A2', 'A3', 'A4']

# Create a start date
start_date = datetime(2025, 4, 1)

# Create empty lists to store data
data = []

# Function to add noise to a value
def add_noise(value, noise_level=0.05):
    return value * (1 + np.random.normal(0, noise_level))

# Generate data for each asset
for i in range(num_samples):
    # Generate timestamp
    timestamp = start_date + timedelta(minutes=5 * i)
    
    # Randomly select an asset
    asset_id = random.choice(assets)
    
    # Initialize all sensor values as NaN
    temp_sensor_A1 = np.nan
    humidity_sensor_A1 = np.nan
    waterproof_temp_A2 = np.nan
    ultrasonic_distance_A3 = np.nan
    flow_rate_A4 = np.nan
    
    # Determine if this sample is a failure (weighted to ensure we get enough failures)
    is_failure = 1 if random.random() < failure_rate else 0
    
    # Generate sensor values based on asset type with more realistic patterns
    if asset_id == 'A1':
        # Base values
        base_temp = np.random.uniform(20, 30)
        base_humidity = np.random.uniform(35, 60)
        
        # Add normal variation
        temp_sensor_A1 = add_noise(base_temp)
        humidity_sensor_A1 = add_noise(base_humidity)
        
        if is_failure:
            # For failures, sometimes the values are in normal range but with subtle deviations
            # Other times they're clearly abnormal
            failure_type = random.random()
            
            if failure_type < 0.3:  # High temperature failure
                temp_sensor_A1 = np.random.uniform(31, 40)
                # Humidity might still be normal
                if random.random() < 0.5:
                    humidity_sensor_A1 = np.random.uniform(55, 75)
            elif failure_type < 0.6:  # Low temperature failure
                temp_sensor_A1 = np.random.uniform(10, 19)
                # Humidity might still be normal
                if random.random() < 0.5:
                    humidity_sensor_A1 = np.random.uniform(25, 40)
            else:  # Subtle failure - values close to normal but with a pattern
                # Temperature slightly elevated and humidity slightly elevated
                temp_sensor_A1 = np.random.uniform(28, 33)
                humidity_sensor_A1 = np.random.uniform(58, 68)
    
    elif asset_id == 'A2':
        # Base values
        base_temp = np.random.uniform(45, 65)
        
        # Add normal variation
        waterproof_temp_A2 = add_noise(base_temp)
        
        if is_failure:
            failure_type = random.random()
            
            if failure_type < 0.4:  # High temperature failure
                waterproof_temp_A2 = np.random.uniform(72, 90)
            elif failure_type < 0.7:  # Low temperature failure
                waterproof_temp_A2 = np.random.uniform(25, 40)
            else:  # Subtle failure - temperature in upper normal range but with fluctuations
                waterproof_temp_A2 = np.random.uniform(66, 75)
    
    elif asset_id == 'A3':
        # Base values
        base_distance = np.random.uniform(80, 120)
        
        # Add normal variation
        ultrasonic_distance_A3 = add_noise(base_distance)
        
        if is_failure:
            failure_type = random.random()
            
            if failure_type < 0.35:  # Distance too small
                ultrasonic_distance_A3 = np.random.uniform(40, 75)
            elif failure_type < 0.7:  # Distance too large
                ultrasonic_distance_A3 = np.random.uniform(130, 180)
            else:  # Subtle failure - distance at edge of normal range with fluctuations
                ultrasonic_distance_A3 = np.random.uniform(75, 85) if random.random() < 0.5 else np.random.uniform(120, 130)
    
    elif asset_id == 'A4':
        # Base values
        base_flow = np.random.uniform(6, 10)
        
        # Add normal variation
        flow_rate_A4 = add_noise(base_flow)
        
        if is_failure:
            failure_type = random.random()
            
            if failure_type < 0.4:  # Flow rate too low
                flow_rate_A4 = np.random.uniform(1, 5)
            elif failure_type < 0.7:  # Flow rate too high
                flow_rate_A4 = np.random.uniform(12, 16)
            else:  # Subtle failure - flow rate at edge of normal range
                # Sometimes failures have values that overlap with normal operation
                flow_rate_A4 = np.random.uniform(5, 6.5) if random.random() < 0.5 else np.random.uniform(10, 11.5)
    
    # Add the data point
    data.append({
        'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'asset_id': asset_id,
        'temp_sensor_A1': temp_sensor_A1,
        'humidity_sensor_A1': humidity_sensor_A1,
        'waterproof_temp_A2': waterproof_temp_A2,
        'ultrasonic_distance_A3': ultrasonic_distance_A3,
        'flow_rate_A4': flow_rate_A4,
        'failure': is_failure
    })

# Create DataFrame
df = pd.DataFrame(data)

# Save to CSV
output_file = 'realistic_dataset_with_failures.csv'
df.to_csv(output_file, index=False)

# Print statistics
failure_count = df['failure'].sum()
success_count = len(df) - failure_count
print(f"Generated {len(df)} samples with {failure_count} failures ({failure_count/len(df)*100:.2f}%)")
print(f"Failures by asset:")
for asset in assets:
    asset_failures = df[(df['asset_id'] == asset) & (df['failure'] == 1)].shape[0]
    asset_total = df[df['asset_id'] == asset].shape[0]
    print(f"  {asset}: {asset_failures} failures out of {asset_total} samples ({asset_failures/asset_total*100:.2f}%)")

print(f"Dataset saved to {output_file}")
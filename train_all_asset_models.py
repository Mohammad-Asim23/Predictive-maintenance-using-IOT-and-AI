import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from imblearn.over_sampling import SMOTE, RandomOverSampler
import matplotlib.pyplot as plt
import os
from sklearn.utils.class_weight import compute_class_weight

# Create a directory to save models if it doesn't exist
if not os.path.exists('models'):
    os.makedirs('models')

# Create a directory to save scalers if it doesn't exist
if not os.path.exists('scalers'):
    os.makedirs('scalers')

# Load the dataset
df = pd.read_csv('realistic_dataset_with_failures.csv')

# Define a function to train and save a model for a specific asset
def train_asset_model(asset_id, features, df):
    print(f"\n=== Training model for Asset {asset_id} ===")
    
    # Filter data for the specific asset and select relevant sensors
    df_asset = df[df['asset_id'] == asset_id][features + ['failure']]
    
    # Drop rows with missing sensor values
    df_asset = df_asset.dropna()
    
    # Split data into features (X) and target (y)
    X_asset = df_asset[features]
    y_asset = df_asset['failure']
    
    # Split the data into training and testing sets (80% training, 20% testing)
    X_train, X_test, y_train, y_test = train_test_split(X_asset, y_asset, test_size=0.2, random_state=42)
    
    # Standardize the features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Save the scaler for later use
    import joblib
    joblib.dump(scaler, f'scalers/scaler_{asset_id}.pkl')
    
    print(f"Training data distribution for Asset {asset_id}:")
    print(y_train.value_counts())
    
    # Check if there are enough minority samples for SMOTE
    if sum(y_train == 1) > 5:
        # Apply SMOTE to oversample the minority class
        smote = SMOTE(sampling_strategy='auto', random_state=42)
        X_train_resampled, y_train_resampled = smote.fit_resample(X_train_scaled, y_train)
        print("Using SMOTE for oversampling")
    else:
        # Use RandomOverSampler instead
        ros = RandomOverSampler(random_state=42)
        X_train_resampled, y_train_resampled = ros.fit_resample(X_train_scaled, y_train)
        print("Using RandomOverSampler due to insufficient minority samples")
    
    # Define the neural network model
    model = Sequential()
    model.add(Dense(32, input_dim=X_train_resampled.shape[1], activation='relu'))
    model.add(Dense(16, activation='relu'))
    model.add(Dense(1, activation='sigmoid'))
    
    # Compute class weights
    class_weights = compute_class_weight(class_weight='balanced', 
                                        classes=np.unique(y_train_resampled), 
                                        y=y_train_resampled)
    class_weight_dict = {i: weight for i, weight in enumerate(class_weights)}
    
    # Compile the model
    model.compile(optimizer='adam', loss='binary_crossentropy', 
                 metrics=['accuracy', tf.keras.metrics.Precision(), tf.keras.metrics.Recall()])
    
    # Train the model with early stopping
    early_stopping = tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
    
    history = model.fit(X_train_resampled, y_train_resampled, 
                       epochs=100, 
                       batch_size=32, 
                       validation_data=(X_test_scaled, y_test),
                       class_weight=class_weight_dict,
                       callbacks=[early_stopping],
                       verbose=0)
    
    # Evaluate the model
    y_pred_proba = model.predict(X_test_scaled, verbose=0)
    y_pred = (y_pred_proba > 0.3).astype("int32")
    
    # Print evaluation metrics
    accuracy = accuracy_score(y_test, y_pred)
    print(f'Accuracy: {accuracy * 100:.2f}%')
    
    print('Confusion Matrix:')
    print(confusion_matrix(y_test, y_pred))
    
    print('\nClassification Report:')
    print(classification_report(y_test, y_pred))
    
    # Save the model
    model.save(f'models/model_{asset_id}.h5')
    print(f"Model for Asset {asset_id} saved to models/model_{asset_id}.h5")
    
    # Create and save precision-recall curve
    from sklearn.metrics import precision_recall_curve, auc
    precision, recall, thresholds = precision_recall_curve(y_test, y_pred_proba)
    pr_auc = auc(recall, precision)
    print(f'PR AUC: {pr_auc:.4f}')
    
    plt.figure(figsize=(8, 6))
    plt.plot(recall, precision, label=f'PR Curve (AUC = {pr_auc:.4f})')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title(f'Precision-Recall Curve - Asset {asset_id}')
    plt.legend()
    plt.savefig(f'models/pr_curve_{asset_id}.png')
    plt.close()
    
    return model, scaler

# Define features for each asset
asset_features = {
    'A1': ['temp_sensor_A1', 'humidity_sensor_A1'],
    'A2': ['waterproof_temp_A2'],
    'A3': ['ultrasonic_distance_A3'],
    'A4': ['flow_rate_A4']
}

# Train and save models for each asset
models = {}
scalers = {}
for asset_id, features in asset_features.items():
    model, scaler = train_asset_model(asset_id, features, df)
    models[asset_id] = model
    scalers[asset_id] = scaler

print("\nAll models trained and saved successfully!")
# Import necessary libraries
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from imblearn.over_sampling import SMOTE

# Load the dataset
df = pd.read_csv('realistic_dataset_with_failures.csv')

# Filter data for Asset A1 and select relevant sensors
df_A1 = df[df['asset_id'] == 'A1'][['temp_sensor_A1', 'humidity_sensor_A1', 'failure']]

# Drop rows with missing sensor values (if necessary)
df_A1 = df_A1.dropna()

# Split data into features (X) and target (y)
X_A1 = df_A1[['temp_sensor_A1', 'humidity_sensor_A1']]  # Features
y_A1 = df_A1['failure']  # Target

# Split the data into training and testing sets (80% training, 20% testing)
X_train, X_test, y_train, y_test = train_test_split(X_A1, y_A1, test_size=0.2, random_state=42)

# Standardize the features (important for Neural Networks)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print("ytain value: ",y_train.value_counts())

# Check if there are enough minority samples for SMOTE
if sum(y_train == 1) > 5:
    # Apply SMOTE to oversample the minority class in the training data
    smote = SMOTE(sampling_strategy='auto', random_state=42)
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train_scaled, y_train)
else:
    # If not enough samples, use a simpler oversampling technique or the original data
    from imblearn.over_sampling import RandomOverSampler
    ros = RandomOverSampler(random_state=42)
    X_train_resampled, y_train_resampled = ros.fit_resample(X_train_scaled, y_train)
    print("Using RandomOverSampler instead of SMOTE due to insufficient minority samples")

# Define the neural network model
model = Sequential()
model.add(Dense(32, input_dim=X_train_resampled.shape[1], activation='relu'))  # Input layer with 32 neurons
model.add(Dense(16, activation='relu'))  # Hidden layer with 16 neurons
model.add(Dense(1, activation='sigmoid'))  # Output layer with sigmoid activation (binary classification)

# Compile the model with class weights to give more importance to minority class
from sklearn.utils.class_weight import compute_class_weight
class_weights = compute_class_weight(class_weight='balanced', 
                                    classes=np.unique(y_train_resampled), 
                                    y=y_train_resampled)
class_weight_dict = {i: weight for i, weight in enumerate(class_weights)}

# Compile the model with class weights
model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy', 
                                                                    tf.keras.metrics.Precision(), 
                                                                    tf.keras.metrics.Recall()])

# Train the model with class weights and early stopping
from tensorflow.keras.callbacks import EarlyStopping
early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

history = model.fit(X_train_resampled, y_train_resampled, 
                   epochs=100,  # Increase epochs
                   batch_size=32, 
                   validation_data=(X_test_scaled, y_test),
                   class_weight=class_weight_dict,  # Add class weights
                   callbacks=[early_stopping])  # Add early stopping

# Evaluate the model
# Adjust the threshold for prediction to improve recall for minority class
# Try different thresholds (0.3 instead of 0.5)
y_pred_proba = model.predict(X_test_scaled)
y_pred_A1 = (y_pred_proba > 0.3).astype("int32")  # Lower threshold to catch more positive cases

# Evaluate and print metrics
accuracy = accuracy_score(y_test, y_pred_A1)
print(f'Accuracy: {accuracy * 100:.2f}%')

# Print confusion matrix and classification report
print('Confusion Matrix:')
print(confusion_matrix(y_test, y_pred_A1))

print('\nClassification Report:')
print(classification_report(y_test, y_pred_A1))

# Add precision-recall curve
from sklearn.metrics import precision_recall_curve, auc
import matplotlib.pyplot as plt

precision, recall, thresholds = precision_recall_curve(y_test, y_pred_proba)
pr_auc = auc(recall, precision)
print(f'PR AUC: {pr_auc:.4f}')

plt.figure(figsize=(8, 6))
plt.plot(recall, precision, label=f'PR Curve (AUC = {pr_auc:.4f})')
plt.xlabel('Recall')
plt.ylabel('Precision')
plt.title('Precision-Recall Curve')
plt.legend()
plt.savefig('precision_recall_curve.png')
plt.close()

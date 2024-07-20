import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt

# Load the enhanced dataset
df = pd.read_csv('poly_data/cleaned_merged_data.csv')

# Prepare features and target
features = ['price', 'day_of_week', 'is_weekend', 'hour_of_day', 'momentum_24h', 
            'distance_from_ma', 'days_until_end', 'volatility_24h']
X = df[features]
y = df['price'].shift(-1)  # Predict next hour's price

# Remove last row (NaN in target)
X = X[:-1]
y = y[:-1]

# Split the data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Scale the features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Train the model
model = XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
model.fit(X_train_scaled, y_train)

# Make predictions
y_pred = model.predict(X_test_scaled)

# Evaluate the model
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"Mean Squared Error: {mse}")
print(f"R-squared Score: {r2}")

# Plot feature importance
plt.figure(figsize=(10, 6))
plt.bar(features, model.feature_importances_)
plt.title("Feature Importance")
plt.xlabel("Features")
plt.ylabel("Importance")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('poly_data/feature_importance.png')
print("Feature importance plot saved to poly_data/feature_importance.png")

# Save the model
import joblib
joblib.dump(model, 'poly_data/xgboost_model.joblib')
print("Model saved to poly_data/xgboost_model.joblib")
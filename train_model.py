import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

print("🚀 Starting model training process...")

# ==========================================================
# 1. Load and Prepare Data
# ==========================================================
try:
    # Load the dataset you saved from your dashboard
    df = pd.read_csv('training_data.csv')
except FileNotFoundError:
    print("❌ Error: training_data.csv not found. Please generate it from your Streamlit app first.")
    exit()

# Convert 'date' to datetime and set it as the index
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date')
df.set_index('date', inplace=True)

print(f"✅ Data loaded successfully with {len(df)} rows.")

# ==========================================================
# 2. Feature Engineering
# ==========================================================
# Create time-based features that the model can learn from
df['day_of_year'] = df.index.dayofyear
df['month'] = df.index.month
df['year'] = df.index.year
df['week_of_year'] = df.index.isocalendar().week

# Create lag features (water level from the recent past)
# This is crucial for time-series forecasting
df['lag_7d'] = df['value'].shift(7)
df['lag_30d'] = df['value'].shift(30)

# Drop rows with missing values that were created by the lag features
df.dropna(inplace=True)

print("✅ Feature engineering complete.")

# ==========================================================
# 3. Split Data into Training and Testing Sets
# ==========================================================
# Define our features (X) and the target we want to predict (y)
features = ['day_of_year', 'month', 'year', 'week_of_year', 'lag_7d', 'lag_30d']
target = 'value'

X = df[features]
y = df[target]

# For time series, we split chronologically, not randomly
# We'll use the last 20% of the data for testing
test_size = int(len(df) * 0.2)
X_train, X_test = X[:-test_size], X[-test_size:]
y_train, y_test = y[:-test_size], y[-test_size:]

print(f"✅ Data split into {len(X_train)} training rows and {len(X_test)} testing rows.")

# ==========================================================
# 4. Train the XGBoost Model 🧠
# ==========================================================
print("🏋️‍♂️ Training XGBoost model...")

# Initialize and train the model
model = xgb.XGBRegressor(
    n_estimators=1000,
    learning_rate=0.05,
    objective='reg:squarederror',
    early_stopping_rounds=10,
    eval_metric='mae'
)

model.fit(
    X_train, 
    y_train,
    eval_set=[(X_test, y_test)],
    verbose=False
)

print("✅ Model training complete.")

# ==========================================================
# 5. Evaluate the Model
# ==========================================================
# Make predictions on the unseen test data
predictions = model.predict(X_test)

# Calculate performance metrics
mae = mean_absolute_error(y_test, predictions)
r2 = r2_score(y_test, predictions)

print("\n--- Model Performance ---")
print(f"Mean Absolute Error (MAE): {mae:.3f}")
print(f"R-squared (R²): {r2:.3f}")
print("-------------------------\n")


# ==========================================================
# 6. Save the Trained Model
# ==========================================================
# This saves our "trained brain" to a file for the Streamlit app to use
joblib.dump(model, 'groundwater_model.joblib')

print(f"💾 Model saved successfully as 'groundwater_model.joblib'")
print("🎉 Process finished.")
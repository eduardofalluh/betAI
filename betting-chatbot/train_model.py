import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib

# Load sample dataset (replace with real data)
data = pd.read_csv("historical_betting_data.csv")  # Ensure this file exists

# Prepare features and labels
X = data[["team_offense", "team_defense", "opponent_offense", "opponent_defense"]]
y = data["win"]  # 1 = win, 0 = loss

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = RandomForestClassifier(n_estimators=100)
model.fit(X_train, y_train)

# Save trained model
joblib.dump(model, "betting_model.pkl")
print("✅ Model trained and saved as betting_model.pkl")
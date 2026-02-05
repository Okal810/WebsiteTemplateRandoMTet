"""
S-Bahn Delay Prediction Neural Network
PyTorch model for predicting delays
"""
import torch
import torch.nn as nn
import numpy as np
from pathlib import Path

from database import LINES, STATIONS

MODEL_PATH = Path(__file__).parent / "delay_model.pth"


class DelayPredictor(nn.Module):
    """
    Neural Network zur Vorhersage von S-Bahn Verspätungen
    
    Input Features:
    - weekday: 7 (one-hot)
    - hour: 1 (normalized 0-1)
    - minute: 1 (normalized 0-1)
    - line: len(LINES) (one-hot)
    - station: len(STATIONS) (one-hot)
    
    Total: 7 + 1 + 1 + 2 + 2 = 13 features
    """
    
    def __init__(self):
        super().__init__()
        
        # Feature dimensions
        self.n_weekdays = 7
        self.n_lines = len(LINES)
        self.n_stations = len(STATIONS)
        self.input_size = self.n_weekdays + 2 + self.n_lines + self.n_stations
        
        # Network layers
        self.network = nn.Sequential(
            nn.Linear(self.input_size, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, 1)  # Output: predicted delay in minutes
        )
    
    def forward(self, x):
        return self.network(x)
    
    def encode_features(self, line: str, station: str, weekday: int, 
                        hour: int, minute: int) -> torch.Tensor:
        """
        Encode input features to tensor
        """
        features = []
        
        # Weekday one-hot (7)
        weekday_onehot = [0] * 7
        weekday_onehot[weekday] = 1
        features.extend(weekday_onehot)
        
        # Hour normalized (0-1, for 8-18 range)
        hour_norm = (hour - 8) / 10.0  # 8->0, 18->1
        hour_norm = max(0, min(1, hour_norm))  # Clamp
        features.append(hour_norm)
        
        # Minute normalized (0-1)
        minute_norm = minute / 59.0
        features.append(minute_norm)
        
        # Line one-hot
        line_onehot = [0] * self.n_lines
        if line in LINES:
            line_onehot[LINES.index(line)] = 1
        features.extend(line_onehot)
        
        # Station one-hot
        station_onehot = [0] * self.n_stations
        # Use case-insensitive matching for robustness
        station_upper = station.upper()
        station_list_upper = [s.upper() for s in STATIONS]
        
        if station_upper in station_list_upper:
            station_onehot[station_list_upper.index(station_upper)] = 1
        features.extend(station_onehot)
        
        return torch.tensor(features, dtype=torch.float32)
    
    def predict(self, line: str, station: str, weekday: int, 
                hour: int, minute: int) -> float:
        """
        Predict delay for given parameters
        
        Returns:
            Predicted delay in minutes
        """
        self.eval()
        with torch.no_grad():
            x = self.encode_features(line, station, weekday, hour, minute)
            x = x.unsqueeze(0)  # Add batch dimension
            prediction = self.forward(x)
            return prediction.item()


def load_model() -> DelayPredictor:
    """Load trained model from disk"""
    model = DelayPredictor()
    if MODEL_PATH.exists():
        try:
            model.load_state_dict(torch.load(MODEL_PATH, weights_only=True))
            print(f"Model loaded from {MODEL_PATH}")
        except RuntimeError as e:
            print(f"Warning: Could not load weights (likely dimension mismatch): {e}")
            print("Using fresh model. You should retrain with 'python main.py train'.")
    else:
        print("No trained model found, using untrained model")
    return model


def save_model(model: DelayPredictor):
    """Save model to disk"""
    torch.save(model.state_dict(), MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    # Test model
    model = DelayPredictor()
    print(f"Model input size: {model.input_size}")
    
    # Test encoding
    x = model.encode_features("S4", "Buchenau", 0, 9, 30)
    print(f"Encoded features shape: {x.shape}")
    print(f"Encoded features: {x}")
    
    # Test prediction
    pred = model.predict("S4", "Buchenau", 0, 9, 30)
    print(f"Predicted delay (untrained): {pred:.2f} minutes")

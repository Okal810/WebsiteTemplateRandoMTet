"""
Training Pipeline for S-Bahn Delay Prediction
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np

from database import Database
from model import DelayPredictor, save_model, load_model


class DelayDataset(Dataset):
    """PyTorch Dataset for delay data"""
    
    def __init__(self, data: list, model: DelayPredictor):
        self.data = data
        self.model = model
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        row = self.data[idx]
        x = self.model.encode_features(
            line=row["line"],
            station=row["station"],
            weekday=row["weekday"],
            hour=row["hour"],
            minute=row["minute"]
        )
        y = torch.tensor([row["delay_minutes"]], dtype=torch.float32)
        return x, y


def train_model(epochs: int = 100, batch_size: int = 8, 
                learning_rate: float = 0.01, verbose: bool = True) -> DelayPredictor:
    """
    Train the delay prediction model
    
    Args:
        epochs: Number of training epochs
        batch_size: Batch size for training
        learning_rate: Learning rate
        verbose: Print training progress
    
    Returns:
        Trained model
    """
    # Load data
    db = Database()
    data = db.get_training_data()
    db.close()
    
    if len(data) < 5:
        print(f"Zu wenig Daten zum Training: {len(data)} records")
        print("Mindestens 5 Datenpunkte benötigt.")
        return None
    
    print(f"Training mit {len(data)} Datenpunkten")
    
    # Create model and dataset
    model = DelayPredictor()
    dataset = DelayDataset(data, model)
    
    # Split data (80% train, 20% validation)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    
    if val_size == 0:
        train_set = dataset
        val_set = None
    else:
        train_set, val_set = torch.utils.data.random_split(
            dataset, [train_size, val_size]
        )
    
    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True)
    
    # Training setup
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    # Training loop
    model.train()
    best_loss = float('inf')
    
    for epoch in range(epochs):
        epoch_loss = 0.0
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            predictions = model(batch_x)
            loss = criterion(predictions, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
        
        avg_loss = epoch_loss / len(train_loader)
        
        if avg_loss < best_loss:
            best_loss = avg_loss
        
        if verbose and (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/{epochs}, Loss: {avg_loss:.4f}")
    
    # Validation
    if val_set:
        model.eval()
        val_loader = DataLoader(val_set, batch_size=batch_size)
        val_loss = 0.0
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                predictions = model(batch_x)
                loss = criterion(predictions, batch_y)
                val_loss += loss.item()
        print(f"Validation Loss: {val_loss / len(val_loader):.4f}")
    
    # Save model
    save_model(model)
    
    return model


def evaluate_model():
    """Evaluate the trained model on all data"""
    db = Database()
    data = db.get_training_data()
    db.close()
    
    if not data:
        print("Keine Daten vorhanden")
        return
    
    model = load_model()
    model.eval()
    
    total_error = 0.0
    print("\n=== Vorhersagen vs. Tatsächlich ===")
    
    for row in data[:10]:  # Show first 10
        predicted = model.predict(
            line=row["line"],
            station=row["station"],
            weekday=row["weekday"],
            hour=row["hour"],
            minute=row["minute"]
        )
        actual = row["delay_minutes"]
        error = abs(predicted - actual)
        total_error += error
        
        print(f"{row['line']} {row['hour']:02d}:{row['minute']:02d} @ {row['station']}: "
              f"Predicted={predicted:.1f}min, Actual={actual}min, Error={error:.1f}")
    
    mae = total_error / len(data)
    print(f"\nMean Absolute Error: {mae:.2f} Minuten")


if __name__ == "__main__":
    print("=== Training S-Bahn Delay Model ===")
    model = train_model(epochs=100, verbose=True)
    
    if model:
        print("\n=== Evaluation ===")
        evaluate_model()

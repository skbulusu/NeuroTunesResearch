import os
import pandas as pd
import numpy as np
import joblib
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

# Define the path for saving/loading model components.
# WEIGHTS_PATH lets an operator point the server at an externally-supplied
# weights directory (e.g. weights restored from the private netrai/neurotunes-weights
# repo / a mounted volume). Defaults to the in-repo "models" dir for backward
# compatibility. See MODEL_CARD.md.
MODEL_DIR = os.environ.get("WEIGHTS_PATH") or os.environ.get("MODEL_DIR") or "models"
MODEL_PATH = os.path.join(MODEL_DIR, "emotion_net.pth")
PREPROCESSOR_PATH = os.path.join(MODEL_DIR, "preprocessor.pkl")
COLUMNS_PATH = os.path.join(MODEL_DIR, "columns.pkl")
DATA_PATH = "data/synthetic_patient_data.csv"

# --- The Neural Network Definition ---
class EmotionNet(nn.Module):
    def __init__(self, input_size, output_size=4):
        super(EmotionNet, self).__init__()
        self.layer1 = nn.Linear(input_size, 64)
        self.layer2 = nn.Linear(64, 32)
        self.output_layer = nn.Linear(32, output_size)
        self.relu = nn.ReLU()
        self.tanh = nn.Tanh()

    def forward(self, x):
        x = self.relu(self.layer1(x))
        x = self.relu(self.layer2(x))
        x = self.tanh(self.output_layer(x))
        return x

# --- UPDATED NeuroTunesModel Class ---
class NeuroTunesModel:
    def __init__(self):
        self.model = None
        self.preprocessor = None
        self.columns = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"NeuroTunesModel using device: {self.device}")
        self.load_or_create_model()

    def load_or_create_model(self):
        """Load existing model or create and train a new one"""
        os.makedirs(MODEL_DIR, exist_ok=True)

        # Check if all necessary files exist
        if (os.path.exists(MODEL_PATH) and 
            os.path.exists(PREPROCESSOR_PATH) and 
            os.path.exists(COLUMNS_PATH)):
            try:
                print("Loading existing model and preprocessor from disk.")
                # FIX: Use weights_only=False for PyTorch 2.6 compatibility
                self.model = torch.load(MODEL_PATH, weights_only=False)
                self.model.to(self.device)
                self.model.eval()
                self.preprocessor = joblib.load(PREPROCESSOR_PATH)
                self.columns = joblib.load(COLUMNS_PATH)
                print("Model loaded successfully.")
            except Exception as e:
                print(f"Error loading model: {e}")
                print("Creating new model...")
                self._train_model()
        else:
            print("Model files not found. Training a new model.")
            self._train_model()

    def _train_model(self):
        """
        A private method to train the EmotionNet model from scratch using the synthetic data.
        """
        if not os.path.exists(DATA_PATH):
            print(f"FATAL: Cannot train model. Data file not found at {DATA_PATH}")
            return

        df = pd.read_csv(DATA_PATH)

        # Create target variables from the correct columns
        # Map text moods to a numerical scale for creating a target
        mood_map = {
            'Stressed': 2, 'Anxious': 2, 'Overwhelmed': 1, 'Tired': 3, 'Frustrated': 3,
            'Hopeful': 8, 'Determined': 9, 'Numb': 1, 'Withdrawn': 2, 'Irritable': 3,
            'Sad': 2, 'Focused': 8, 'Neutral': 5, 'Motivated': 9
        }
        df['mood_rating'] = df['mood'].map(mood_map).fillna(5)

        # Create proxy target vector for training
        df['target_arousal'] = (df['energy_levels'] - 5) / 5  # Corrected column name
        df['target_valence'] = (df['mood_rating'] - 5) / 5
        df['target_focus'] = (df['stress_level'] < 4).astype(int) * 2 - 1
        df['target_calm'] = (df['sleep_quality'] > 6).astype(int) * 2 - 1

        # Define features (X) and target (y)
        X = df.drop(['patient_id', 'target_arousal', 'target_valence', 'target_focus', 'target_calm', 'mood_rating'], axis=1)
        y = df[['target_arousal', 'target_valence', 'target_focus', 'target_calm']].values

        # Define correct feature types based on the CSV
        numeric_features = ['age', 'stress_level', 'sleep_quality', 'energy_levels']
        categorical_features = ['gender', 'diagnosis', 'therapy_goal', 'mood']

        # Create the preprocessing pipeline
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), numeric_features),
                ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
            ])

        self.preprocessor = preprocessor.fit(X)
        X_processed = self.preprocessor.transform(X)

        joblib.dump(self.preprocessor, PREPROCESSOR_PATH)
        self.columns = X.columns.tolist()
        joblib.dump(self.columns, COLUMNS_PATH)

        # Initialize and train the PyTorch model
        input_size = X_processed.shape[1]
        self.model = EmotionNet(input_size=input_size, output_size=y.shape[1]).to(self.device)

        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)

        X_tensor = torch.tensor(X_processed.toarray(), dtype=torch.float32).to(self.device)
        y_tensor = torch.tensor(y, dtype=torch.float32).to(self.device)

        print(f"Starting training on {len(X)} samples...")
        for epoch in range(200):
            self.model.train()
            optimizer.zero_grad()
            outputs = self.model(X_tensor)
            loss = criterion(outputs, y_tensor)
            loss.backward()
            optimizer.step()
            if (epoch + 1) % 20 == 0:
                print(f'Epoch [{epoch+1}/200], Loss: {loss.item():.4f}')

        # FIX: Save with explicit weights_only=False for future loading
        torch.save(self.model, MODEL_PATH)
        print(f"New model trained and saved to {MODEL_PATH}")
        self.model.eval()

    def predict(self, processed_data, original_patient_data=None):
        """
        FIXED: Predict emotional/functional state from patient data
        Now properly uses the sklearn preprocessor instead of the custom data_processor output
        """
        try:
            # IGNORE the processed_data from data_processor.py - it doesn't match our model
            # Instead, use the original_patient_data and preprocess it properly

            if original_patient_data is None:
                print("Warning: No original_patient_data provided, using default values")
                original_patient_data = {
                    'age': 45, 'gender': 'Male', 'diagnosis': 'Post-Stroke', 
                    'therapy_goal': 'Gait & Motor Priming', 'stress_level': 5,
                    'sleep_quality': 5, 'energy_levels': 5, 'mood': 'Neutral'
                }

            print(f"Processing patient data: {original_patient_data}")

            # Create DataFrame in the same format as training data
            df = pd.DataFrame([original_patient_data])

            # Ensure we have all the expected columns that the model was trained on
            expected_cols = ['age', 'gender', 'diagnosis', 'therapy_goal', 'stress_level', 'sleep_quality', 'energy_levels', 'mood']
            for col in expected_cols:
                if col not in df.columns:
                    if col in ['gender', 'diagnosis', 'therapy_goal', 'mood']:
                        df[col] = 'Unknown'
                    else:
                        df[col] = 5

            # Apply the same preprocessing pipeline as during training
            processed_array = self.preprocessor.transform(df)
            processed_tensor = torch.FloatTensor(processed_array.toarray()).to(self.device)

            print(f"Preprocessed tensor shape: {processed_tensor.shape}")

            # Use the model to predict emotional state
            with torch.no_grad():
                emotion_output = self.model(processed_tensor)
                # The model outputs 4 values: [arousal, valence, focus, calm]
                # This is regression, not classification, so no softmax needed
                state_vector = emotion_output.squeeze().cpu().numpy()

                print(f"Predicted state vector: {state_vector}")
                return state_vector

        except Exception as e:
            print(f"Error in predict method: {e}")
            print(f"Input data: {original_patient_data}")
            import traceback
            traceback.print_exc()
            # Return a default state vector if prediction fails
            return np.array([0.0, 0.0, 0.0, 0.0])

    def map_to_clinical_params(self, state_vector, therapy_goal):
        """
        Maps the predicted state vector to musical parameters based on the
        clinical therapy goal, using evidence-based principles.
        """
        arousal, valence, focus, calm = state_vector

        params = {
            'key': 'C', 'mode': 'major', 'tempo': 80, 'complexity': 0.5,
            'instrument': 'Acoustic Grand Piano', 'rhythm_stability': 0.8,
            'dynamic_range': 0.6
        }

        if therapy_goal == 'Gait & Motor Priming':
            # Goal: Strong, stable, predictable rhythm to entrain movement
            params['tempo'] = np.interp(arousal, [-1, 1], [80, 125])
            params['mode'] = 'major' if valence > 0 else 'minor'
            params['complexity'] = 0.2
            params['rhythm_stability'] = 0.95
            params['dynamic_range'] = 0.4

        elif therapy_goal == 'Cognitive Enhancement':
            # Goal: Increase focus and mental stimulation without being distracting
            params['tempo'] = np.interp(calm, [-1, 1], [80, 60])
            params['mode'] = 'major'
            params['complexity'] = np.interp(focus, [-1, 1], [0.4, 0.8])
            params['instrument'] = 'Electric Piano 1'
            params['rhythm_stability'] = np.interp(calm, [-1, 1], [0.6, 0.9])

        elif therapy_goal == 'Apathy & Mood Regulation':
            # Goal: Elevate mood and energy
            params['tempo'] = np.interp(arousal, [-1, 1], [70, 110])
            params['mode'] = 'major'
            params['key'] = 'G' if valence > 0.5 else 'C'
            params['complexity'] = np.interp(arousal, [-1, 1], [0.3, 0.7])
            params['dynamic_range'] = np.interp(valence, [-1, 1], [0.5, 0.9])

        elif therapy_goal == 'Speech & Auditory Cueing':
            # Goal: Clear, simple melodic contours and rhythms to cue speech patterns
            params['tempo'] = np.interp(calm, [-1, 1], [75, 60])
            params['mode'] = 'major'
            params['complexity'] = 0.1
            params['instrument'] = 'Vibraphone'
            params['rhythm_stability'] = 0.9
            params['dynamic_range'] = 0.3

        # Ensure all params are standard python types for JSON serialization
        for key, value in params.items():
            if isinstance(value, np.generic):
                params[key] = value.item()

        return params

    # Legacy method for backward compatibility
    def map_to_music_params(self, state_vector, therapy_goal):
        """Legacy method - redirects to map_to_clinical_params for backward compatibility"""
        return self.map_to_clinical_params(state_vector, therapy_goal)

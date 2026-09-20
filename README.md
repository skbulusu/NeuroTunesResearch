
# NeuroTunes

**An open-source platform for reproducible, pre-clinical music-therapy ML research.**

NeuroTunes explores how machine learning can be used to generate individualized therapeutic music while keeping the underlying models, evaluation, and safety constraints inspectable.

**Sai Karthik Bulusu**  
Mission Early College High School & Mission College  
Santa Clara, California

[Website](https://www.netr.ai) · [Demo](https://www.youtube.com/watch?v=Rqx6QJ0Lidc) · [Email](mailto:skbulusu@gmail.com)

---

## Overview

Personalized music therapy brings together machine learning, neuroscience, and music cognition. Developing these systems involves challenges such as limited patient-response data, expensive expert annotation, and the difficulty of evaluating models before clinical studies.

NeuroTunes focuses on the **pre-clinical research stage**, providing an environment for developing, testing, and evaluating individualized music-generation systems.

The project uses synthetic data and computational evaluation to explore these ideas. It does not claim to demonstrate clinical efficacy or replace professional therapy.

## How It Works

NeuroTunes generates music from an individual's target affective profile rather than selecting tracks from an existing music library.

The pipeline follows a logged workflow:

```text
Assessment
    ↓
EmotionNet
    ↓
MusicGenerator
    ↓
Safety Validator
    ↓
Generated Audio + Session Log
```

### Components

#### EmotionNet

Maps an individual's profile to target dimensions such as:

- Arousal
- Valence
- Focus
- Calm

#### MusicGenerator

Converts the target affective profile into MIDI and audio using a deterministic, parametric renderer.

The renderer provides explicit control over musical parameters, including tempo, musical mode, and binaural frequency.

Unlike learned generative audio models, the renderer is designed to make its behavior inspectable and reproducible.

#### Safety Validator

Applies hard constraints to generated music, including:

- Tempo
- Binaural frequency
- Duration

These constraints are intended to limit the range of generated outputs. They do not establish clinical safety.

#### RewardNet

Uses logged feedback to train a reward model that supports experimentation with feedback-driven personalization.

#### Retraining Scheduler

Uses a champion/challenger evaluation process to compare updated models against the current model.

A new model is promoted only when it meets the defined evaluation criteria. Otherwise, the existing model is retained.

## Research Infrastructure

NeuroTunes includes infrastructure for reproducible experimentation:

- Synthetic longitudinal patient cohort
- LLM-assisted soft affect annotation
- Confidence-based review gating
- Deterministic, parametric audio generation
- Logged sessions and evaluation
- Multi-seed retraining
- Model weight verification
- Research API with consent gating
- Simulated federated learning and differential privacy components

All results are based on synthetic or practice data. The platform is intended for research and education, not clinical deployment.

## License

NeuroTunes is licensed under the **Apache-2.0 License**.

See [LICENSE](LICENSE) for details.

## Contact

**Sai Karthik Bulusu**

- Email: [skbulusu@gmail.com](mailto:skbulusu@gmail.com)
- Website: [www.netr.ai](https://www.netr.ai)
- Demo: [YouTube](https://www.youtube.com/watch?v=Rqx6QJ0Lidc)
- GitHub: [NeuroTunesDemoTrack](https://github.com/YOUR_USERNAME/NeuroTunesDemoTrack)

Feedback, research suggestions, and collaboration inquiries are welcome.

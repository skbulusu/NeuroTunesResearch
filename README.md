
# NeuroTunes

**An open-source platform for reproducible, pre-clinical music-therapy ML research.**

NeuroTunes explores how machine learning can be used to generate individualized therapeutic music while keeping the underlying models, evaluation, and safety constraints inspectable.

**Sai Karthik Bulusu**  
Mission Early College High School & Mission College  
Santa Clara, California

[Website](https://www.netr.ai) · [Demo](https://www.youtube.com/watch?v=Rqx6QJ0Lidc) · [Email](mailto:skbulusu@gmail.com)

Licensed under the Apache-2.0 License.

---

## Overview

Personalized music therapy sits at the intersection of music cognition, neuroscience, and machine learning. However, developing and evaluating these systems presents several challenges:

- **Limited data:** Patient-response data is difficult to collect, especially across different conditions and over long periods.
- **Expensive annotation:** Expert affect labeling requires time from trained professionals.
- **Unclear evaluation:** A model can reproduce its own training labels without producing clinically meaningful results.

NeuroTunes focuses on the **pre-clinical research stage**. It provides a controlled environment for developing, testing, and evaluating music-generation models before any human study or clinical deployment.

The project does not claim to demonstrate clinical efficacy.

## What It Does

NeuroTunes generates music from an individual's target affective profile rather than selecting tracks from an existing music library.

The pipeline follows a single, logged workflow:

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

### Main components

- **EmotionNet:** Maps a profile to target dimensions such as arousal, valence, focus, and calm.
- **MusicGenerator:** Converts the target into MIDI and audio using a deterministic, parametric renderer.
- **Safety Validator:** Applies hard limits to tempo, binaural frequency, and duration.
- **RewardNet:** Learns from simulated session feedback.
- **Retraining Scheduler:** Uses champion/challenger evaluation to determine whether a new model should replace the current one.

The audio renderer is not a learned generative audio model. It uses explicit parameters and deterministic rendering to make its behavior easier to inspect and reproduce.

## Research Highlights

### Synthetic longitudinal cohort

- 291,331 rows
- 26,094 simulated patients
- 14 neurological and psychiatric conditions
- Longitudinal patient trajectories

The cohort uses documented realism axes, including medication adherence, chronotype, comorbidity, and response archetypes. These are intended to produce structured variation rather than independent random samples.

The cohort is synthetic and does not represent real patient outcomes.

### LLM-based annotation

An open-weight Qwen2.5-7B model produces soft affect targets at scale.

NeuroTunes uses an ensemble and uncertainty model to identify labels that may require human review. Approximately 42–44% of labels are flagged by the confidence gate.

The LLM is treated as a scalable prior, not as clinical ground truth.

### EmotionNet

The compact EmotionNet model has approximately 8,000 parameters.

It reconstructs the ensemble targets with an R² of 0.938 on the reported evaluation.

This measures self-consistency with the generated labels. It does not establish clinical validity.

### Independent audio evaluation

An independent MERT-based audio critic identified an affect-inversion bug in the renderer:

| Metric | Before fix | After fix |
|---|---:|---:|
| Arousal correlation | -0.43 | +0.50 |
| Valence correlation | Not reported | +0.46 |

The results demonstrate why evaluating a system only against its own labels can miss important failures.

The reported correlations are research evaluation results, not clinical validation.

## How It Extends Existing Research

NeuroTunes brings together ideas from several areas of research:

| Existing research | Limitation | NeuroTunes approach |
|---|---|---|
| Music-emotion datasets | Usually annotate music rather than patient trajectories | Synthetic patient × session data across 14 conditions |
| Generative audio models | Can be difficult to inspect and reproduce | Deterministic renderer with explicit parameters |
| LLM-based annotation | LLM outputs can be mistaken for ground truth | Soft priors, ensemble targets, and confidence gating |
| Self-consistency evaluation | Can miss directional failures | Independent audio critic and adversarial evaluation |

The goal is not to replace existing research, but to provide a testbed for studying the connections between these approaches.

## Running

> Instructions will be expanded as the repository is finalized.

### Requirements

- Python 3.10+
- PyTorch
- NumPy
- Pandas
- Audio and MIDI dependencies listed in `requirements.txt`

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/NeuroTunesDemoTrack.git
cd NeuroTunesDemoTrack

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### Run the pipeline

```bash
python main.py
```

The exact entry points and configuration options may change as development continues. Refer to the repository's implementation and configuration files for the current workflow.

## Reproducibility

NeuroTunes is designed around reproducible experimentation.

Planned and implemented infrastructure includes:

- Deterministic, multi-seed retraining
- Model weight verification
- Logged training and evaluation runs
- Champion/challenger model comparison
- Configurable safety constraints
- A consent-gated `/api/v1` research interface
- Simulated federated learning and differential privacy components

Some components are experimental and should not be interpreted as production-ready clinical infrastructure.

## Evaluation and Limitations

NeuroTunes is built around a simple principle: **a model should not be considered successful merely because it agrees with its own labels.**

The project reports both positive and negative results, including bugs discovered during independent evaluation.

Current limitations include:

- The patient cohort is synthetic.
- LLM-generated labels are not clinical ground truth.
- Self-consistency metrics do not establish therapeutic benefit.
- Audio correlations do not establish clinical efficacy.
- The safety validator does not guarantee clinical safety.
- Federated learning and privacy components are simulated where applicable.

Clinical research, human studies, and IRB-approved evaluation are future work.

## Potential Research Applications

NeuroTunes may be useful as an experimental platform for researchers working in:

- Music cognition
- Rhythmic entrainment
- Affective computing
- Machine learning for mental health
- Reinforcement learning from human feedback
- Personalized audio generation

The platform provides explicit control over parameters such as tempo, musical mode, and binaural frequency, along with session logging for reproducible experiments.

It is intended to support research, not replace therapists or provide medical treatment.

## Project Status

NeuroTunes is an ongoing research and education project.

The system is being developed to make the pre-clinical modeling process more transparent, reproducible, and easier to evaluate. Features and evaluation protocols may change as the project develops.

## License

This project is licensed under the **Apache-2.0 License**.

See [LICENSE](LICENSE) for details.

## Contact

**Sai Karthik Bulusu**

- Email: skbulusu@gmail.com
- Website: https://www.netr.ai
- Demo: https://www.youtube.com/watch?v=Rqx6QJ0Lidc

Feedback, research suggestions, and collaboration inquiries are welcome.

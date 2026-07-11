# SafetyOps Copilot NLP Model (DistilBERT)

## Overview

This directory holds the fine-tuned DistilBERT model used for incident
**severity classification** from short free-text incident descriptions.

- Base model: `distilbert-base-uncased`
- Task: single-label classification
- Target: `severity` ∈ {`low`, `medium`, `high`}
- Max sequence length: 128 tokens

Category classification (e.g. `fall`, `electrical`, `fire`, `chemical`) is
implemented with a lightweight rule-based classifier and is **not** learned by
this model.

## Training data

**MSHA accident narratives** (real data): the U.S. Mine Safety and Health
Administration publishes all mine operator/contractor accident reports since
2000 (~273k records with usable narratives), including a free-text `NARRATIVE`
and a `DEGREE_INJURY` outcome code.
Source: <https://arlweb.msha.gov/OpenGovernmentData/OGIMSHA.asp>

Severity labels are derived from the reported outcome (`DEGREE_INJURY_CD`):

| Label  | Outcome codes                                                  |
|--------|----------------------------------------------------------------|
| high   | 01 fatality, 02 permanent total/partial disability              |
| medium | 03 days away from work, 04 days away + restricted, 05 restricted activity |
| low    | 00 accident only (no injury), 06 no lost days/restrictions, 10 other incl. first aid |

Ambiguous codes (07 occupational illness, 08 natural causes, 09 non-employees)
are excluded. Narratives are deduplicated and filtered to ≥ 30 characters.

The dataset is **balance-sampled** to the smallest class:

- Training pool: 9,105 rows (3,035 per class) — `data/text/incidents_msha.csv`
- Held-out test set: 1,605 rows (535 per class) — `data/text/incidents_msha_test.csv`

Rebuild with:

```bash
python scripts/download_msha_dataset.py
```

## Results (held-out test set, 1,605 samples)

Trained 2 epochs, batch size 16, lr 5e-5, seed 42 (CPU, ~1h).

| Model                | Accuracy | Macro-F1 | High-severity F1 | High-severity recall |
|----------------------|----------|----------|------------------|----------------------|
| Rule-based baseline  | 0.40     | 0.34     | 0.27             | 0.16                 |
| **DistilBERT (this)**| **0.78** | **0.78** | **0.84**         | **0.88**             |

DistilBERT confusion matrix (rows = true, cols = predicted; order low/medium/high):

```
   low: [389, 110,  36]
medium: [ 69, 395,  71]
  high: [ 21,  45, 469]
```

Full per-class metrics: `models/nlp/eval_results.json`. Reproduce with:

```bash
python -m safetyops.ml.nlp.evaluate
```

## Training

```bash
python -m safetyops.ml.nlp.train  # defaults to data/text/incidents_msha.csv
```

- Splits the training pool 80/20 into train/validation.
- Fine-tunes with the Hugging Face `Trainer`, selecting the best epoch by
  validation macro-F1.
- Logs params/metrics/artifacts to MLflow
  (`SAFETYOPS_MLFLOW_TRACKING_URI`, defaults to `sqlite:///mlflow.db`).
- Saves the best model to this directory; the runtime
  (`safetyops.ml.nlp.infer.predict_severity`) picks it up automatically and
  falls back to the rule-based classifier when the model or its dependencies
  are absent.

Model weights are **not** committed to the repository.

## Limitations

- Trained on **mining-industry** narratives; transfer to other industries
  (construction, labs, warehouses) is plausible but unvalidated.
- Labels are derived from administrative outcome codes, which proxy severity
  imperfectly (e.g. a near-miss with catastrophic potential is "low").
- English-only; narratives are terse report-style prose, so conversational
  input may be out-of-distribution.
- The model predicts severity of the *reported outcome*, not risk of
  recurrence.

## Responsible use

Treat predictions as **advisory triage signals**. High-severity recall (0.88)
was prioritized in evaluation, but real deployments must keep a human in the
loop for incident classification and regulatory reporting.

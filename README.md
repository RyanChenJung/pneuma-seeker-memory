![The Architecture of Pneuma-Seeker](etc/pneuma_seeker.png)

# Pneuma-Seeker

A system that helps users identify and fulfill their latent information needs.

## Installation

```bash
conda create --name processor python=3.12
pip install -r requirements.txt
fastapi dev src/processor/processor.py
```

<!-- ## Test (NOTE: outdated tests; will be updated)

```bash
cd ./tests/processor
python -m coverage run -m unittest discover
python -m coverage html
``` -->

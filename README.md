![The Architecture of Pneuma-Seeker](pneuma_seeker.png)

# Pneuma-Seeker

[![arXiv](https://img.shields.io/badge/arXiv-2603.10747-b31b1b?logo=arxiv)](https://arxiv.org/abs/2603.10747)

**Pneuma-Seeker** is a system that reifies an *active information need* over tabular data as a relational data model $(\mathcal{T}, S)$, where:

- $\mathcal{T}$ is a set of views derived from the underlying dataset (table collection)
- $S$ is a Python script defined over $\mathcal{T}$

This system, which we first introduced as part of our vision for [the Pneuma project](https://www.cidrdb.org/cidr2026/papers/p31-balaka.pdf), fulfills information needs by executing $S$ over $\mathcal{T}$.

---

# How to Run the System

First, prepare the environment:

```bash
conda create --name pneuma_seeker python=3.12.9
pip install -r requirements.txt
```

You may modify configuration values through the `.env` file. Refer to `src/pneuma_seeker/shared/config.py` for all available configuration options.

Then, run the backend:

```bash
cd src/pneuma_seeker
nohup fastapi dev main.py --host 0.0.0.0 --port 8000 >> main.out &
```

## MacOS Note

On MacOS, FastAPI does not work well with nohup. Use the following instead:

```bash
fastapi dev main.py > main.out 2>&1
```

## Running the Frontend

Clone the UI repository and run OpenWebUI:

```bash
cd ..
git clone https://github.com/luthfibalaka/pneuma-seeker-ui.git
cd pneuma-seeker-ui
git checkout stable-0.6.22
pip install .
nohup open-webui serve >> output.out &
```

After launching the frontend, import all functions in `openwebui_functions` into the OpenWebUI interface so the frontend can call the Pneuma-Seeker backend.


# Running Unit Tests

```bash
cd ./tests/pneuma_seeker
python -m unittest discover
```

# Code Structure

```
pneuma_seeker/
├── data_src/                 # Datasets used in experiments
├── baselines/                # Baselines used in experiments
├── openwebui_functions/      # OpenWebUI functions that call the Pneuma-Seeker backend
│
├── src/pneuma_seeker/
│   ├── provenance/           # ProvenanceGraph implementation
│   │
│   ├── services/
│   │   ├── core/             # Core system components (Conductor, Materializer, Retriever)
│   │   ├── db/               # DBService: interface to datasets and workspace databases
│   │   └── language_model/   # LMService: interface to LLMs and embedding models
│   │
│   ├── shared/               # Shared schemas, utilities, and common functionality
│   ├── templates/            # (T,S) HTML templates used by the frontend
│   │
│   ├── chat_session.py       # Chat session instantiated for each (user, chat) pair
│   ├── session_manager.py    # Manages chat sessions for main.py
│   └── main.py               # FastAPI endpoints (backend entry points)
│
├── tests/                    # Unit tests
├── .env                      # Sample environment configuration
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

# Citation

If you would like to cite the paper on `Pneuma-Seeker`, please use the following BibTeX entry:
```
@misc{PneumaSeeker2026,
      title={Pneuma-Seeker: A Relational Reification Mechanism to Align AI Agents with Human Work over Relational Data}, 
      author={Muhammad Imam Luthfi Balaka and John Hillesland and Kemal Badur and Raul Castro Fernandez},
      year={2026},
      eprint={2603.10747},
      archivePrefix={arXiv},
      primaryClass={cs.DB},
      url={https://arxiv.org/abs/2603.10747}, 
}

```
If you would like to cite the paper on the Pneuma project, please use the following BibTex entry:
```
@inproceedings{PneumaProjectCIDR2026,
  author    = {Muhammad Imam Luthfi Balaka and Raul Castro Fernandez},
  title     = {The Pneuma Project: Reifying Information Needs as Relational Schemas to Automate Discovery, Guide Preparation, and Align Data with Intent},
  booktitle = {Proceedings of the 16th Annual Conference on Innovative Data Systems Research (CIDR '26)},
  year      = {2026},
}
```

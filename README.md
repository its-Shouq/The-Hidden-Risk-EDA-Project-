# THE HIDDEN RISK ✈️
### Not Every Strike Is Equal

**An exploratory data analysis and interactive aviation safety dashboard built using FAA wildlife strike reports (2020–2025).**

🔗 **[Explore the Live Dashboard](https://the-hidden-risk.streamlit.app/)** | 📓 **[View the Jupyter Notebook](FAA_Dataset_Notebook.ipynb)**

## Project Overview

Wildlife strikes are a recurring challenge in aviation safety, but **a frequently reported species is not necessarily the species associated with the highest recorded damage rate**.

This project explores an important question:

> How do wildlife species, animal size, flight phase, and the number of animals involved relate to reported aircraft damage?

## Dataset

- **Source:** [Federal Aviation Administration (FAA) — Wildlife Strike Database](https://www.faa.gov/airports/airport_safety/wildlife)
- **Period:** 2020–2025
- **Cleaned records:** 110,940 reported wildlife strikes
- **Damaging reports:** 4,314 (3.89%)
- **Cleaned dataset:** `FAA_Cleaned.csv`

## Project Structure

| File | Description |
|---|---|
| `FAA_Dataset_Notebook.ipynb` | Data exploration, cleaning, EDA, and insights |
| `FAA_Cleaned.csv` | Cleaned dataset |
| `app.py` | Main Streamlit dashboard |
| `lab.py` | Simulation data preparation and scenario logic |
| `simulator.html` | Interactive wildlife-strike simulation |
| `style.css` | Dashboard styling |
| `requirements.txt` | Required Python packages |

## Key Findings

| Category | Recorded Damage Rate |
|---|---:|
| Overall | 3.89% |
| Small animals | 1.49% |
| Large animals | 24.36% |
| Mourning dove | 1.30% |
| White-tailed deer | 73.76% |
| Single-animal strikes | 3.58% |
| Multiple-animal strikes | 7.20% |

**Main Insight:** Strike frequency alone does not explain aircraft damage. Wildlife characteristics and incident circumstances reveal important differences in recorded damage rates.

## Interactive Dashboard

The Streamlit dashboard allows users to:

- Filter records by year, animal size, and flight phase.
- Explore summary statistics and damage-rate trends.
- Compare wildlife species by frequency and recorded damage rate.
- Analyze patterns across animal sizes and strike groups.
- Select Explore an animated wildlife-strike simulation scenarios through an interactive damage-rate heatmap.
- Key findings

## Technologies Used

**Python · Pandas · Streamlit · Plotly · JS/CSS/HTML · Jupyter Notebook**


## Limitations

- The analysis is based on reported wildlife strikes, not all flights.
- Approximately 45% of reports had no recorded flight phase, and 20% had no recorded animal size.
- Species damage rankings included only wildlife categories with at least 100 reports.
- The findings show associations, not causation.

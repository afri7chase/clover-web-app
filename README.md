# Clover Web App

## Windows

Double-click `run_clover.bat`.

The launcher:

- opens from the project directory
- creates `.venv` if it does not exist
- activates the virtual environment
- installs packages from `requirements.txt` only when needed
- starts the Clover Streamlit app

## Manual Setup

1. Create and activate a Python virtual environment.
2. Install the project dependencies:

```powershell
pip install -r requirements.txt
```

3. Start the Streamlit entry point:

```powershell
streamlit run app.py
```

`reportlab` is included in `requirements.txt`, so PDF report generation does not require a separate manual install step.

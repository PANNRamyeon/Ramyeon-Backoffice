# Common Commands - PANN Back Office

## Backend Commands

### Create Virtual Environment (First Time Only)
cd backend
python -m venv .venv

### Activate Virtual Environment
cd backend
.venv\Scripts\Activate.ps1

### Install Requirements
cd backend
pip install -r requirements.txt

### Initialize DynamoDB Counters
cd backend
python init_counters.py

### Run Django Server
cd backend
python manage.py runserver


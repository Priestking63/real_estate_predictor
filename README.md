# 🏠 Real Estate Price Predictor

ML-приложение для предсказания стоимости недвижимости.

## 🚀 Быстрый стартy

### Вариант 1: Docker Compose (рекомендуется)
```bash
# Клонируйте репозиторий
git clone https://github.com/priestking63/real-estate-predictor.git
cd real-estate-predictor

# Запустите приложение
docker-compose up -d

# Откройте в браузере
# Frontend: http://localhost:8501
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs

### Вариант 2: Ручной запуск
#Backend
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Frontend (в другом терминале)
cd frontend
pip install -r requirements.txt
streamlit run streamlit_app.py
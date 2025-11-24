import os
import streamlit as st
import requests
import pandas as pd


BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')


# Настройки страницы
st.set_page_config(
    page_title="Real Estate Price Predictor",
    page_icon="🏠",
    layout="wide"
)

# Заголовок
st.title("🏠 Real Estate Price Predictor")
st.markdown("Предсказание стоимости недвижимости на основе параметров")

CITY_MAPPING = {
    'Москва': 'Москва',
    'Санкт-Петербург': 'Питер', 
    'Казань': 'Казань',
    'Нижний Новгород': 'Нижний',
    'Новосибирск': 'Новосиб',
    'Екатеринбург': 'ЕКБ'
}

col1, col2 = st.columns(2)

with col1:
    st.header("Основные параметры")
    
    # Числовые параметры
    total_area = st.number_input("Общая площадь (м²)", min_value=10.0, max_value=500.0, value=65.0, step=0.5)
    kitchen_area = st.number_input("Площадь кухни (м²)", min_value=5.0, max_value=100.0, value=12.0, step=0.5)
    floor = st.number_input("Этаж", min_value=1, max_value=50, value=5)
    floors_total = st.number_input("Всего этажей в доме", min_value=1, max_value=50, value=9)
    build_year = st.number_input("Год постройки", min_value=1900, max_value=2026, value=2008)

with col2:
    st.header("Категориальные параметры")
    
    # Выпадающие меню для категориальных признаков
    rooms = st.selectbox("Количество комнат", options=["студия", "1", "2", "3", "4", "5+"])
    
    renovation = st.selectbox(
        "Ремонт", 
        options=['дизайнерский', 'евро', 'требует ремонта', 'косметический']
    )
    
    house_type = st.selectbox(
        "Тип дома", 
        options=['монолитный', 'панельный', 'кирпичный', 'монолитно-кирпичный', 'блочный', 'деревянный']
    )
    
    # Город с полными названиями
    city_full = st.selectbox(
        "Город", 
        options=list(CITY_MAPPING.keys())
    )
    
    passenger_lift = st.selectbox("Пассажирский лифт", options=["1", "2", "3", "нет"])
    cargo_lift = st.selectbox("Грузовой лифт", options=["1", "0", "нет"])
    
    parking = st.selectbox(
        "Парковка", 
        options=['подземная', 'открытая во дворе', 'наземная многоуровневая', 'за шлагбаумом во дворе']
    )

# Кнопка для предсказания
if st.button("🎯 Предсказать стоимость", type="primary"):
    city_api = CITY_MAPPING[city_full]
    
    input_data = {
        "total_area": total_area,
        "kitchen_area": kitchen_area,
        "floor": floor,
        "total_floor": floors_total,
        "rooms": rooms,
        "renovation": renovation,
        "house_type": house_type,
        "city": city_api,  
        "passenger_lift": passenger_lift,
        "cargo_lift": cargo_lift,
        "parking": parking,
        "build_year": build_year
    }
    
    try:
        response = requests.post(
           f"{BACKEND_URL}/predict",
            json=input_data
        )
        
        if response.status_code == 200:
            result = response.json()
            predicted_price = result['predicted_price']
            
            # Красиво отображаем результат
            st.success("✅ Предсказание выполнено успешно!")
            
            # Красивый вывод цены
            st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 2rem;
                border-radius: 15px;
                text-align: center;
                color: white;
                margin: 1rem 0;
            '>
                <h2 style='margin: 0; font-size: 2.5rem;'>💰 {predicted_price:,.0f} ₽</h2>
                <p style='margin: 0.5rem 0 0 0; opacity: 0.9;'>Предсказанная стоимость в {city_full}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Вывод похожих объектов
            if 'similar_listings' in result and result['similar_listings']:
                st.header("🏘️ Похожие объекты")
                
                similar_cols = st.columns(3)
                
                for idx, similar in enumerate(result['similar_listings']):
                    with similar_cols[idx]:
                        st.markdown(f"""
                        <div style='
                            border: 1px solid #ddd;
                            border-radius: 10px;
                            padding: 1rem;
                            margin: 0.5rem 0;
                            background-color: #f9f9f9;
                        '>
                            <h4 style='margin-top: 0;'>Объект {idx + 1}</h4>
                            <p><strong>💰 Цена:</strong> {similar['price']:,.0f} ₽</p>
                            <p><strong>🚪 Комнат:</strong> {similar['rooms']}</p>
                            <p><strong>📐 Площадь:</strong> {similar['total_area']} м²</p>
                            <p><a href="{similar['link']}" target="_blank">🔗 Ссылка на объявление</a></p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("ℹ️ Похожие объекты не найдены")
            
            with st.expander("📊 Детали запроса"):
                st.write("**Параметры недвижимости:**")
                st.json({
                    "Город": city_full,
                    "Общая площадь": f"{total_area} м²",
                    "Площадь кухни": f"{kitchen_area} м²", 
                    "Этаж": f"{floor} из {floors_total}",
                    "Комнаты": rooms,
                    "Ремонт": renovation,
                    "Тип дома": house_type,
                    "Год постройки": build_year,
                    "Парковка": parking
                })
                st.write("**Полный ответ API:**")
                st.json(result)
                
        else:
            st.error(f"❌ Ошибка API: {response.status_code} - {response.text}")
            
    except requests.exceptions.ConnectionError:
        st.error("🚫 Не удалось подключиться к API. Убедитесь, что сервер запущен на localhost:8000")
    except Exception as e:
        st.error(f"❌ Произошла ошибка: {str(e)}")

with st.sidebar:
    st.header("ℹ️ Информация")
    st.markdown("""
    ### Как использовать:
    1. Заполните все параметры недвижимости
    2. Нажмите кнопку "Предсказать стоимость"
    3. Получите предсказанную цену и похожие объекты
    
    ### Доступные города:
    - **Москва**
    - **Санкт-Петербург** 
    - **Казань**
    - **Нижний Новгород**
    - **Новосибирск**
    - **Екатеринбург**
    
    ### Примечание:
    Убедитесь, что API сервер запущен на порту 8000
    """)
    
    st.header("🔗 Статус подключения")
    try:
        health_response = requests.get(f"{BACKEND_URL}/predict", timeout=5)
        if health_response.status_code == 200:
            st.success("✅ API доступен")
            health_data = health_response.json()
            st.metric("Модель загружена", "Да" if health_data.get('model_loaded') else "Нет")
        else:
            st.error("❌ API недоступен")
    except:
        st.error("❌ Не удалось подключиться к API")

st.markdown("---")
st.markdown("Real Estate Price Predictor • Powered by ML")
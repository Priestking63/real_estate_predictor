import pandas as pd
import numpy as np
import gower
from fastapi import FastAPI, HTTPException
import joblib
from real_estate_predictor.backend.schema import PropertyInput, PredictionResponse,SimilarListing


app = FastAPI(title="Real Estate Price Predictor", version="1.0.0")

def load_models():
    try:
        model = joblib.load('best_real_estate_model.pkl')
        print("Model loaded successfully")
    except Exception as e:
        print(f"Error loading model: {e}")
        model = None

    return model

model = load_models()

def smart_floor_feature(floor, total_floors):
    
    if total_floors == 1:
        return 0.5
    relative = (floor - 1) / (total_floors - 1)
    
    if total_floors <= 5: 
        if floor == 1:
            return relative * 0.7 
        elif floor == total_floors:
            return relative * 1.1  
        else:
            return relative
            
    else:  # высотки
        if floor == 1:
            return relative * 0.6  
        elif floor == total_floors:
            return relative * 1.4  
        elif floor >= total_floors - 2:
            return relative * 1.2 
        else:
            return relative

def create_city_specific_features(df):
    """Создает признаки учитывающие специфику городов"""
    df = df.copy()
    
    # Питерские исторические дома (особый случай)
    df['is_spb_historical'] = ((df['city'] == 'Питер') & 
                              (df['house_age'] > 130) & 
                              (df['house_type'])).astype(int)
    
    df['is_prestigious_historical'] = ((df['house_age'] > 100) & 
                                      (df['city'].isin(['Питер', 'Москва'])) & 
                                      (df['house_type'])).astype(int)
    
    
    return df


def create_city_aware_age_features(df):
    """Создает возрастные признаки с учетом специфики городов"""
    df = df.copy()
    
    df['house_age'] = 2026 - df['build_year']
    
    def get_city_specific_age_group(city, age):
        if city == 'Питер':
            if age <= 5: return 'спб_новостройка'
            elif age <= 30: return 'спб_современная'
            elif age <= 60: return 'спб_советская'
            elif age <= 100: return 'спб_дореволюционная'
            else: return 'спб_историческая'
        elif city == 'Москва':
            if age <= 5: return 'мск_новостройка'
            elif age <= 30: return 'мск_современная'
            elif age <= 60: return 'мск_советская'
            elif age <= 100: return 'мск_старая'
            else: return 'мск_историческая'
        else:  # Другие города
            if age <= 5: return 'др_новостройка'
            elif age <= 30: return 'др_современная'
            elif age <= 60: return 'др_советская'
            else: return 'др_старая'
    
    df['city_specific_age_group'] = df.apply(
        lambda x: get_city_specific_age_group(x['city'], x['house_age']), axis=1
    )
    
    df['age_city_premium'] = df.apply(calculate_age_city_premium, axis=1)
    
    return df

def calculate_age_city_premium(row):
    """Рассчитывает премию за возраст в зависимости от города"""
    city = row['city']
    age = row['house_age']
    
    if city == 'Питер':
        if age > 100: return 1.4  
        elif age > 80: return 1.2
        elif age <= 5: return 1.1
        else: return 1.0
    elif city == 'Москва':
        if age <= 5: return 1.3 
        elif age > 100: return 1.1
        else: return 1.0
    else:  # Другие города
        if age <= 5: return 1.1
        elif age > 50: return 0.9 
        else: return 1.0


def transform_inf(resp):
    if isinstance(resp, dict):
        resp = pd.DataFrame([resp])
    
    resp['rooms'] = resp['rooms'].replace('студия', 0)
    resp[['cargo_lift', 'passenger_lift']] = resp[['cargo_lift', 'passenger_lift']].replace('нет', 0)
    resp[['cargo_lift', 'passenger_lift','rooms']] = resp[['cargo_lift', 'passenger_lift','rooms']].astype(int)
    resp['smart_floor_ratio'] = resp.apply(lambda x: smart_floor_feature(x['floor'], x['floors_total']), axis=1)
    resp = create_city_aware_age_features(resp)
    resp = create_city_specific_features(resp)
    resp = resp.drop('build_year', axis =1 )
    
    return resp[['rooms', 'total_area', 'kitchen_area', 'floor',
       'renovation', 'house_type', 'passenger_lift', 'cargo_lift', 'parking',
       'city', 'floors_total', 'smart_floor_ratio', 'house_age',
       'city_specific_age_group', 'age_city_premium', 'is_spb_historical']]

@app.get("/")
async def root():
    return {"message": "Real Estate Price Prediction API", "status": "active"}


@app.post("/predict", response_model=PredictionResponse)
async def predict_property_price(input_data: PropertyInput):
    """
    Предсказание цены недвижимости на основе параметров
    """
    try:
        input_dict = input_data.dict()
        processed_data = transform_inf(input_dict)
        df = pd.read_csv('real_estate_predictor/EDA&model_train/ready_to_train.csv.csv')
        
        col = ['rooms','total_area', 'kitchen_area','floor', 'renovation', 'house_type', 'city']
        
        distance_matrix = gower.gower_matrix(df[col], processed_data[col])
        nearest_indices = distance_matrix.argsort(axis=0)[1:4] 
        nearest_rows = df.iloc[nearest_indices.flatten()]

        similar_listings = [
            SimilarListing(
                link=row['link'],
                price=row.get('price', 0),
                rooms=row['rooms'],
                total_area=row['total_area']
            )
            for _, row in nearest_rows.iterrows()
        ]

        if model is None:
            return PredictionResponse(
                predicted_price=0,
                status="error",
                message="Model not loaded",
                similar_listings=similar_listings
            )
        
        prediction = model.predict(processed_data)
        predicted_price = round(float(np.expm1(prediction[0])), -3) 

            
        return PredictionResponse(
            predicted_price=predicted_price,
            status="success",
            message="Price predicted successfully",
            similar_listings=similar_listings
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Prediction error: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Проверка статуса API"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "timestamp": pd.Timestamp.now().isoformat()
    }

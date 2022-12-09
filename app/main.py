from requests import request
from pymongo import MongoClient
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
import uvicorn
from pydantic import BaseModel
from app.token2 import create_access_token, verify_token
from app.hashing import Hash
from app.model import User, Login, Token, TokenData
import joblib
from newspaper import Article
import json


app = FastAPI()

mongodb_uri = 'mongodb+srv://admin:admin@cluster0.eshtk.mongodb.net/?retryWrites=true&w=majority'
port = 8000
client = MongoClient(mongodb_uri, port)
db = client["User"]


@app.get('/', tags=["root"])
def home():
    return {'text': 'Welcome to News Classifier'}


class request_body(BaseModel):
    link: str


class GradRequest(BaseModel):
    name: str
    score: int
    toefl: int
    university: int
    sop: float
    lor: float
    cgpa: float
    certificate: int


@app.post('/register', tags=["Authentication"])
def create_user(request: User):
    hashed_pass = Hash.bcrypt(request.password)
    user_object = dict(request)
    user_object["password"] = hashed_pass
    user = db["users"].find_one({"username": request.username})
    if not user:
        user_id = db["users"].insert_one(user_object)
        return {"User successfully created"}
    else:
        raise HTTPException(
            status_code=403,
            detail=f'Already exists, please enter a different username')


@app.post('/login', tags=["Authentication"])
def login(request: OAuth2PasswordRequestForm = Depends()):
    user = db["users"].find_one({"username": request.username})
    if not user:
        raise HTTPException(
            status_code=401,
            detail=f'Invalid username, please try again')
    if not Hash.verify(user["password"], request.password):
        raise HTTPException(
            status_code=401,
            detail=f'Invalid password, please try again')
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access token": access_token, "token type": "bearer"}


@app.post('/predict', tags=["Core"])
def predict(data: request_body, token: str):
    user = verify_token(token)
    clf = joblib.load('./app/model/model_fakenewsclassifier.pkl')
    article = Article(data.link)
    article.download()
    article.parse()
    to_predict = article.title + ' ' + article.text
    to_predict = to_predict.lower()
    prediction = clf.predict([to_predict])
    if (prediction == 0):
        res = 'Fake'
    elif (prediction == 1):
        res = 'Real'
    return {'result': 'This News is {}'.format(res)}


@app.post('/callPredict')
def Predict(link: request_body):
    url = "https://newsclassifiertst.azurewebsites.net/login"
    user = {
        "username": "johndoe",
        "password": "secret"
    }
    response = request("POST", url, data=user)
    print(response.json())
    access_token = response.json()["access token"]
    url = "https://newsclassifiertst.azurewebsites.net/predict"
    response2 = request("POST", url+'/?token='+access_token, data=link.json())
    return response2.json()
    # if (str(response2.json()) == "['This News is Real']"):
    #     return "Real News"
    # else:
    #     return "Fake News"


@app.post('/callIisma', tags=["Core"])
def Iisma(input: GradRequest):
    # url = "https://newsclassifiertst.azurewebsites.net/token"
    # user = {
    #     "username": "tania",
    #     "password": "secret"
    # }
    # response = request("POST", url, data=user)
    # access_token = response.json()["access token"]
    url = "https://iismaprediction.azurewebsites.net/iisma/"
    response2 = request("POST", url, data=input.json())
    # response2 = request("POST", url+'/?token='+access_token, data=input.json())
    return response2.json()

from requests import request
from bs4 import BeautifulSoup
import requests
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
from sumy.parsers.html import HtmlParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer as Summarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words
import numpy as np

app = FastAPI()

mongodb_uri = 'mongodb+srv://admin:admin@cluster0.eshtk.mongodb.net/?retryWrites=true&w=majority'
port = 8000
client = MongoClient(mongodb_uri, port)
db = client["User"]


@app.get('/')
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


@app.post('/summarize', tags=["Core"])
def sumarize_news(token: str, link):
    def manual_tokenize(news):
        return news.split()
    def tokenize_sentence(news):
        return news.splitlines()

    def TF(news):
        tf = []
        for sentence in news:
            for w in sentence:
                tf.append(w)
        bow = list(set(tf))
        fin_res = {}
        for a_word in bow:
            fin_res[a_word] = w.count(a_word)
        return fin_res

    def weighting(news,TF):
        w = []
        for words in news:
            counter = 0
            for word in words:
                counter += TF[word]
            w.append(counter)
        return w

    user = verify_token(token)
    article = Article(link)
    article.download()
    article.parse()
    to_predict = article.text
    to_predict = to_predict.lower()

    sentence_list = tokenize_sentence(to_predict)
    data = []
    for sentence in sentence_list:
        data.append(manual_tokenize(sentence))
    data = (list(filter(None, data)))
    tf = TF(data)
    rank = weighting(data,tf)
    
    num = 2
    final_res = ''
    sorted_list = np.argsort(rank)[::-1][:num]
    for i in range(num):
        final_res += ' {} '.format(sentence_list[sorted_list[i]])

    return {final_res}

@app.get("/latest-news",tags=["Support"])
def get_latest_news(amount: int):
    response = requests.get("https://www.bbc.com/news")
    soup = BeautifulSoup(response.text, "html.parser")
    news_items = soup.find_all("div", class_="gs-c-promo-body")
    news_titles = [item.find("h3").text for item in news_items[:amount]]
    return {"latest_news": news_titles}


@app.post('/callIisma', tags=["Iisma Prediction"])
def Iisma(input: GradRequest):
    url = "https://iismapredictiontst.azurewebsites.net/token"
    user = {
        "username": "tania",
        "password": "secret"
    }
    response = request("POST", url, data=user)
    print(response.json())
    access_token = response.json()["access_token"]
    url = "https://iismapredictiontst.azurewebsites.net/iisma/"
    response2 = request("POST", url+'/?token='+access_token, data=input.json())
    return response2.json()


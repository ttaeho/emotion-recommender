# app.py — 감정 예측 + 운동/음악 추천 통합 앱 (klue/bert 기반)

import streamlit as st
import torch
import torch.nn as nn
from torch.nn import functional as F
from transformers import AutoTokenizer, AutoModel
from googleapiclient.discovery import build
import isodate
import requests
import random
import os
import gdown
st.set_page_config(page_title="감정 기반 추천기", layout="wide")
# 세션 상태 초기화
if "show_recommendation" not in st.session_state:
    st.session_state["show_recommendation"] = False

# ✅ 모델 구성 ------------------------------------------
class BERTClassifier(nn.Module):
    def __init__(self, bert, hidden_size=768, num_classes=6, dropout_rate=0.1):
        super(BERTClassifier, self).__init__()
        self.bert = bert
        self.dropout = nn.Dropout(dropout_rate)
        self.classifier = nn.Linear(hidden_size, num_classes)

    def forward(self, input_ids, attention_mask=None, token_type_ids=None):
        _, pooled_output = self.bert(input_ids=input_ids,
                                     attention_mask=attention_mask,
                                     token_type_ids=token_type_ids,
                                     return_dict=False)
        out = self.dropout(pooled_output)
        return self.classifier(out)

# ✅ 모델 로딩 ------------------------------------------


# ✅ 모델 파일이 없다면 Google Drive에서 다운로드
if not os.path.exists("kluebert_emotion.pt"):
    url = "https://drive.google.com/uc?id=14KcQ7KpTQXaQXETR_LS_edwiZL6j1DzO"
    gdown.download(url, "kluebert_emotion.pt", quiet=False)

# ✅ 모델 로딩
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
tokenizer = AutoTokenizer.from_pretrained("klue/bert-base")
bert = AutoModel.from_pretrained("klue/bert-base")
model = BERTClassifier(bert).to(device)

# ✅ 여기 strict=False 추가!
model.load_state_dict(torch.load("kluebert_emotion.pt", map_location=device), strict=False)
model.eval()


label_map = {
    0: "기쁨",
    1: "외로움",
    2: "화남",
    3: "두려움",
    4: "불안",
    5: "우울함"
}

# ✅ YouTube, Last.fm API 세팅 ------------------------------------------
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]
LASTFM_API_KEY = st.secrets["LASTFM_API_KEY"]
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# ✅ 감정 기반 서브 감정 분류 ------------------------------------------
emotion_group = {
    "기쁨": ["즐거움", "감사함", "희망", "상쾌함"],
    "외로움": ["고독", "혼자", "쓸쓸함"],
    "화남": ["답답함", "짜증", "분노"],
    "두려움": ["불확실함", "공포", "긴장"],
    "불안": ["초조함", "걱정됨", "예민함"],
    "우울함": ["무기력함", "슬픔", "눈물날 듯함"]
}
emotion_to_workout = {
    "즐거움": "유산소",
    "감사함": "줌바 홈트",
    "희망": "리듬 피트니스 루틴",
    "상쾌함": "상쾌한 아침 스트레칭",

    "고독": "힐링 요가 루틴",
    "혼자": "혼자하는 스트레칭",
    "쓸쓸함": "자기전 릴렉싱 홈트",

    "짜증": "킥복싱 샌드백 루틴",
    "분노": "펀치 복싱 고강도",
    "답답함": "하드코어 타바타",

    "공포": "바디스캔 명상",
    "긴장": "긴장 완화 요가",
    "불확실함": "호흡 이완 운동",

    "초조함": "필라테스 명상 루틴",
    "걱정됨": "천천히 하는 스트레칭",
    "예민함": "감정 조절 운동",

    "무기력함": "기상 5분 루틴",
    "슬픔": "햇빛 스트레칭 루틴",
    "눈물날 듯함": "마음 회복 요가"
}
# ✅ 감정 예측 함수 ------------------------------------------
def predict_emotion(text, threshold=0.6):
    tokens = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
    tokens = {k: v.to(device) for k, v in tokens.items()}
    with torch.no_grad():
        logits = model(**tokens)
        probs = F.softmax(logits, dim=1)
        max_prob, pred = torch.max(probs, dim=1)
    if max_prob.item() < threshold:
        return "기타", max_prob.item()
    return label_map[pred.item()], max_prob.item()

# ✅ 음악 추천 함수 ------------------------------------------
def get_songs_by_mood(korean_mood, api_key, sample_count=5):
    tags = {
        "즐거움": ["joyful", "upbeat"],
        "감사함": ["cinematic", "emotional"],
        "희망": ["hopeful"],
        "상쾌함": ["fresh", "uplifting"],
        "외로움": ["lonely"],
        "슬픔": ["sad", "melancholy"],
        "초조함": ["uneasy"],
        "걱정됨": ["soothing"],
        "예민함": ["gentle"],
        "화남": ["angry", "rock"],
        "답답함": ["punk"],
        "두려움": ["tense"],
        "무기력함": ["motivating"],
        "눈물날 듯함": ["emotional"]
    }.get(korean_mood, [])
    all_tracks = []
    for tag in tags:
        url = f"http://ws.audioscrobbler.com/2.0/?method=tag.gettoptracks&tag={tag}&api_key={api_key}&format=json&limit=30"
        try:
            response = requests.get(url)
            data = response.json()
            all_tracks += data.get('tracks', {}).get('track', [])
        except:
            continue
    seen = set()
    unique_tracks = []
    for track in all_tracks:
        key = (track['name'], track['artist']['name'])
        if key not in seen:
            seen.add(key)
            unique_tracks.append(track)
    sampled = random.sample(unique_tracks, min(sample_count, len(unique_tracks)))
    return [(track['name'], track['artist']['name']) for track in sampled]

# ✅ 유튜브 추천 함수 ------------------------------------------
def search_youtube(query, max_results=3):
    request = youtube.search().list(q=query, part='snippet', maxResults=max_results, type='video')
    response = request.execute()
    return [
        {
            'title': item['snippet']['title'],
            'video_id': item['id']['videoId'],
            'thumbnail': item['snippet']['thumbnails']['high']['url']
        } for item in response['items']
    ]

# ✅ Streamlit 앱 ------------------------------------------


user_input = st.text_area("당신의 감정을 문장으로 표현해주세요:", height=100)

# 감정 예측 버튼
if st.button("감정 예측 및 추천 받기"):
    with st.spinner("감정을 분석 중입니다..."):
        predicted_emotion, confidence = predict_emotion(user_input)
        st.session_state["predicted_emotion"] = predicted_emotion
        st.session_state["confidence"] = confidence
        st.session_state["show_recommendation"] = False  # 초기화

if "predicted_emotion" in st.session_state:
    predicted_emotion = st.session_state["predicted_emotion"]
    confidence = st.session_state["confidence"]
    st.success(f"예측된 감정: **{predicted_emotion}** (확신도: {confidence:.2f})")

    category_match = None
    for category, group in emotion_group.items():
        if predicted_emotion in group or predicted_emotion == category:
            category_match = category
            break

    if category_match:
        st.info(f"**{category_match}** 감정 카테고리에서 세부 감정을 선택해주세요.")
        sub_emotion = st.selectbox("세부 감정을 선택하세요", emotion_group[category_match])

        # 세부 감정 추천 트리거
        if st.button("최종 추천 보기"):
            st.session_state["show_recommendation"] = True
            st.session_state["sub_emotion"] = sub_emotion

        # 실제 추천 표시
        if st.session_state.get("show_recommendation", False):
            st.subheader("🎬 유튜브 영상 추천")
            search_query = emotion_to_workout.get(sub_emotion, sub_emotion + " 운동")
            videos = search_youtube(search_query)
            for video in videos:
                st.markdown(f"**{video['title']}**")
                st.video(f"https://www.youtube.com/watch?v={video['video_id']}")

            st.subheader("🎧 음악 추천")
            songs = get_songs_by_mood(st.session_state["sub_emotion"], LASTFM_API_KEY)
            for name, artist in songs:
                st.markdown(f"🎵 **{name}** - *{artist}*")
    else:
        st.warning("예측된 감정이 사전 설정된 감정 그룹과 일치하지 않습니다.")

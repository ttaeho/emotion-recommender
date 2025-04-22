
# app.py (대분류-세분류 감정 선택 UI 반영 버전)
import streamlit as st
import requests
import random
from googleapiclient.discovery import build
import isodate

# ========== API 키 ==========
YOUTUBE_API_KEY = 'AIzaSyDx9jT18tfD2hl3R5qmtk9vgPtW_1xz7pw'
LASTFM_API_KEY = '684f541055c4022dfd2a106fe20ac356'

youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# ========== 감정 그룹 ==========
# ========== 감정 그룹 ==========
emotion_group = {
    "기쁨": ["즐거움", "감사함", "희망", "상쾌함"],
    "슬픔": ["외로움", "허전함", "무기력함", "눈물날 듯함"],
    "불안": ["초조함", "걱정됨", "예민함"],
    "분노": ["화남", "답답함", "폭발할 것 같음"],
    "당황": ["혼란스러움", "두려움", "놀람"],
    "자기강화": ["에너지 넘침", "설렘", "몰입", "차분함", "자신감 부족"]
}

# ========== 운동 추천 매핑 ==========
emotion_to_workout = {
    "즐거움": "다이어트 댄스",
    "감사함": "감성 필라테스",
    "희망": "긍정 에너지 요가",
    "상쾌함": "전신 유산소",
    "외로움": "혼자하는 요가",
    "허전함": "느긋한 스트레칭",
    "무기력함": "10분 전신 스트레칭",
    "눈물날 듯함": "힐링 요가",
    "초조함": "불안 완화 요가",
    "걱정됨": "명상 요가",
    "예민함": "호흡 명상",
    "화남": "격한 유산소 운동",
    "답답함": "복싱 서킷",
    "폭발할 것 같음": "화풀이 인터벌 트레이닝",
    "혼란스러움": "마음 안정 스트레칭",
    "두려움": "부드러운 요가",
    "놀람": "밸런스 트레이닝",
    "에너지 넘침": "고강도 인터벌",
    "설렘": "로맨틱 요가",
    "몰입": "코어 강화 운동",
    "차분함": "명상 스트레칭",
    "자신감 부족": "근력 운동 초보자"
}


# ========== 음악 태그 ==========
korean_to_tags = {
    "즐거움": ["joyful", "upbeat", "dance"],
    "감사함": ["cinematic", "emotional"],
    "희망": ["hopeful", "positive"],
    "상쾌함": ["happy", "fresh", "uplifting"],
    "외로움": ["lonely", "slow", "introspective"],
    "허전함": ["nostalgic", "soft", "slow"],
    "무기력함": ["wake up", "motivating"],
    "눈물날 듯함": ["sad", "emotional", "melancholy"],
    "초조함": ["uneasy", "delicate"],
    "걱정됨": ["soothing", "calm", "reassuring"],
    "예민함": ["gentle", "peaceful"],
    "화남": ["angry", "aggressive", "rock"],
    "답답함": ["punk", "noise"],
    "폭발할 것 같음": ["powerful", "explosive", "high energy"],
    "혼란스러움": ["chaotic", "quirky"],
    "두려움": ["cinematic", "tense"],
    "놀람": ["surprising", "experimental"],
    "에너지 넘침": ["energetic", "workout", "motivation"],
    "설렘": ["romantic", "dreamy", "sweet"],
    "몰입": ["focus", "instrumental", "study"],
    "차분함": ["relaxing", "calm", "ambient"],
    "자신감 부족": ["empowerment", "strength"]
}

# ========== 음악 추천 ==========
def get_songs_by_mood(korean_mood, api_key, sample_count=5):
    tags = korean_to_tags.get(korean_mood)
    if not tags:
        return [("추천 불가", f"'{korean_mood}' 감정은 현재 지원되지 않습니다.")]

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

# ========== 유튜브 & 운동 분석 ==========
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

def get_video_details(video_id):
    request = youtube.videos().list(part='snippet,contentDetails', id=video_id)
    response = request.execute()
    if response['items']:
        item = response['items'][0]
        snippet = item['snippet']
        duration = item['contentDetails']['duration']
        return {
            'title': snippet['title'],
            'channel': snippet['channelTitle'],
            'tags': snippet.get('tags', []),
            'description': snippet.get('description', ''),
            'duration': duration
        }
    return None

def parse_duration(duration_str):
    duration = isodate.parse_duration(duration_str)
    return f"{duration.seconds // 60}분 {duration.seconds % 60}초"

def extract_workout_keywords(text):
    text = text.lower()
    keywords = {'부위': [], '시간': None, '기구': [], '난이도': '중간'}
    if any(x in text for x in ['전신', 'full body']): keywords['부위'].append('전신')
    if any(x in text for x in ['하체', 'leg']): keywords['부위'].append('하체')
    if any(x in text for x in ['복부', 'core', 'abs']): keywords['부위'].append('복부')
    if any(x in text for x in ['어깨', 'shoulder']): keywords['부위'].append('어깨')
    if any(x in text for x in ['등', 'back']): keywords['부위'].append('등')
    if '8분' in text: keywords['시간'] = '8분'
    if '10분' in text: keywords['시간'] = '10분'
    if '20분' in text: keywords['시간'] = '20분'
    if any(x in text for x in ['no equipment', '기구 없음']): keywords['기구'].append('기구 없음')
    if any(x in text for x in ['덤벨', 'equipment']): keywords['기구'].append('기구 있음')
    if any(x in text for x in ['beginner', '초보자']): keywords['난이도'] = '쉬움'
    if any(x in text for x in ['hiit', '어려운']): keywords['난이도'] = '어려움'
    return keywords

# ========== 통합 추천 ==========
def recommend_all_streamlit(emotion):
    st.subheader(f"🎯 감정: {emotion}")
    workout_keyword = emotion_to_workout.get(emotion)
    if workout_keyword:
        st.markdown(f"🏋️ 운동 추천 키워드: **{workout_keyword}**")
        videos = search_youtube(workout_keyword, max_results=3)
        for v in videos:
            video_info = get_video_details(v['video_id'])
            combined = ' '.join([
                video_info.get('title', ''),
                ' '.join(video_info.get('tags', [])),
                video_info.get('description', '')
            ])
            info = extract_workout_keywords(combined)
            st.markdown(f"### 🔗 [영상 보러가기](https://youtu.be/{v['video_id']})")
            st.image(v['thumbnail'], width=300)
            st.markdown(f"**제목:** {video_info['title']}")
            st.markdown(f"**채널:** {video_info['channel']}")
            st.markdown(f"**길이:** {parse_duration(video_info['duration'])}")
            st.markdown("**운동 정보 분석:**")
            st.markdown(f"- 운동 부위: {', '.join(info['부위']) if info['부위'] else '없음'}")
            st.markdown(f"- 기구: {', '.join(info['기구']) if info['기구'] else '없음'}")
            st.markdown(f"- 난이도: {info['난이도']}")
            st.markdown("---")
    else:
        st.warning("⚠️ 해당 감정에 대한 운동 키워드가 없습니다.")

    st.subheader("🎧 음악 추천")
    songs = get_songs_by_mood(emotion, LASTFM_API_KEY)
    for name, artist in songs:
        st.markdown(f"🎵 **{name}** - *{artist}*")

# ========== Streamlit 실행 ==========
st.set_page_config(page_title="감정 기반 운동+음악 추천", layout="wide")
st.title("🧠 감정 기반 운동 & 음악 추천기")

category = st.selectbox("감정 카테고리를 선택하세요", list(emotion_group.keys()))
emotion = st.selectbox("보다 세밀한 감정을 선택하세요", emotion_group[category])

if st.button("추천 받기"):
    with st.spinner("추천을 생성 중입니다..."):
        recommend_all_streamlit(emotion)

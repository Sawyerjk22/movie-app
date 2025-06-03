import streamlit as st
import pandas as pd
import requests

TMDB_API_KEY = "a1d765178f442e9b0677b32ac19d9c68"

def build_taste_profile(df, top_n=30):
    top_rated = df.sort_values(by='Your Rating', ascending=False).head(top_n)
    genre_prefs = top_rated['Genres'].str.split(', ').explode().value_counts().index.tolist()
    director_prefs = top_rated['Director'].str.split(', ').explode().value_counts().index.tolist()
    actor_prefs = top_rated['Cast'].str.split(', ').explode().value_counts().index.tolist()
    return genre_prefs[:3], director_prefs[:3], actor_prefs[:3]

st.set_page_config(page_title="Sawyer Movie DNA", layout="wide")
st.title("🎬 Sawyer Knox Movie DNA & Recommender")
st.markdown("Upload your enriched Letterboxd export to see stats, recs, and what's new for you.")

uploaded_file = st.file_uploader("Upload your enriched Letterboxd file (Excel or CSV)", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    st.success(f"Loaded {len(df)} movies.")

    st.subheader("Your Top Genres")
    genre_counts = df['Genres'].str.split(', ').explode().value_counts()
    st.bar_chart(genre_counts)

    st.subheader("Directors You've Watched Most")
    director_counts = df['Director'].str.split(', ').explode().value_counts()
    st.dataframe(director_counts.head(10))

    if 'Your Rating' in df.columns:
        st.subheader("Your Top-Rated Films")
        st.dataframe(df.sort_values('Your Rating', ascending=False).head(10)[['Name', 'Year', 'Your Rating', 'Genres', 'Director']])

    # === Personalized Recommendations ===
    st.subheader("Monthly Recommendations (Demo)")
    st.subheader("Personalized Movie Recommendations")

    genre_prefs, director_prefs, actor_prefs = build_taste_profile(df)
    st.markdown(f"**Profile Summary**: Likes genres {genre_prefs}, directors {director_prefs}, actors {actor_prefs}")

    recommended_movies = []
    search_terms = director_prefs + actor_prefs
    seen_titles = set(df['Name'].str.lower())

    for name in search_terms:
        url = "https://api.themoviedb.org/3/search/person"
        params = {"api_key": TMDB_API_KEY, "query": name}
        r = requests.get(url, params=params)
        if not r.ok or not r.json().get('results'):
            continue
        person_id = r.json()['results'][0]['id']

        url = f"https://api.themoviedb.org/3/person/{person_id}/movie_credits"
        r = requests.get(url, params={"api_key": TMDB_API_KEY})
        if not r.ok:
            continue
        credits = r.json().get('cast', []) + r.json().get('crew', [])
        for movie in credits:
            title = movie.get('title')
            if not title or title.lower() in seen_titles:
                continue
            recommended_movies.append({
                "title": title,
                "release_date": movie.get('release_date'),
                "known_for": name
            })

    if recommended_movies:
        recs_df = pd.DataFrame(recommended_movies).drop_duplicates(subset='title').sort_values('release_date', ascending=False).head(10)
        st.dataframe(recs_df)
    else:
        st.info("No personalized recs found yet — try uploading a log with more data.")

    # === Upcoming Releases ===
    st.subheader("Upcoming Releases You Might Like")

    genres = set(genre_counts.head(3).index)
    upcoming = []

    for genre in genres:
        url = f"https://api.themoviedb.org/3/discover/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "sort_by": "release_date.desc",
            "include_adult": "false",
            "with_genres": "",  # To be mapped in future
            "primary_release_date.gte": "2024-01-01"
        }
        resp = requests.get(url, params=params)
        if resp.ok:
            results = resp.json().get('results', [])[:3]
            for movie in results:
                upcoming.append({
                    "title": movie['title'],
                    "release_date": movie['release_date']
                })

    if upcoming:
        st.dataframe(pd.DataFrame(upcoming))
    else:
        st.info("Upcoming recommendations will appear here.")

else:
    st.info("Upload your enriched Letterboxd file to begin.")

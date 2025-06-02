import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Boss Man Movie DNA", layout="wide")

st.title("🎬 Sawyer Knox Movie DNA & Recommender")
st.markdown("Upload your enriched Letterboxd export to see stats, recs, and what's new for you.")

# 1. Upload file
uploaded_file = st.file_uploader("Upload your enriched Letterboxd file (Excel or CSV)", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    st.success(f"Loaded {len(df)} movies.")
    
    # Show some stats/charts
    st.subheader("Your Top Genres")
    genre_counts = df['Genres'].str.split(', ').explode().value_counts()
    st.bar_chart(genre_counts)
    
    st.subheader("Directors You've Watched Most")
    director_counts = df['Director'].str.split(', ').explode().value_counts()
    st.dataframe(director_counts.head(10))
    
    # Top-rated movies (by you)
    if 'Your Rating' in df.columns:
        st.subheader("Your Top-Rated Films")
        st.dataframe(df.sort_values('Your Rating', ascending=False).head(10)[['Name', 'Year', 'Your Rating', 'Genres', 'Director']])

    # Placeholder for recommendations (expand later)
    st.subheader("Monthly Recommendations (Demo)")
    st.write("These would be generated based on your taste. [More to come!]")

    # Get new releases from TMDb matching your genres (example)
    st.subheader("Upcoming Releases You Might Like")
    # ---- Insert TMDb code below ----

    # Example TMDb API call (requires your API key)
    TMDB_API_KEY = "a1d765178f442e9b0677b32ac19d9c68"
    genres = set()
    for g in genre_counts.head(3).index:
        genres.add(g)
    upcoming = []
    for genre in genres:
        url = f"https://api.themoviedb.org/3/discover/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "sort_by": "release_date.desc",
            "include_adult": "false",
            "with_genres": "", # genre id, can add advanced mapping later
            "primary_release_date.gte": "2024-01-01"
        }
        resp = requests.get(url, params=params)
        if resp.ok:
            results = resp.json().get('results', [])[:3]
            for movie in results:
                upcoming.append({"title": movie['title'], "release_date": movie['release_date']})
    if upcoming:
        st.write(pd.DataFrame(upcoming))
    else:
        st.info("Upcoming recommendations will appear here.")

else:
    st.info("Upload your enriched Letterboxd file to begin.")

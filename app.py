# Sawyer's Upgraded Movie DNA App (v5+) - Intelligent Recommender + Taste Analysis

import streamlit as st
import pandas as pd
import requests
import datetime
from time import sleep
import os

TMDB_API_KEY = "a1d765178f442e9b0677b32ac19d9c68"
TODAY = datetime.date.today()
NEXT_YEAR = TODAY + datetime.timedelta(days=365)

st.set_page_config(page_title="Sawyer Movie DNA", layout="wide")
st.title("🎮 Sawyer Knox Movie DNA & Recommender")
st.markdown("Upload your enriched Letterboxd export to see stats, recs, and what's new for you.")

uploaded_file = st.file_uploader("Upload your enriched Letterboxd file (Excel or CSV)", type=["xlsx", "csv"])

@st.cache_data
def load_public_ratings():
    try:
        return pd.read_csv("TMDb_Public_Ratings.csv")
    except FileNotFoundError:
        return pd.DataFrame(columns=["TMDb ID", "IMDb ID", "Title", "Year", "Public Avg Rating"])

def get_tmdb_rating(imdb_id):
    url = f"https://api.themoviedb.org/3/find/{imdb_id}"
    params = {"api_key": TMDB_API_KEY, "external_source": "imdb_id"}
    r = requests.get(url, params=params)
    if r.ok:
        results = r.json().get("movie_results", [])
        if results:
            return results[0].get("vote_average", None), results[0].get("id")
    return None, None

def score_decade(year):
    try:
        y = int(year)
        return int(y // 10 * 10)
    except:
        return None

def generate_taste_profile(merged, genre_summary, top_dirs, decade_scores):
    top_genres = genre_summary.sort_values("Your Rating", ascending=False).head(3).index.tolist()
    top_decades = sorted(decade_scores.items(), key=lambda x: -x[1])[:2]
    top_director_names = top_dirs.head(3).index.tolist()

    parts = []
    if top_genres:
        parts.append(f"You gravitate toward genres like **{', '.join(top_genres)}**.")
    if top_decades:
        parts.append("You especially enjoy films from the " + " and ".join([f"**{int(d)}s**" for d, _ in top_decades]) + ".")
    if top_director_names:
        parts.append("Your highest-rated directors include " + ", ".join([f"**{d}**" for d in top_director_names]) + ".")
    rt_mean = merged['Runtime'].mean()
    if rt_mean >= 120:
        parts.append("You don’t mind long runtimes — many of your favorites run over 2 hours.")
    elif rt_mean <= 90:
        parts.append("You prefer leaner films — under 90 minutes tends to score best for you.")
    else:
        parts.append("You're flexible on runtime, but seem to favor quality over length.")

    return " ".join(parts)

GENRE_NAME_TO_ID = {
    "Action": 28,
    "Adventure": 12,
    "Animation": 16,
    "Comedy": 35,
    "Crime": 80,
    "Documentary": 99,
    "Drama": 18,
    "Family": 10751,
    "Fantasy": 14,
    "History": 36,
    "Horror": 27,
    "Music": 10402,
    "Mystery": 9648,
    "Romance": 10749,
    "Science Fiction": 878,
    "TV Movie": 10770,
    "Thriller": 53,
    "War": 10752,
    "Western": 37
}
EXCLUDED_GENRES = {"TV Movie", "Family"}  # You can add "Animation" if needed
MIN_VOTE_COUNT = 1000

if uploaded_file:
    df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith("xlsx") else pd.read_csv(uploaded_file)
    st.success(f"Loaded {len(df)} movies.")

    ratings_lookup = load_public_ratings()
    df.columns = [c.strip().replace(" ", "_") for c in df.columns]
    ratings_lookup.columns = [c.strip().replace(" ", "_") for c in ratings_lookup.columns]

    merged = df.merge(ratings_lookup, on=["IMDb_ID"], how="left", suffixes=("", "_public"))
    missing = merged[merged['Public_Avg_Rating'].isna() & merged['IMDb_ID'].notna()]
    new_ratings = []
    for _, row in missing.iterrows():
        rating, tmdb_id = get_tmdb_rating(row['IMDb_ID'])
        if rating is not None:
            new_ratings.append({
                "TMDb ID": tmdb_id,
                "IMDb ID": row['IMDb_ID'],
                "Title": row['Name'],
                "Year": row['Year'],
                "Public Avg Rating": rating
            })
            merged.loc[row.name, 'Public_Avg_Rating'] = rating
        sleep(0.25)
    if new_ratings:
        new_df = pd.DataFrame(new_ratings)
        if os.path.exists("missing_ratings.csv"):
            new_df.to_csv("missing_ratings.csv", mode='a', index=False, header=False)
        else:
            new_df.to_csv("missing_ratings.csv", index=False)

    merged['Public_Avg_Rating'] = merged['Public_Avg_Rating'] / 2
    merged['Decade'] = merged['Year'].apply(score_decade)
    # Analyze your preferred age ratings (like PG-13, R, etc.)
    rating_counts = merged['Certificate'].value_counts()
    preferred_certificates = rating_counts[rating_counts > 2].index.tolist()


    st.subheader("Your Rating Distribution (0–10 scale)")
    st.bar_chart(merged['Rating'].value_counts().sort_index())

    st.subheader("Average Rating by Genre (You vs Public)")
    genre_rows = []
    for _, row in merged.iterrows():
        if pd.isna(row['Genres']): continue
        for genre in str(row['Genres']).split(', '):
            genre_rows.append({"Genre": genre, "Your Rating": row['Rating'], "Public Rating": row['Public_Avg_Rating']})
    genre_df = pd.DataFrame(genre_rows)
    genre_summary = genre_df.groupby("Genre").agg({"Your Rating": "mean", "Public Rating": "mean"}).round(2)
    st.dataframe(genre_summary.sort_values("Your Rating", ascending=False))

    st.subheader("Top-Rated Directors (min 2 films)")
    dir_ratings = merged.dropna(subset=['Rating', 'Director'])
    dir_rows = []
    for _, row in dir_ratings.iterrows():
        for d in str(row['Director']).split(', '):
            dir_rows.append({"Director": d, "Rating": row['Rating']})
    dir_df = pd.DataFrame(dir_rows)
    top_dirs = dir_df.groupby("Director").agg(["count", "mean"]).droplevel(0, axis=1)
    top_dirs.columns = ["# Films", "Avg Rating"]
    top_dirs = top_dirs[top_dirs["# Films"] >= 2].sort_values("Avg Rating", ascending=False)
    st.dataframe(top_dirs.round(2))

    st.subheader("Country Preference (min 3 films, ≥2 directors)")
    countries = []
    for _, row in merged.iterrows():
        for c in str(row['Country']).split(', '):
            countries.append({"Country": c, "Rating": row['Rating'], "Director": row['Director']})
    country_df = pd.DataFrame(countries)
    agg = country_df.groupby("Country").agg({"Rating": "mean", "Director": pd.Series.nunique, "Country": "count"}).rename(columns={"Director": "# Unique Directors", "Country": "# Films"})
    agg = agg[(agg["# Films"] >= 3) & (agg["# Unique Directors"] >= 2)]
    st.dataframe(agg.sort_values("Rating", ascending=False).round(2))

    decade_scores = merged.groupby("Decade")['Rating'].mean().to_dict()

    st.subheader("Taste Profile Narrative")
    taste_summary = generate_taste_profile(merged, genre_summary, top_dirs, decade_scores)
    st.markdown(taste_summary)

    st.markdown("## 🎛️ Recommendation Filters")
    min_rating = st.slider("Minimum Public Rating (out of 5)", 0.0, 5.0, 3.5, 0.1)
    max_year = st.slider("Latest Release Year", 1950, TODAY.year, TODAY.year)

    st.markdown("## 🎯 Smart Recommendations (Released Films)")
    seen = set(merged['Name'].str.lower())
    def score_candidate(movie, user_top_genres, user_decades, preferred_certificates):
        score = 0
        reason = []

    title = movie.get("title", "").strip()
       if not title:
        return None

    vote_count = movie.get("vote_count", 0)
    pub_rating = float(movie.get("vote_average", 0)) / 2
    release_date = movie.get("release_date", "")
    year = int(release_date[:4]) if release_date else 0
    decade = score_decade(year)

    if vote_count < MIN_VOTE_COUNT or not release_date:
        return None
    if pub_rating < min_rating or year > max_year:
        return None

    # TMDb genre IDs to names
    genre_ids = movie.get("genre_ids", [])
    genres = [k for k, v in GENRE_NAME_TO_ID.items() if v in genre_ids]
    if any(g in EXCLUDED_GENRES for g in genres):
        return None

    # Genre match
    match_genres = [g for g in genres if g in user_top_genres]
    if match_genres:
        score += 1.5 * len(match_genres)
        reason.append(f"Top genres: {', '.join(match_genres)}")

    # Decade match
    if decade in user_decades:
        score += 1.0
        reason.append(f"Matches your {decade}s taste")

    # Public acclaim
    if pub_rating >= 4:
        score += 1.0
        reason.append("Critically acclaimed")

    # Certificate match (if TMDb adds it — not guaranteed here)
    cert = movie.get("certification")
    if cert and cert in preferred_certificates:
        score += 0.5
        reason.append(f"Preferred rating: {cert}")

    return {
        "Title": title,
        "Release Date": release_date,
        "Public Rating": round(pub_rating, 2),
        "Why": ", ".join(reason),
        "Score": score
    }

    scored_recs = []
    top_genres = genre_summary.sort_values("Your Rating", ascending=False).head(5).index.tolist()
    genre_ids = [GENRE_NAME_TO_ID.get(g) for g in top_genres if GENRE_NAME_TO_ID.get(g)]

    scored_recs = []
    seen = set(merged['Name'].str.lower())
    ser_decades = set(decade_scores.keys())

for gid in genre_ids:
    url = "https://api.themoviedb.org/3/discover/movie"
    r = requests.get(url, params={
        "api_key": TMDB_API_KEY,
        "with_genres": gid,
        "sort_by": "vote_average.desc",
        "vote_count.gte": MIN_VOTE_COUNT,
        "primary_release_date.lte": TODAY,
        "include_adult": "false"
    })
    if not r.ok:
        continue
    for m in r.json().get("results", []):
        if m.get("title", "").lower() in seen:
            continue
        scored = score_candidate(m, top_genres, user_decades, preferred_certificates)
        if scored:
            scored_recs.append(scored)

# Final display
if scored_recs:
    rec_df = pd.DataFrame(scored_recs).sort_values("Score", ascending=False).drop_duplicates("Title")
    st.dataframe(rec_df[["Title", "Release Date", "Public Rating", "Why"]].reset_index(drop=True), use_container_width=True, height=600)
else:
    st.info("No solid recs found — try uploading a bigger log file.")


    if scored_recs:
        rec_df = pd.DataFrame(scored_recs).drop_duplicates("Title")
        rec_df = rec_df.sort_values("Public Rating", ascending=False).head(50)
        st.dataframe(rec_df.reset_index(drop=True), use_container_width=True, height=600)
    else:
        st.info("No solid recs found — try uploading a bigger log file.")

    st.subheader("Upcoming Releases (Next 12 Months)")
    for genre in top_genres:
        genre_id = GENRE_NAME_TO_ID.get(genre)
        if not genre_id:
            continue
        url = "https://api.themoviedb.org/3/discover/movie"
        r = requests.get(url, params={
            "api_key": TMDB_API_KEY,
            "sort_by": "primary_release_date.asc",
            "primary_release_date.gte": TODAY,
            "primary_release_date.lte": NEXT_YEAR,
            "with_genres": genre_id,
            "include_adult": "false"
        })
        if r.ok:
            data = r.json().get("results", [])
            filtered = [{"Title": m['title'], "Release Date": m['release_date']} for m in data if m.get("title") and m.get("release_date")]
            if filtered:
                st.markdown(f"**Upcoming {genre}**")
                st.dataframe(pd.DataFrame(filtered[:10]))
        else:
         st.info("Upload your enriched Letterboxd file to begin.")





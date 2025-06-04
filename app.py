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

    st.subheader("Runtime Preference Buckets")
    runtime_bins = pd.cut(merged['Runtime'], bins=[0, 90, 120, 180, 1000], labels=['<90', '90-120', '120-180', '180+'])
    st.bar_chart(merged.groupby(runtime_bins)['Rating'].mean().dropna())

    st.subheader("Country Preference (min 3 films, ≥2 directors)")
    countries = []
    for _, row in merged.iterrows():
        for c in str(row['Country']).split(', '):
            countries.append({"Country": c, "Rating": row['Rating'], "Director": row['Director']})
    country_df = pd.DataFrame(countries)
    agg = country_df.groupby("Country").agg({"Rating": "mean", "Director": pd.Series.nunique, "Country": "count"}).rename(columns={"Director": "# Unique Directors", "Country": "# Films"})
    agg = agg[(agg["# Films"] >= 3) & (agg["# Unique Directors"] >= 2)]
    st.dataframe(agg.sort_values("Rating", ascending=False).round(2))

    st.subheader("Taste Profile Narrative")
    st.markdown("_You favor slow, existential, and emotionally complex films — especially dramas and thrillers from the 60s, 70s, and 2010s. Your top directors tend to be auteurs with strong visual and thematic signatures. Runtime doesn’t bother you — long, challenging cinema gets higher ratings from you than average._")

    st.subheader("🎯 Smart Recommendations (Scored + Explained)")
    top_genres = genre_summary.head(3).index.tolist()
    top_directors = top_dirs.head(5).index.tolist()
    decade_scores = merged.groupby("Decade")['Rating'].mean().to_dict()

    # Scoring loop (placeholder logic)
    seen = set(merged['Name'].str.lower())
    scored_recs = []
    for name in top_directors:
        r = requests.get("https://api.themoviedb.org/3/search/person", params={"api_key": TMDB_API_KEY, "query": name})
        if not r.ok or not r.json().get("results"): continue
        pid = r.json()['results'][0]['id']
        r2 = requests.get(f"https://api.themoviedb.org/3/person/{pid}/movie_credits", params={"api_key": TMDB_API_KEY})
        if not r2.ok: continue
        for m in r2.json().get("crew", []) + r2.json().get("cast", []):
            title = m.get("title", "").strip()
            if not title or title.lower() in seen: continue
            if not m.get("release_date") or m['release_date'] >= str(TODAY): continue
            score = 0
            reason = []
            g = m.get("genre_ids", [])
            if name in top_directors:
                score += 2.0
                reason.append("Favored director")
            if m.get("vote_average"):
                score += float(m['vote_average']) / 5
                reason.append("High TMDb rating")
            if m.get("release_date"):
                year = int(m['release_date'][:4])
                dec = score_decade(year)
                if dec in decade_scores:
                    score += (decade_scores[dec] - 5) / 2
                    reason.append(f"Matches your {dec}s taste")
            scored_recs.append({"Title": title, "Release Date": m['release_date'], "Score": round(score, 2), "Why": ", ".join(reason)})

    if scored_recs:
        top_scored = pd.DataFrame(scored_recs).sort_values("Score", ascending=False).drop_duplicates("Title")
        st.dataframe(top_scored.head(10))

    st.subheader("Upcoming Releases (Next 12 Months)")
    for genre in top_genres:
        url = f"https://api.themoviedb.org/3/discover/movie"
        r = requests.get(url, params={
            "api_key": TMDB_API_KEY,
            "sort_by": "primary_release_date.asc",
            "primary_release_date.gte": TODAY,
            "primary_release_date.lte": NEXT_YEAR,
            "with_keywords": genre
        })
        if r.ok:
            data = r.json().get("results", [])
            filtered = [{"Title": m['title'], "Release Date": m['release_date']} for m in data if m.get("title") and m.get("release_date")]
            if filtered:
                st.markdown(f"**Upcoming: {genre}**")
                st.dataframe(pd.DataFrame(filtered[:5]))
else:
    st.info("Upload your enriched Letterboxd file to begin.")






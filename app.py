import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Anime Analytics Dashboard", page_icon="", layout="wide")

st.markdown("""
<style>
    .main-header {font-size: 2.5rem; font-weight: bold; color: #FF6B6B; text-align: center; margin: 2rem 0;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    try:
        df = pd.read_csv('anime_dataset.csv')
    except:
        st.error("Dataset not found. Please upload anime_dataset.csv")
        return None
    
    df['year'] = pd.to_datetime(df['start_date'], errors='coerce').dt.year
    
    def safe_eval(val):
        try:
            if pd.isna(val) or val in ['[]', '']:
                return []
            if isinstance(val, str):
                import ast
                return ast.literal_eval(val)
            return val if isinstance(val, list) else []
        except:
            return []
    
    df['genres_list'] = df['genres'].apply(safe_eval)
    df['studios_list'] = df['studios'].apply(safe_eval)
    
    return df

df = load_data()
if df is None:
    st.stop()

st.sidebar.title("Filters")
st.sidebar.markdown("---")

min_year = int(df['year'].min()) if df['year'].notna().any() else 1917
max_year = int(df['year'].max()) if df['year'].notna().any() else 2025
year_range = st.sidebar.slider("Year Range", min_year, max_year, (2000, 2025))
score_min = st.sidebar.slider("Minimum Score", 0.0, 10.0, 6.0, 0.1)

df_filtered = df[
    (df['year'] >= year_range[0]) & 
    (df['year'] <= year_range[1]) & 
    (df['score'] >= score_min)
].copy()

st.markdown('<h1 class="main-header">Anime Analytics Dashboard</h1>', unsafe_allow_html=True)
st.markdown("Exploring 108 years of anime data (1917-2025)")
st.markdown("---")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Anime", f"{len(df_filtered):,}")
with col2:
    st.metric("Avg Score", f"{df_filtered['score'].mean():.2f}")
with col3:
    st.metric("Total Members", f"{df_filtered['members'].sum()/1e6:.1f}M")
with col4:
    genres_flat = [g for genres in df_filtered['genres_list'] for g in genres]
    top_genre = pd.Series(genres_flat).value_counts().index[0] if genres_flat else "N/A"
    st.metric("Top Genre", top_genre)

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Hidden Gems", "Trends", "Search"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Score Distribution")
        fig = px.histogram(df_filtered, x='score', nbins=40, color_discrete_sequence=['#FF6B6B'])
        fig.update_layout(height=400, showlegend=False, xaxis_title="Score", yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Top Studios")
        studios_flat = [s for studios in df_filtered['studios_list'] for s in studios]
        if studios_flat:
            top_studios = pd.Series(studios_flat).value_counts().head(10)
            fig = px.bar(x=top_studios.values, y=top_studios.index, orientation='h',
                        color_discrete_sequence=['#4ECDC4'])
            fig.update_layout(height=400, showlegend=False, yaxis_title="", xaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Hidden Gems Analysis")
    
    df_gems = df_filtered[
        (df_filtered['recommendation_count'].notna()) & 
        (df_filtered['members'] > 100)
    ].copy()
    
    if len(df_gems) > 0:
        df_gems['rec_ratio'] = df_gems['recommendation_count'] / df_gems['members']
        
        median_members = df_gems['members'].median()
        median_ratio = df_gems['rec_ratio'].median()
        
        fig = px.scatter(df_gems, x='members', y='rec_ratio', 
                        color='score', size='recommendation_count',
                        hover_data=['title', 'score', 'members'],
                        title='Hidden Gems: Recommendation Efficiency',
                        labels={'members': 'Members (Log Scale)', 'rec_ratio': 'Recommendation Ratio'},
                        color_continuous_scale='Viridis', log_x=True)
        
        fig.add_vline(x=median_members, line_dash="dash", line_color="gray")
        fig.add_hline(y=median_ratio, line_dash="dash", line_color="gray")
        fig.update_layout(height=600)
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("#### Top Hidden Gems")
        hidden = df_gems[
            (df_gems['members'] < median_members) & 
            (df_gems['rec_ratio'] > median_ratio)
        ].nlargest(10, 'rec_ratio')[['title', 'score', 'members', 'rec_ratio']]
        st.dataframe(hidden, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Genre Trends")
    
    df_trends = df_filtered[df_filtered['genres_list'].apply(len) > 0].copy()
    df_trends['decade'] = (df_trends['year'] // 10) * 10
    
    all_genres = [g for genres in df_trends['genres_list'] for g in genres]
    top_genres = pd.Series(all_genres).value_counts().head(6).index.tolist()
    
    if top_genres:
        genre_counts = []
        for decade in sorted(df_trends['decade'].unique()):
            decade_data = df_trends[df_trends['decade'] == decade]
            decade_genres = [g for genres in decade_data['genres_list'] for g in genres]
            for genre in top_genres:
                genre_counts.append({
                    'decade': decade,
                    'genre': genre,
                    'count': decade_genres.count(genre)
                })
        
        genre_df = pd.DataFrame(genre_counts)
        
        fig = px.line(genre_df, x='decade', y='count', color='genre',
                     title='Genre Evolution Over Decades', markers=True)
        fig.update_layout(height=500, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Type Distribution")
        type_counts = df_filtered['type'].value_counts().head(6)
        fig = px.pie(values=type_counts.values, names=type_counts.index, hole=0.4)
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### Average Score by Type")
        type_scores = df_filtered.groupby('type')['score'].mean().sort_values(ascending=False).head(6)
        fig = px.bar(x=type_scores.values, y=type_scores.index, orientation='h',
                    color_discrete_sequence=['#E74C3C'])
        fig.update_layout(height=350, xaxis_title="Average Score", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("Search and Explore")
    
    search = st.text_input("Search by title")
    
    if search:
        results = df_filtered[df_filtered['title'].str.contains(search, case=False, na=False)]
        st.write(f"Found {len(results)} results")
    else:
        results = df_filtered
        st.write(f"Showing top 100 results")
    
    display_cols = ['title', 'score', 'year', 'type', 'episodes', 'members', 'favorites']
    available_cols = [col for col in display_cols if col in results.columns]
    
    st.dataframe(
        results[available_cols].sort_values('score', ascending=False).head(100),
        use_container_width=True,
        hide_index=True
    )

st.sidebar.markdown("---")
st.sidebar.markdown("Anime Analytics Dashboard - MSc Data Science")

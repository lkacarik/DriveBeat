import sqlite3
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt
import os, warnings

os.environ["LOKY_MAX_CPU_COUNT"] = "6"
warnings.filterwarnings("ignore")

# -------------------------------------------------------
# POSTAVKE
# -------------------------------------------------------
DB_PATH = r"D:\FOI\3. godina\ZAVRSNI\glazba.db"
K = 3
FEATURES = ['tempo', 'energy', 'valence', 'danceability', 'acousticness', 'instrumentalness']
# -------------------------------------------------------

# Učitaj bazu
conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("""
    SELECT id, title, artist, tempo, energy, valence,
           danceability, acousticness, instrumentalness
    FROM songs
""", conn)
conn.close()

print(f"Učitano {len(df)} pjesama.")

# Normalizacija
X = df[FEATURES].values
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# K-Means s odabranim K
km = KMeans(n_clusters=K, random_state=42, n_init=10)
df['cluster'] = km.fit_predict(X_scaled)

# Upiši klastere u bazu
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
for _, row in df.iterrows():
    cursor.execute("UPDATE songs SET cluster = ? WHERE id = ?",
                   (int(row['cluster']), int(row['id'])))
conn.commit()
conn.close()

print(f"\nKlasteri upisani u bazu.")

# Provjera
conn = sqlite3.connect(DB_PATH)
provjera = pd.read_sql_query(
    "SELECT title, artist, tempo, cluster FROM songs ORDER BY cluster, tempo",
    conn
)
conn.close()
print(f"\n{provjera.to_string()}")
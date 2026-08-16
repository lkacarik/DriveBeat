import sqlite3
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import os, warnings

os.environ["LOKY_MAX_CPU_COUNT"] = "6" #da se makne upozorenje za CPU corove
warnings.filterwarnings("ignore") #da makne jos druga neka random upozorenja

DB_PATH = r"D:\FOI\3. godina\ZAVRSNI\DriveBeat\glazba.db"
K = 3 #br klastera
FEATURES = ['tempo', 'energy', 'valence', 'danceability', 'acousticness', 'instrumentalness']

def main():
    #citanje iz baze
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT id, title, artist, tempo, energy, valence,
               danceability, acousticness, instrumentalness
        FROM songs
    """, conn)
    conn.close()

    print(f"Ucitano {len(df)} pjesama.")

    #normalizacija da se ujednace vaznosti featura
    X = df[FEATURES].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    #kmeans
    km = KMeans(n_clusters=K, random_state=23, n_init=10)
    df['cluster'] = km.fit_predict(X_scaled)#upisivanje klastera u df

    #upisivanje klastera nazad u bazu
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute("UPDATE songs SET cluster = ? WHERE id = ?",
                       (int(row['cluster']), int(row['id'])))
    conn.commit()
    conn.close()

    print(f"\nKlasteri upisani u bazu.")

    #provjera i ispis pjesama i klastera
    conn = sqlite3.connect(DB_PATH)
    provjera = pd.read_sql_query(
        "SELECT title, artist, tempo, cluster FROM songs ORDER BY cluster, tempo",
        conn
    )
    conn.close()
    print(f"\n{provjera.to_string()}")


if __name__ == "__main__":
    main()
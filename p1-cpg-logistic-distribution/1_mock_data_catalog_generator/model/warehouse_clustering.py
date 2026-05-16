"""
K-Means geographic clustering model to optimize Warehouse (distribution center or Cedi most common in Latam)
placement for a CPG retail network (Walmart / Soriana / Chedraui).
"""

import os
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


# ── Constants ─────────────────────────────────────────────────────────────────

MEXICO_BBOX = dict(lat_min=14, lat_max=33, lon_min=-118, lon_max=-86)

K_RANGE = range(3, 14)

SEGMENT_SCORE = {"gold": 3, "silver": 2, "bronze": 1}

PALETTE = [
    "#3266AD", "#E05C2F", "#2DA875", "#C94B8F", "#7B5EA7",
    "#E8A020", "#2C8C99", "#B03A2E", "#1A7843", "#5D4E8C",
    "#C27A2B", "#1B6391", "#8B2FC9",
]

BRAND_MARKERS = {"Walmart": "o", "Soriana": "s", "Chedraui": "^"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def haversine(lat1: np.ndarray, lon1: np.ndarray,
              lat2: float, lon2: float) -> np.ndarray:
    """Return great-circle distance in km between point arrays and a centroid."""
    R = 6_371
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2))
         * np.sin(dlon / 2) ** 2)
    return R * 2 * np.arcsin(np.sqrt(a))


# ── Pipeline steps ────────────────────────────────────────────────────────────

def _validate_and_filter(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate required columns, remove geographic outliers outside Mexico's
    bounding box, and return a clean copy.

    Required columns: lat, lon, name, brand, city, state, segment.
    """
    required_cols = {"lat", "lon", "name", "brand", "city", "state", "segment"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Input DataFrame is missing columns: {missing}")

    filtered = df[
        (df["lat"] > MEXICO_BBOX["lat_min"]) & (df["lat"] < MEXICO_BBOX["lat_max"]) &
        (df["lon"] > MEXICO_BBOX["lon_min"]) & (df["lon"] < MEXICO_BBOX["lon_max"])
    ].dropna(subset=["lat", "lon"]).copy().reset_index(drop=True)

    removed = len(df) - len(filtered)
    print(f"[load]    {len(filtered)} stores kept after filtering "
          f"({removed} removed as geographic outliers).")
    return filtered


def _find_optimal_k(coords: np.ndarray) -> tuple:
    """
    Evaluate k in K_RANGE using inertia (elbow) and silhouette score.
    Returns best_k, inertias list, silhouettes list.
    """
    inertias, silhouettes = [], []
    for k in K_RANGE:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(coords)
        inertias.append(km.inertia_)
        silhouettes.append(silhouette_score(coords, labels))

    best_k = list(K_RANGE)[int(np.argmax(silhouettes))]
    print(f"[kmeans]  Optimal k={best_k}  |  Silhouette={max(silhouettes):.3f}")
    return best_k, inertias, silhouettes


def _fit_clusters(df: pd.DataFrame, coords: np.ndarray,
                  best_k: int) -> tuple:
    """Fit final K-Means model and attach cluster labels to df."""
    km = KMeans(n_clusters=best_k, random_state=42, n_init=20)
    df = df.copy()
    df["cluster"] = km.fit_predict(coords)
    df["seg_score"] = df["segment"].map(SEGMENT_SCORE)
    centroids = km.cluster_centers_
    print(f"[kmeans]  Model fitted — {best_k} clusters.")
    return df, centroids


def _build_cluster_stats(df: pd.DataFrame,
                         centroids: np.ndarray) -> pd.DataFrame:
    """Aggregate per-cluster KPIs and compute max coverage radius."""
    stats = df.groupby("cluster").agg(
        stores        = ("name",      "count"),
        lat_centroid  = ("lat",       "mean"),
        lon_centroid  = ("lon",       "mean"),
        gold          = ("segment",   lambda x: (x == "gold").sum()),
        silver        = ("segment",   lambda x: (x == "silver").sum()),
        bronze        = ("segment",   lambda x: (x == "bronze").sum()),
        avg_seg_score = ("seg_score", "mean"),
        states        = ("state",     "nunique"),
        main_city     = ("city",      lambda x: x.value_counts().index[0]),
    ).reset_index()

    max_radii = []
    for _, row in stats.iterrows():
        c = int(row["cluster"])
        mask = df["cluster"] == c
        dists = haversine(
            df.loc[mask, "lat"].values, df.loc[mask, "lon"].values,
            centroids[c, 0], centroids[c, 1],
        )
        max_radii.append(round(float(dists.max()), 1))
    stats["max_radius_km"] = max_radii
    return stats


def _build_store_df(df: pd.DataFrame, centroids: np.ndarray,
                    stats: pd.DataFrame) -> pd.DataFrame:
    name_map = {
        int(row["cluster"]): f"CEDI-{int(row['cluster']) + 1:02d} · {row['main_city']}"
        for _, row in stats.iterrows()
    }
    out = df.copy()
    out["warehouse"] = out["cluster"].map(name_map)
    out = out.drop(columns=["cluster", "seg_score"])
    return out


def _build_warehouse_catalog(stats: pd.DataFrame) -> pd.DataFrame:
    """
    Build and return the warehouse catalog DataFrame.

    Schema
    ──────
    warehouse_id    : int   — 1-based identifier (CEDI 1, CEDI 2, …)
    warehouse_name  : str   — human-readable label, e.g. "CEDI-01 · Monterrey"
    lat             : float — centroid latitude
    lon             : float — centroid longitude
    stores_served   : int   — total stores assigned to this CEDI
    gold            : int   — gold-tier stores
    silver          : int   — silver-tier stores
    bronze          : int   — bronze-tier stores
    avg_seg_score   : float — weighted quality index (1–3)
    states_covered  : int   — number of distinct states in the cluster
    max_radius_km   : float — max great-circle distance to farthest store
    """
    catalog = pd.DataFrame({
        "warehouse_id":   stats["cluster"] + 1,
        "warehouse_name": stats.apply(
            lambda r: f"CEDI-{int(r['cluster']) + 1:02d} · {r['main_city']}", axis=1
        ),
        "lat":            stats["lat_centroid"].round(4),
        "lon":            stats["lon_centroid"].round(4),
        "stores_served":  stats["stores"].astype(int),
        "gold":           stats["gold"].astype(int),
        "silver":         stats["silver"].astype(int),
        "bronze":         stats["bronze"].astype(int),
        "avg_seg_score":  stats["avg_seg_score"].round(2),
        "states_covered": stats["states"].astype(int),
        "max_radius_km":  stats["max_radius_km"],
    }).reset_index(drop=True)
    return catalog


def _print_summary(catalog: pd.DataFrame) -> None:
    """Print human-readable CEDI summary to stdout."""
    print("\n" + "=" * 70)
    print("PROPOSED CEDI NETWORK")
    print("=" * 70)
    for _, row in catalog.iterrows():
        print(f"\n  {row['warehouse_name']}")
        print(f"    Centroid (lat, lon)  : {row['lat']}, {row['lon']}")
        print(f"    Stores served        : {row['stores_served']}")
        print(f"    Max coverage radius  : {row['max_radius_km']} km")
        print(f"    Segment mix          : {row['gold']} gold | "
              f"{row['silver']} silver | {row['bronze']} bronze")
        print(f"    Avg segment score    : {row['avg_seg_score']:.2f} / 3.00")
        print(f"    States covered       : {row['states_covered']}")


# ── Visualization ─────────────────────────────────────────────────────────────

def _plot_results(df: pd.DataFrame, stats: pd.DataFrame,
                  centroids: np.ndarray, best_k: int,
                  inertias: list, silhouettes: list,
                  output_path: str) -> None:
    """Render 4-panel dashboard and save to PNG."""
    fig = plt.figure(figsize=(20, 14))
    fig.patch.set_facecolor("#F7F6F2")
    gs = GridSpec(3, 3, figure=fig, hspace=0.38, wspace=0.32)

    ax_map   = fig.add_subplot(gs[:2, :2])
    ax_elbow = fig.add_subplot(gs[0, 2])
    ax_sil   = fig.add_subplot(gs[1, 2])
    ax_bar   = fig.add_subplot(gs[2, :])

    for ax in [ax_map, ax_elbow, ax_sil, ax_bar]:
        ax.set_facecolor("#FAFAF8")
        for sp in ax.spines.values():
            sp.set_edgecolor("#DDDBCF")

    # — Map —
    cluster_col = "cluster" if "cluster" in df.columns else (
        df["warehouse_id"] - 1 if "warehouse_id" in df.columns else None
    )
    plot_df = df.copy()
    if "cluster" not in plot_df.columns and "warehouse_id" in plot_df.columns:
        plot_df["cluster"] = plot_df["warehouse_id"] - 1

    for c in range(best_k):
        sub = plot_df[plot_df["cluster"] == c]
        col = PALETTE[c % len(PALETTE)]
        for brand, marker in BRAND_MARKERS.items():
            b = sub[sub["brand"] == brand]
            if not b.empty:
                ax_map.scatter(b["lon"], b["lat"], c=col, marker=marker,
                               s=28, alpha=0.72, linewidths=0, zorder=3)

    for c in range(best_k):
        ax_map.scatter(centroids[c, 1], centroids[c, 0],
                       c=PALETTE[c % len(PALETTE)], marker="*",
                       s=320, edgecolors="white", linewidths=1.2, zorder=6)
        ax_map.annotate(
            f"CEDI {c + 1}", (centroids[c, 1], centroids[c, 0]),
            xytext=(5, 5), textcoords="offset points",
            fontsize=7.5, fontweight="bold", color=PALETTE[c % len(PALETTE)],
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                      edgecolor=PALETTE[c % len(PALETTE)], alpha=0.85, linewidth=0.8),
        )

    ax_map.set_xlim(-118, -86)
    ax_map.set_ylim(14, 33)
    ax_map.set_title(
        f"Geographic clustering — {best_k} proposed CEDIs\n"
        "★ = optimal CEDI location  •  ○ Walmart  □ Soriana  △ Chedraui",
        fontsize=11, fontweight="bold", pad=10, color="#2C2C2A",
    )
    ax_map.set_xlabel("Longitude", fontsize=9, color="#5F5E5A")
    ax_map.set_ylabel("Latitude",  fontsize=9, color="#5F5E5A")
    ax_map.tick_params(labelsize=8, colors="#888780")
    ax_map.grid(True, linestyle="--", alpha=0.35, color="#CCCAC0")
    ax_map.legend(
        handles=[mpatches.Patch(color=PALETTE[i], label=f"Cluster {i + 1}")
                 for i in range(best_k)],
        fontsize=7.5, ncol=2, loc="lower left",
        framealpha=0.9, edgecolor="#CCCAC0",
    )

    # — Elbow —
    k_vals = list(K_RANGE)
    ax_elbow.plot(k_vals, inertias, "o-", color="#3266AD", linewidth=2, markersize=6)
    ax_elbow.axvline(best_k, color="#E05C2F", linestyle="--", linewidth=1.5, alpha=0.8)
    ax_elbow.set_title("Elbow method", fontsize=10, fontweight="bold", color="#2C2C2A")
    ax_elbow.set_xlabel("Number of clusters (k)", fontsize=8.5, color="#5F5E5A")
    ax_elbow.set_ylabel("Inertia", fontsize=8.5, color="#5F5E5A")
    ax_elbow.tick_params(labelsize=8, colors="#888780")
    ax_elbow.grid(True, linestyle="--", alpha=0.35, color="#CCCAC0")
    ax_elbow.annotate(f"k={best_k}", (best_k, inertias[best_k - 3]),
                      xytext=(8, 8), textcoords="offset points",
                      fontsize=8, color="#E05C2F", fontweight="bold")

    # — Silhouette —
    ax_sil.plot(k_vals, silhouettes, "s-", color="#2DA875", linewidth=2, markersize=6)
    ax_sil.axvline(best_k, color="#E05C2F", linestyle="--", linewidth=1.5, alpha=0.8)
    ax_sil.set_title("Silhouette score", fontsize=10, fontweight="bold", color="#2C2C2A")
    ax_sil.set_xlabel("Number of clusters (k)", fontsize=8.5, color="#5F5E5A")
    ax_sil.set_ylabel("Silhouette score", fontsize=8.5, color="#5F5E5A")
    ax_sil.tick_params(labelsize=8, colors="#888780")
    ax_sil.grid(True, linestyle="--", alpha=0.35, color="#CCCAC0")
    ax_sil.annotate(f"k={best_k}", (best_k, silhouettes[best_k - 3]),
                    xytext=(8, -14), textcoords="offset points",
                    fontsize=8, color="#E05C2F", fontweight="bold")

    # — Stacked bar —
    x = np.arange(best_k)
    w = 0.6
    ax_bar.bar(x, stats["gold"],   width=w, label="Gold",   color="#E8A020")
    ax_bar.bar(x, stats["silver"], width=w, label="Silver",
               bottom=stats["gold"], color="#888780")
    ax_bar.bar(x, stats["bronze"], width=w, label="Bronze",
               bottom=stats["gold"] + stats["silver"], color="#C27A2B")

    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(
        [f"CEDI {i + 1}\n{stats.loc[i, 'stores']} stores\n{stats.loc[i, 'main_city']}"
         for i in range(best_k)],
        fontsize=7.5, color="#444441",
    )
    ax_bar.set_title("Customer segment composition per CEDI",
                     fontsize=10, fontweight="bold", color="#2C2C2A", pad=8)
    ax_bar.set_ylabel("Number of stores", fontsize=8.5, color="#5F5E5A")
    ax_bar.tick_params(axis="y", labelsize=8, colors="#888780")
    ax_bar.legend(fontsize=8.5, framealpha=0.9, edgecolor="#CCCAC0")
    ax_bar.grid(True, axis="y", linestyle="--", alpha=0.35, color="#CCCAC0")
    ax_bar.set_facecolor("#FAFAF8")

    for i, row in stats.iterrows():
        ax_bar.text(i, row["stores"] + 0.5, str(int(row["stores"])),
                    ha="center", va="bottom", fontsize=8,
                    fontweight="bold", color="#2C2C2A")

    plt.suptitle(
        "K-Means model — CEDI network optimization · Walmart / Soriana / Chedraui",
        fontsize=13, fontweight="bold", y=0.99, color="#2C2C2A",
    )
    plt.savefig(output_path, dpi=160, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"[plot]    Chart saved → {output_path}")


# ── Public API ────────────────────────────────────────────────────────────────

def run_clustering(
    df: pd.DataFrame,
    output_dir: str | None = None,
    save_plot: bool = True
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run the full Warehouse clustering pipeline on an in-memory DataFrame.

    Parameters
    ──────────
    df          : pd.DataFrame
        Store-level data. Required columns:
        lat, lon, name, brand, city, state, segment.
        Any extra columns are preserved in the returned store DataFrame.

    output_dir  : str | None
        If provided, CSVs and the PNG chart are written there.
        If None, no files are written to disk.

    save_plot   : bool
        Whether to render and save the 4-panel dashboard PNG.
        Only used when output_dir is not None.

    Returns
    ───────
    df_stores : pd.DataFrame
        Original data + 'warehouse_id', 'cedi_lat', 'cedi_lon' columns.

    df_warehouses : pd.DataFrame
        Warehouse catalog with columns:
        warehouse_id, warehouse_name, lat, lon, stores_served,
        gold, silver, bronze, avg_seg_score, states_covered, max_radius_km.
    """
    # 1. Clean & validate
    clean_df = _validate_and_filter(df)
    coords   = clean_df[["lat", "lon"]].values

    # 2. Find optimal k
    best_k, inertias, silhouettes = _find_optimal_k(coords)

    # 3. Fit clusters
    clustered_df, centroids = _fit_clusters(clean_df, coords, best_k)

    # 4. Build per-cluster stats (internal, used for catalog + plot)
    stats = _build_cluster_stats(clustered_df, centroids)

    # 5. Build the two output DataFrames
    df_stores = _build_store_df(clustered_df, centroids, stats)
    df_warehouses = _build_warehouse_catalog(stats)

    # 6. Console summary
    _print_summary(df_warehouses)

    # 7. Optional: persist outputs
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)

        stores_path    = os.path.join(output_dir, "customer_warehouse_assignment.csv")
        warehouses_path = os.path.join(output_dir, "warehouse_catalog.csv")
        df_stores.to_csv(stores_path, index=False)
        df_warehouses.to_csv(warehouses_path, index=False)
        print(f"[export]  Store assignments  → {stores_path}")
        print(f"[export]  Warehouse catalog  → {warehouses_path}")

        if save_plot:
            plot_path = os.path.join(output_dir, "warehouse_clustering.png")
            _plot_results(clustered_df, stats, centroids,
                          best_k, inertias, silhouettes, plot_path)

    return df_stores, df_warehouses
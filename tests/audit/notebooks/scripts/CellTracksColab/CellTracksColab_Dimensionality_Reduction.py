"""Click script and oracle of CellTracksColab_Dimensionality_Reduction.ipynb (UMAP and t-SNE of the track metrics, HDBSCAN clusters, fingerprints, plots, exemplar tracks).

Data: the CellTracksColab tables of scripts/_ctc.py: 48 tracks whose numeric metrics (mean speed, ...) differ by condition (Control about 1.0, Mutant about 2.0, 3 % noise), so the true
clusters are the two conditions. Clicks: the loading cell, then HDBSCAN with min_samples 5 and min_cluster_size 10 (the defaults, 20 and 200, exceed the 48 tracks of this small dataset and would label everything noise), then every button once with the defaults (metrics selection with all metrics, UMAP, HDBSCAN, plots, exemplars; the same for t-SNE).
HUMAN: cells 31 and 33 (find / export the exemplar tracks on the raw video) need a raw video that does not exist for this dataset.
Oracle: the saved merged_Tracks has a Cluster_UMAP and a Cluster_tsne column whose clusters (noise label -1 excluded) are pure: each holds tracks of one condition only, with at least 2 clusters.
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _ctc import files_rows, load_stage, make_dataset  # noqa: E402

AUTO_DRIVE_ALL = True
AUTO_TICK = ("Mean Speed", "Total Distance Traveled")  # the plot cells need variables ticked, as a user would
AFTER_CELL = {7: "load", 16: "hdbscan", 40: "hdbscan"}
STAGES = {
    "load": load_stage(
        {
            "Data_Dims_widget": "2D",
            "Track_table_widget": "I['track_table']",
            "Spot_table_widget": "I['spot_table']",
            "Results_Folder_widget": "I['results']",
        }
    )
}
STAGES["hdbscan"] = (
    "lcnb.set_value(lcnb.find(var='min_samples_widget'), 5)\nlcnb.set_value(lcnb.find(var='min_cluster_size_widget'), 10)\nlcnb.auto_drive('hdbscan')\n"
)
HUMAN_CELLS = {
    31: "needs the raw video of the experiment (Video path widget) to overlay the exemplar tracks: no video exists for the synthetic tracks",
    33: "exports movies of the exemplar tracks from the raw video chosen in cell 31",
}
_DATA: dict[str, Any] = {}


def inputs(ctx: Any) -> dict[str, Any]:
    _DATA.update(make_dataset(ctx.work, "2D", "custom"))
    return dict(_DATA)


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    import pandas as pd

    results = Path(_DATA["results"])
    path = results / "merged_Tracks.csv.gz"
    if not path.is_file():
        return [("tracks_file", "FAIL", "%s was not written" % path)]
    tracks = pd.read_csv(path, low_memory=False)
    rows = []
    for column in ("Cluster_UMAP", "Cluster_tsne"):
        if column not in tracks.columns:
            rows.append(
                (
                    "pure_clusters_" + column,
                    "FAIL",
                    "column %s is not in %s (columns: %s)" % (column, path.name, list(tracks.columns)[-8:]),
                )
            )
            continue
        clusters = tracks[tracks[column] != -1].groupby(column)["Condition"].nunique()
        rows.append(
            (
                "pure_clusters_" + column,
                "PASS" if len(clusters) >= 2 and (clusters == 1).all() else "FAIL",
                "%s: %d clusters, conditions per cluster %s (noise label -1 excluded)"
                % (column, len(clusters), clusters.to_dict()),
            )
        )
    return rows + files_rows(results, {"Umap/*": 1}, "files")

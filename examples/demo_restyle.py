"""Before/after: ordinary seaborn and matplotlib figures, restyled afterwards."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

import cogra


def make_figure():
    plt.rcdefaults()
    sns.set_theme()  # a typical user's default look
    rng = np.random.default_rng(2)
    n = 40
    df = pd.DataFrame(
        {
            "load": np.tile(np.arange(1, 7), n * 2),
            "cond": np.repeat(["feature", "conjunction"], 6 * n),
        }
    )
    df["rt"] = 400 + 35 * df["load"] + np.where(df.cond == "conjunction", 40, 0) + rng.normal(0, 60, len(df))
    sc = pd.DataFrame({"go": rng.normal(500, 60, 200)})
    sc["ssrt"] = 0.3 * sc.go + rng.normal(60, 20, 200)
    sc["acc"] = rng.uniform(0.6, 1, 200)
    hm = pd.DataFrame(rng.normal(0, 1, (6, 8)).cumsum(axis=1), index=[f"S{i}" for i in range(1, 7)])

    fig, axs = plt.subplots(2, 3, figsize=(11, 6.4))
    sns.lineplot(df, x="load", y="rt", hue="cond", style=None, marker="o", ax=axs[0, 0])
    sns.barplot(df[df.load.isin([2, 4, 6])], x="load", y="rt", hue="cond", ax=axs[0, 1])
    sns.kdeplot(df, x="rt", hue="cond", fill=True, ax=axs[0, 2])
    s = axs[1, 0].scatter(sc.go, sc.ssrt, c=sc.acc, cmap="viridis", s=18)
    fig.colorbar(s, ax=axs[1, 0], label="Accuracy")
    axs[1, 0].set(xlabel="go RT", ylabel="SSRT")
    sns.violinplot(df[df.load.isin([2, 6])], x="load", y="rt", hue="cond", ax=axs[1, 1])
    sns.heatmap(hm, ax=axs[1, 2], cmap="mako")
    fig.suptitle("Illustrative values only")
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    f = make_figure()
    f.savefig("restyle-before.png", dpi=130)
    plt.close(f)
    f = make_figure() | cogra.cogra()
    f.savefig("restyle-after.png", dpi=130)
    cogra.save_vintage(f, "restyle-after-scan.png", look="scan", dpi=450, scan_dpi=200)
    for k, v in f.cogra_report.items():
        print(k)
        [print("  ", x) for x in v]

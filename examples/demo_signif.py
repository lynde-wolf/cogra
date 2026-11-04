"""Significance brackets: on cogra.bars, and on a seaborn figure restyled afterwards.

    python examples/demo_signif.py      # writes signif-clean.png and signif-scan.png

Illustrative values only, not data.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

import cogra


def make_figure():
    cogra.use()
    rng = np.random.default_rng(7)
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 3.0), gridspec_kw={"width_ratios": [1, 1.25]})

    # (a) cogra.bars: stars, a bracket that clears the middle bar, and an APA-style p
    cogra.bars(a, [0, 1, 2], [212, 236, 251], yerr=[8, 9, 11])
    a.set_xticks([0, 1, 2], ["Simple", "Feature", "Conjunction"])
    a.set(ylabel="SSRT (msec)", ylim=(0, 300))
    cogra.signif(a, 0, 1, p=0.03)  # *
    cogra.signif(a, 1, 2, p=0.21, ns=True)  # n.s.
    cogra.signif(a, 0, 2, p=0.0004, show="p")  # p < .001, above the other two

    # (b) seaborn in colour, a test per block, then restyle
    df = pd.DataFrame(
        {
            "block": np.tile(np.repeat(["1", "2", "3"], 20), 2),
            "cond": np.repeat(["Feature", "Conjunction"], 60),
        }
    )
    cost = np.where(df.cond == "Conjunction", df.block.map({"1": 40, "2": 25, "3": 6}), 0)  # shrinks by block
    df["ssrt"] = 240 + cost + rng.normal(0, 30, len(df))
    sns.barplot(df, x="block", y="ssrt", hue="cond", palette="deep", capsize=0.2, ax=b)
    b.set(xlabel="Block", ylabel="SSRT (msec)", ylim=(0, 300))
    b.legend(title=None, loc="lower center", ncols=2, bbox_to_anchor=(0.5, 1.02))
    for k, blk in enumerate(["1", "2", "3"]):
        g = df[df.block == blk]
        p = stats.ttest_ind(g[g.cond == "Feature"].ssrt, g[g.cond == "Conjunction"].ssrt).pvalue
        cogra.signif(b, k - 0.2, k + 0.2, p=p, ns=True)  # dodged bars sit at x +/- 0.2
    cogra.restyle(fig)
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    fig = make_figure()
    fig.savefig("signif-clean.png", dpi=200)
    cogra.save_vintage(fig, "signif-scan.png")
    print("ok")

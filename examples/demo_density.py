import matplotlib.pyplot as plt
import numpy as np

import cogra

cogra.use()
rng = np.random.default_rng(11)
# Illustrative: two overlapping clusters, not data
a = rng.multivariate_normal([470, 215], [[2200, 520], [520, 420]], 260)
b = rng.multivariate_normal([590, 255], [[2600, -300], [-300, 520]], 140)
d = np.vstack([a, b])
fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.1), sharey=True, gridspec_kw={"wspace": 0.12})
cogra.density_topo(axs[0], d[:, 0], d[:, 1])
cogra.density_topo(axs[1], d[:, 0], d[:, 1], points="outside")
for ax, t in zip(axs, ("All points", "Points outside 90% only")):
    ax.set_xlabel("Mean go RT (msec)")
    ax.set_title(t, fontsize=9)
axs[0].set_ylabel("SSRT (msec)")
fig.text(
    0.5,
    -0.1,
    "Illustrative values only. Contours enclose 10% to 90% of the estimated density;\nlabelled lines enclose 50% and 90%.",
    ha="center",
    fontsize=7,
)
fig.savefig("density-clean.png", dpi=200)
cogra.save_vintage(fig, "density-scan.png", look="scan")
print("ok")

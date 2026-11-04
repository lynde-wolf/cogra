import matplotlib.pyplot as plt
import numpy as np

import cogra

cogra.use()
rng = np.random.default_rng(4)
# Illustrative ex-Gaussian RTs (msec), not data
feat = rng.normal(420, 45, 120) + rng.exponential(80, 120)
conj = rng.normal(455, 50, 120) + rng.exponential(100, 120)

# Electrode layout: rings on the unit circle, nose at +y. Synthetic field.
pts = [(0, 0)]
for r, n in ((0.33, 8), (0.62, 14), (0.9, 20)):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False) + (0.2 if n == 14 else 0)
    pts += list(zip(r * np.sin(a), r * np.cos(a)))
xy = np.array(pts)
field = (
    4.2 * np.exp(-((xy[:, 0]) ** 2 + (xy[:, 1] - 0.25) ** 2) / 0.12)
    - 3.1 * np.exp(-((xy[:, 0] + 0.35) ** 2 + (xy[:, 1] + 0.55) ** 2) / 0.10)
    - 2.6 * np.exp(-((xy[:, 0] - 0.4) ** 2 + (xy[:, 1] + 0.5) ** 2) / 0.10)
)

fig, axs = plt.subplots(
    1, 3, figsize=(8.4, 3.2), gridspec_kw={"wspace": 0.4, "width_ratios": [1, 1.15, 1.45]}
)
cogra.violin(axs[0], [feat, conj])
axs[0].set_xticks([0, 1], ["Feature", "Conj."])
axs[0].set_ylabel("RT (msec)")
cogra.raincloud(axs[1], [feat, conj])
axs[1].set_xticks([0, 1], ["Feature", "Conj."])
axs[1].set_xlim(-0.45, 1.6)
cs = cogra.topoplot(axs[2], xy, field)
axs[2].text(0, -1.3, "Amplitude ($\\mu$V)", ha="center", fontsize=8)
for ax, t in zip(axs, "ABC"):
    ax.text(-0.18, 1.04, t, transform=ax.transAxes, fontsize=11, fontweight="bold")
fig.text(0.5, -0.1, "Illustrative values only.", ha="center", fontsize=8)
fig.savefig("modern-clean.png", dpi=200)
cogra.save_vintage(fig, "modern-scan.png", look="scan")
print("ok")

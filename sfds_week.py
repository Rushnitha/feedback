import numpy as np
import seaborn as sns
import matplotlib.pyplot as plot

sns=set(style="whitegrid")

data=np.array([45,50,60,52,48,58,62,47,53,65,70,42,38,57])

sns.histplot(data,bins=10,kde=True,colore="orange")
plt.xlabel("values")
plt.ylable("Density")
plt.title("Stastical plot using seaborn")

plt.show()
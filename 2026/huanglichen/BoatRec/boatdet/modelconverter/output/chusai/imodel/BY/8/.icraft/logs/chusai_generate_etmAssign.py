import matplotlib.pyplot as plt

success = [[16, 5, 6, 0, 3276800, 0], 
[57, 15, 16, 0, 3276800, 0], 
[437, 25, 155, 0, 3276800, 0], 
[51, 11, 15, 3276800, 5734400, 0], 
[28, 7, 13, 0, 1638400, 0], 
[92, 21, 25, 3276800, 4505600, 0], 
[361, 42, 137, 3276800, 4505600, 0], 
[502, 166, 170, 0, 1228800, 0], 
[508, 170, 268, 1228800, 2048000, 0], 
[2354, 91, 92, 4505600, 5171200, 0], 
[307, 91, 93, 5171200, 5836800, 0], 
[2358, 218, 219, 0, 665600, 0], 
[644, 218, 220, 2048000, 2713600, 0], 
[169, 38, 42, 4505600, 5120000, 0], 
[426, 148, 152, 3276800, 3891200, 0], 
[517, 152, 173, 3891200, 4505600, 0], 
[582, 184, 188, 0, 614400, 0], 
[38, 9, 10, 1638400, 2048000, 0], 
[267, 60, 65, 4505600, 4915200, 0], 
[492, 163, 166, 1228800, 1638400, 0], 
[246, 55, 59, 4505600, 4812800, 0], 
[597, 134, 191, 4505600, 4812800, 0], 
[688, 258, 262, 0, 307200, 0], 
[159, 35, 38, 3276800, 3481600, 0], 
[350, 131, 134, 4812800, 5017600, 0], 
[416, 145, 148, 3891200, 4096000, 0], 
[572, 181, 184, 614400, 819200, 0], 
[603, 191, 260, 665600, 870400, 0], 
[694, 262, 284, 307200, 512000, 0], 
[236, 52, 55, 4812800, 4915200, 0], 
[3576, 79, 87, 4505600, 4558848, 0], 
[3582, 206, 214, 870400, 923648, 0], 
[302, 85, 90, 4558848, 4610048, 0], 
[639, 212, 217, 923648, 974848, 0], 
[836, 284, 285, 0, 12800, 0], 
[842, 285, 286, 12800, 25600, 0], 
]

end_time = max(success, key=lambda row: row[2])[2]
plt.figure(figsize=(15, 8))
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.ticklabel_format(style='plain', axis='y')

cmap = plt.get_cmap('tab20')

for i in range(end_time):
    for idx, slice in enumerate(success):
        if i <= slice[2] and i >= slice[1]:
            plt.bar(x=i + 0.5, bottom=slice[3], height=slice[4] - slice[3], width=1,
                    color=cmap(idx % 20), edgecolor='black', alpha=0.7)
            plt.text(x=i + 0.6, y=(slice[4] + slice[3]) / 2, s=str(slice[0]),
                     ha='center', va='center', rotation=90)

plt.xlabel('时间')
plt.ylabel('ETM空间')
plt.axhline(y=5836800, color='red', linewidth=1, linestyle='--')
plt.text(x=10, y=5.89517e+06, color='red', s='ETM FTMP total_consumption : ' + str(5836800))
plt.grid(True, which='both', linestyle='--', linewidth=0.5)

plt.tight_layout()
plt.show()

# ETM FTMP total_consumption is 5836800
# ETM FTMP org_total_consumption is 45564992

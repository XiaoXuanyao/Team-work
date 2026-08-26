import matplotlib.pyplot as plt

success = [[16, 3, 4, 0, 3276800, 0], 
[57, 13, 14, 0, 3276800, 0], 
[437, 23, 153, 0, 3276800, 0], 
[51, 9, 13, 3276800, 5734400, 0], 
[28, 5, 11, 0, 1638400, 0], 
[1474, 263, 265, 0, 1638400, 0], 
[92, 19, 23, 3276800, 4505600, 0], 
[361, 40, 135, 3276800, 4505600, 0], 
[502, 164, 168, 0, 1228800, 0], 
[508, 168, 267, 1638400, 2457600, 0], 
[712, 263, 264, 2457600, 3276800, 0], 
[2373, 89, 90, 4505600, 5171200, 0], 
[307, 89, 91, 5171200, 5836800, 0], 
[2377, 216, 217, 0, 665600, 0], 
[644, 216, 218, 665600, 1331200, 0], 
[169, 36, 40, 4505600, 5120000, 0], 
[426, 146, 150, 3276800, 3891200, 0], 
[517, 150, 171, 3891200, 4505600, 0], 
[582, 182, 186, 0, 614400, 0], 
[38, 7, 8, 1638400, 2048000, 0], 
[267, 58, 63, 4505600, 4915200, 0], 
[492, 161, 164, 1228800, 1638400, 0], 
[588, 186, 277, 3276800, 3686400, 0], 
[1476, 268, 270, 0, 409600, 0], 
[1478, 273, 275, 0, 409600, 0], 
[246, 53, 57, 4505600, 4812800, 0], 
[597, 132, 189, 4505600, 4812800, 0], 
[688, 256, 260, 2457600, 2764800, 0], 
[159, 33, 36, 3276800, 3481600, 0], 
[350, 129, 132, 4812800, 5017600, 0], 
[416, 143, 146, 3891200, 4096000, 0], 
[572, 179, 182, 614400, 819200, 0], 
[694, 260, 286, 3686400, 3891200, 0], 
[738, 268, 269, 409600, 614400, 0], 
[764, 273, 274, 409600, 614400, 0], 
[236, 50, 53, 4812800, 4915200, 0], 
[1480, 278, 280, 0, 102400, 0], 
[790, 278, 279, 102400, 153600, 0], 
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
# ETM FTMP org_total_consumption is 49945600

import matplotlib
from datetime import datetime
import matplotlib.pyplot as plt
import csv
import os
import fnmatch

x, y, z, s, ir, iw, csv_files = ([] for i in range(7))

for root, dirs, files in os.walk('/Users/nahmed/Python/load_with_vscout/'):
    csv_files += fnmatch.filter(files, '*.csv')

print csv_files, len(csv_files)

plt.rcParams.update({'font.size': 7,'font.family': 'monospace','font.variant':'normal'})
plt.rcParams['lines.linewidth'] = 1
time_format = matplotlib.dates.DateFormatter('%H:%M:%S')
plt.figure(figsize=(8, 2), dpi=600)

for f in csv_files:
    del x[:]
    del y[:]
    del z[:]
    del s[:]
    del ir[:]
    del iw[:]
    with open('load_with_vscout/' + f,'r') as csvfile:
        plots = csv.reader(csvfile, delimiter=',')
        ncol=len(next(plots))
        print str(ncol) +'->'+ f
        for row in plots:
            x.append(datetime.fromtimestamp(float(row[0])))
            if ncol == 23:
                y.append(row[3])
                z.append(row[8])
                s.append(row[13])
            elif ncol == 27:
                y.append(row[3])
                z.append(row[12])
                s.append(row[17])
            elif ncol == 11:
                y.append(row[2])
                z.append(row[3])

    plt.gca().xaxis.set_major_formatter(time_format)
    plt.plot(x,y, label='CPU %')
    plt.plot(x,z, label='MEM %')
    if len(s) is not 0:
        plt.plot(x,s, label='SWAP %')
    plt.xlabel('Time')
    plt.grid(True)
    if len(s) is not 0:
        plt.ylabel('CPU/MEM/SWAP %', fontweight='normal')
        plt.title(os.path.splitext(f)[0].split('.')[0] + ' - System Usage(w/NetScout)', fontweight='normal')
    else:
        plt.ylabel('CPU/MEM %', fontweight='normal')
        plt.title(os.path.splitext(f)[0].split('.')[0] + ' - NetScout Usage', fontweight='normal')
    plt.autoscale(enable=True, axis='y')
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=3, fancybox=True, shadow=True, prop={'weight':'normal'}) #framealpha=0.5
    plt.subplots_adjust(bottom=.1,left=.125)
    plt.savefig('load_with_vscout/'+os.path.splitext(f)[0] +'.png', bbox_inches='tight', transparent=False)
    plt.clf()

#!/usr/bin/env python

'''
    File name: main_ripp_mod.py
    Author: Guillaume Viejo
    Date created: 16/08/2017    
    Python Version: 3.5.2

Sharp-waves ripples modulation 
Used to make figure 1,2

'''

import numpy as np
import pandas as pd
# from matplotlib.pyplot import plot,show,draw
import scipy.io
from functions import *
from pylab import *
from sklearn.decomposition import PCA
import _pickle as cPickle

###############################################################################################################
# LOADING DATA
###############################################################################################################
data_directory 	= '/mnt/DataGuillaume/MergedData/'
datasets 		= np.loadtxt(data_directory+'datasets_ThalHpc.list', delimiter = '\n', dtype = str, comments = '#')

theta_mod, theta_ses 	= loadThetaMod('/mnt/DataGuillaume/MergedData/THETA_THAL_mod.pickle', datasets, return_index=True)
swr_mod, swr_ses 		= loadSWRMod('/mnt/DataGuillaume/MergedData/SWR_THAL_corr.pickle', datasets, return_index=True)
spind_mod, spind_ses 	= loadSpindMod('/mnt/DataGuillaume/MergedData/SPINDLE_mod.pickle', datasets, return_index=True)

swr 					= pd.DataFrame(	index = swr_ses, 
										columns = np.arange(-500, 505, 5),
										data = swr_mod)

phase 					= pd.DataFrame(index = theta_ses['wake'], columns = ['theta_wake', 'theta_rem', 'spindle_hpc', 'spindle_thl'])
phase.loc[theta_ses['wake'],'theta_wake'] = theta_mod['wake'][:,0]
phase.loc[theta_ses['rem'], 'theta_rem'] = theta_mod['rem'][:,0]
phase.loc[spind_ses['hpc'], 'spindle_hpc'] = spind_mod['hpc'][:,0]
phase.loc[spind_ses['thl'], 'spindle_thl'] = spind_mod['thl'][:,0]

pvalue 					= pd.DataFrame(index = theta_ses['wake'], columns = ['theta_wake', 'theta_rem', 'spindle_hpc', 'spindle_thl'])
pvalue.loc[theta_ses['wake'], 'theta_wake'] = theta_mod['wake'][:,1]
pvalue.loc[theta_ses['rem'], 'theta_rem'] = theta_mod['rem'][:,1]
pvalue.loc[spind_ses['hpc'], 'spindle_hpc'] = spind_mod['hpc'][:,1]
pvalue.loc[spind_ses['thl'], 'spindle_thl'] = spind_mod['thl'][:,1]

kappa 					= pd.DataFrame(index = theta_ses['wake'], columns = ['theta_wake', 'theta_rem', 'spindle_hpc', 'spindle_thl'])
kappa.loc[theta_ses['wake'], 'theta_wake'] = theta_mod['wake'][:,2]
kappa.loc[theta_ses['rem'], 'theta_rem'] = theta_mod['rem'][:,2]
kappa.loc[spind_ses['hpc'], 'spindle_hpc'] = spind_mod['hpc'][:,2]
kappa.loc[spind_ses['thl'], 'spindle_thl'] = spind_mod['thl'][:,2]

# filtering swr_mod
swr 				= pd.DataFrame(	index = swr.index, 
									columns = swr.columns,
									data = gaussFilt(swr.values, (10,)))


# CHECK FOR NAN
tmp1 			= swr.index[np.unique(np.where(np.isnan(swr))[0])]
tmp2 			= phase.index[phase.isnull().any(1)]
# CHECK P-VALUE 
tmp3	 		= pvalue.index[(pvalue['theta_rem'] > 0.1).values]
tmp 			= np.unique(np.concatenate([tmp1,tmp2,tmp3]))
# copy and delete 
if len(tmp):
	swr_modth 	= swr.drop(tmp)
	theta_modth = np.zeros((len(swr_modth),3))	
	theta_modth[:,0] = phase.loc[swr_modth.index,	'theta_rem']
	theta_modth[:,1] = pvalue.loc[swr_modth.index,	'theta_rem']
	theta_modth[:,2] = kappa.loc[swr_modth.index,	'theta_rem']


neuron_index = swr_modth.index
swr_modth = swr_modth.values


###############################################################################################################
# PCA
###############################################################################################################
n = 6
pca = PCA(n_components = n)
zpca = pca.fit_transform(swr_modth)
pc = zpca[:,0:2]
eigen = pca.components_

phi = np.mod(np.arctan2(zpca[:,1], zpca[:,0]), 2*np.pi)

times = np.arange(0, 1005, 5) - 500 # BAD

###############################################################################################################
# jPCA
###############################################################################################################
from scipy.sparse import lil_matrix

X = pca.components_.transpose()
dX = np.hstack([np.vstack(derivative(times, X[:,i])) for i in range(X.shape[1])])
#build the H mapping for a given n
# work by lines but H is made for column based
n = X.shape[1]
H = buildHMap(n)
# X tilde
Xtilde = np.zeros( (X.shape[0]*X.shape[1], X.shape[1]*X.shape[1]) )
for i, j in zip( (np.arange(0,n**2,n) ), np.arange(0, n*X.shape[0], X.shape[0]) ):
	Xtilde[j:j+X.shape[0],i:i+X.shape[1]] = X
# put dx in columns
dXv = np.vstack(dX.transpose().reshape(X.shape[0]*X.shape[1]))
# multiply Xtilde by H
XtH = np.dot(Xtilde, H)
# solve XtH k = dXv
k, residuals, rank, s = np.linalg.lstsq(XtH, dXv)
# multiply by H to get m then M
m = np.dot(H, k)
Mskew = m.reshape(n,n).transpose()
# Contruct the two vectors for projection with MSKEW
evalues, evectors = np.linalg.eig(Mskew)
# index = np.argsort(evalues).reshape(5,2)[:,1]
index = np.argsort(np.array([np.linalg.norm(i) for i in evalues]).reshape(int(n/2),2)[:,0])
evectors = evectors.transpose().reshape(int(n/2),2,n)
u = np.vstack([
				np.real(evectors[index[-1]][0] + evectors[index[-1]][1]),
				np.imag(evectors[index[-1]][0] - evectors[index[-1]][1])
			]).transpose()
# PRoject X
rX = np.dot(X, u)
rX = rX*-1.0
score = np.dot(swr_modth, rX)
phi2 = np.mod(np.arctan2(score[:,1], score[:,0]), 2*np.pi)
# Construct the two vectors for projection with MSYM
Msym = np.copy(Mskew)
Msym[np.triu_indices(n)] *= -1.0
evalues2, evectors2 = np.linalg.eig(Msym)
v = evectors2[:,0:2]
rY = np.dot(X, v)
score2 = np.dot(swr_modth, rY)
phi3 = np.mod(np.arctan2(score2[:,1], score2[:,0]), 2*np.pi)

dynamical_system = {	'x'		:	X,
						'dx'	:	dX,
						'Mskew'	:	Mskew,
						'Msym'	:	Msym,
						'times'	:	times 	}

# import _pickle as cPickle
# cPickle.dump(dynamical_system, open('../data/dynamical_system.pickle', 'wb'))

###############################################################################################################
# CROSS-VALIDATION
###############################################################################################################
# scorecv, phicv = crossValidation(swr_modth, times, n_cv = 5, dims = (6,2))

###############################################################################################################
# QUARTILES OF THETA FORCES MODULATION
###############################################################################################################
force = theta_modth[:,2]
index = np.argsort(force)
swr_modth_sorted = swr_modth[index,:]
theta_modth_sorted = theta_modth[index,:]
scoretheta, phitheta, indextheta, jpca_theta = quartiles(swr_modth_sorted, times, n_fold = 2, dims = (6,2))

###############################################################################################################
# QUARTILES OF VARIANCE OF RIPPLE MODULATION
###############################################################################################################
variance = np.var(swr_modth, 1)
index = np.argsort(variance)
swr_modth_sorted2 = swr_modth[index,:]
theta_modth_sorted2 = theta_modth[index,:]
scorerip, phirip, indexrip, jpca_rip = quartiles(swr_modth_sorted2, times, n_fold = 2, dims = (6,2))


###############################################################################################################
# TO SAVE
###############################################################################################################
datatosave = {	'swr_modth'		:	swr_modth,
				'eigen'			:	eigen,
				'times' 		: 	times,
				'theta_modth' 	:	theta_modth,
				'phi' 			: 	phi,
				'zpca'			: 	zpca,
				'phi2' 			: 	phi2,
				'rX'			: 	rX,
				'jscore'		:	score,
				'variance'		:	variance,
				'force'			: 	force,
				'scoretheta'	:	scoretheta,
				'scorerip'		:	scorerip,
				'phitheta'		:	phitheta,
				'phirip'		:	phirip,
				'indextheta'	:	indextheta,
				'indexrip'		:	indexrip,
				'jpca_theta'	: 	jpca_theta,
				'jpca_rip'		: 	jpca_rip				
				}	

cPickle.dump(datatosave, open('../data/to_plot.pickle', 'wb'))

###############################################################################################################
# PLOT
###############################################################################################################

import matplotlib.cm as cm
########################
figure()
subplot(2,3,1)
imshow(swr_modth, aspect = 'auto')

subplot(2,3,2)
plot(times, swr_modth.transpose())

subplot(2,3,3)
plot(times, eigen[0])
plot(times, eigen[1])

subplot(2,3,4)
idxColor = np.digitize(theta_modth[:,0], np.linspace(0, 2*np.pi+0.0001, 61))
idxColor = idxColor-np.min(idxColor)
idxColor = idxColor/float(np.max(idxColor))
sizes = theta_modth[:,2] - np.min(theta_modth[:,2])
sizes = theta_modth[:,2]/float(np.max(theta_modth[:,2])) 
colors = cm.rainbow(idxColor)
scatter(zpca[:,0], zpca[:,1], s = sizes*150.+10., c = colors)

subplot(2,3,5)
# dist_cp = np.sqrt(np.sum(np.power(eigen[0] - eigen[1], 2))
theta_mod_toplot = theta_modth[:,0]#,dist_cp>0.02]
phi_toplot = phi #[dist_cp>0.02]
x = np.concatenate([theta_mod_toplot, theta_mod_toplot, theta_mod_toplot+2*np.pi, theta_mod_toplot+2*np.pi])
y = np.concatenate([phi_toplot, phi_toplot + 2*np.pi, phi_toplot, phi_toplot + 2*np.pi])
plot(x, y, 'o', markersize = 1)
xlabel('Theta phase (rad)')
ylabel('SWR PCA phase (rad)')

subplot(2,3,6)
H, xedges, yedges = np.histogram2d(y, x, 50)
H = gaussFilt(H, (3,3))
imshow(H, origin = 'lower', interpolation = 'nearest', aspect = 'auto')



#############################
figure()
subplot(2,3,1)
plot(rX[:,0], rX[:,1])

subplot(2,3,2)
plot(rX)
# axvline(idx0)
# axvline(idx1)

subplot(2,3,3)
scatter(score[:,0], score[:,1], s = 20., c = colors)

subplot(2,3,4)
theta_mod_toplot = theta_modth[:,0]#,dist_cp>0.02]
phi_toplot = phi2 #[dist_cp>0.02]
x = np.concatenate([theta_mod_toplot, theta_mod_toplot, theta_mod_toplot+2*np.pi, theta_mod_toplot+2*np.pi])
y = np.concatenate([phi_toplot, phi_toplot + 2*np.pi, phi_toplot, phi_toplot + 2*np.pi])
plot(x, y, 'o', markersize = 1)
xlabel('Theta phase (rad)')
ylabel('SWR PCA phase (rad)')

subplot(2,3,5)
H, xedges, yedges = np.histogram2d(y, x, 50)
H = gaussFilt(H, (3,3))
imshow(H, origin = 'lower', interpolation = 'nearest', aspect = 'auto')

subplot(2,3,6)
# theta_mod_toplot = theta_modth[:,0]#,dist_cp>0.02]
# phi_toplot = np.hstack(phicv)
# x = np.concatenate([theta_mod_toplot, theta_mod_toplot, theta_mod_toplot+2*np.pi, theta_mod_toplot+2*np.pi])
# y = np.concatenate([phi_toplot, phi_toplot + 2*np.pi, phi_toplot, phi_toplot + 2*np.pi])
# plot(x, y, 'o', markersize = 1)
# xlabel('Theta phase (rad)')
# ylabel('SWR PCA phase (rad)')
# title('Cross-Validation (10)')




#########################
# figure()

# subplot(2,5,1)
# tmp = []
# indexdata = np.linspace(0,len(theta_modth_sorted),4+1).astype('int')	
# for i in range(4):
# 	tmp.append(theta_modth_sorted[indexdata[i]:indexdata[i+1],0])
# theta_mod_toplot = np.array(tmp)
# phi_toplot = phiqr
# idxColor = np.arange(1,5)
# idxColor = idxColor-np.min(idxColor)
# idxColor = idxColor/float(np.max(idxColor))
# colors = cm.rainbow(idxColor)
# for i in range(len(phi_toplot)):
# 	x = np.concatenate([theta_mod_toplot[i], theta_mod_toplot[i], theta_mod_toplot[i]+2*np.pi, theta_mod_toplot[i]+2*np.pi])
# 	y = np.concatenate([phi_toplot[i], phi_toplot[i] + 2*np.pi, phi_toplot[i], phi_toplot[i] + 2*np.pi])
# 	scatter(x,y, s = 10, c = colors[i], label = str(np.round(np.mean(theta_mod_toplot[i]),2)))
# legend()
# title('Theta Modulation')

# for i in range(4):	
# 	subplot(2,5,2+i)	
# 	x = np.concatenate([theta_mod_toplot[i], theta_mod_toplot[i], theta_mod_toplot[i]+2*np.pi, theta_mod_toplot[i]+2*np.pi])
# 	y = np.concatenate([phi_toplot[i], phi_toplot[i] + 2*np.pi, phi_toplot[i], phi_toplot[i] + 2*np.pi])
# 	scatter(x,y, s = 10, c = colors[i], label = str(np.round(np.mean(theta_mod_toplot[i]),2)))	

# subplot(2,5,6)
# tmp = []
# indexdata = np.linspace(0,len(theta_modth_sorted2),4+1).astype('int')	
# for i in range(4):
# 	tmp.append(theta_modth_sorted2[indexdata[i]:indexdata[i+1],0])
# theta_mod_toplot = np.array(tmp)
# phi_toplot = phiva
# idxColor = np.arange(1,5)
# idxColor = idxColor-np.min(idxColor)
# idxColor = idxColor/float(np.max(idxColor))
# colors = cm.rainbow(idxColor)
# for i in range(len(phi_toplot)):
# 	x = np.concatenate([theta_mod_toplot[i], theta_mod_toplot[i], theta_mod_toplot[i]+2*np.pi, theta_mod_toplot[i]+2*np.pi])
# 	y = np.concatenate([phi_toplot[i], phi_toplot[i] + 2*np.pi, phi_toplot[i], phi_toplot[i] + 2*np.pi])
# 	scatter(x,y, s = 10, c = colors[i], label = str(np.round(np.mean(theta_mod_toplot[i]),2)))
# legend()
# title('Ripple Modulation')

# for i in range(4):	
# 	subplot(2,5,7+i)	
# 	x = np.concatenate([theta_mod_toplot[i], theta_mod_toplot[i], theta_mod_toplot[i]+2*np.pi, theta_mod_toplot[i]+2*np.pi])
# 	y = np.concatenate([phi_toplot[i], phi_toplot[i] + 2*np.pi, phi_toplot[i], phi_toplot[i] + 2*np.pi])
# 	scatter(x,y, s = 10, c = colors[i], label = str(np.round(np.mean(theta_mod_toplot[i]),2)))	




# # subplot(2,6,7)
# # H, xedges, yedges = np.histogram2d(y, x, 50)
# # H = gaussFilt(H, (3,3))
# # imshow(H, origin = 'lower', interpolation = 'nearest', aspect = 'auto')
# # title('Theta modulation')

# # subplot(2,6,8)
# # tmp = []
# # indexdata = np.linspace(0,len(theta_modth_sorted),4+1).astype('int')	
# # for i in range(4):
# 	tmp.append(theta_modth_sorted[indexdata[i]:indexdata[i+1],0])
# theta_mod_toplot = np.array(tmp)
# phi_toplot = phiqr
# idxColor = np.arange(1,5)
# idxColor = idxColor-np.min(idxColor)
# idxColor = idxColor/float(np.max(idxColor))
# colors = cm.rainbow(idxColor)
# for i in range(len(phi_toplot)):
# 	x = np.concatenate([theta_mod_toplot[i], theta_mod_toplot[i], theta_mod_toplot[i]+2*np.pi, theta_mod_toplot[i]+2*np.pi])
# 	y = np.concatenate([phi_toplot[i], phi_toplot[i] + 2*np.pi, phi_toplot[i], phi_toplot[i] + 2*np.pi])
# 	scatter(x,y, s = 10, c = colors[i], label = str(np.round(np.mean(theta_mod_toplot[i]),2)))
# legend()
# title('Quartiles')

# for i in range(4):	
# 	subplot(2,6,3+i)	
# 	x = np.concatenate([theta_mod_toplot[i], theta_mod_toplot[i], theta_mod_toplot[i]+2*np.pi, theta_mod_toplot[i]+2*np.pi])
# 	y = np.concatenate([phi_toplot[i], phi_toplot[i] + 2*np.pi, phi_toplot[i], phi_toplot[i] + 2*np.pi])
# 	scatter(x,y, s = 20, c = colors[i], label = str(np.round(np.mean(theta_mod_toplot[i]),2)))	


show()




























sys.exit()



subplot(2,3,1)
plot(rY[:,0], rY[:,1])

subplot(2,3,2)
plot(rY)
# axvline(idx0)
# axvline(idx1)

subplot(2,3,3)
scatter(score2[:,0], score2[:,1], s = 20., c = colors)

subplot(2,3,4)
theta_mod_toplot = theta_modth[:,0]#,dist_cp>0.02]
phi_toplot = phi3 #[dist_cp>0.02]
x = np.concatenate([theta_mod_toplot, theta_mod_toplot, theta_mod_toplot+2*np.pi, theta_mod_toplot+2*np.pi])
y = np.concatenate([phi_toplot, phi_toplot + 2*np.pi, phi_toplot, phi_toplot + 2*np.pi])
plot(x, y, 'o', markersize = 1)
xlabel('Theta phase (rad)')
ylabel('SWR PCA phase (rad)')

subplot(2,3,5)
H, xedges, yedges = np.histogram2d(y, x, 50)
H = gaussFilt(H, (3,3))
imshow(H, origin = 'lower', interpolation = 'nearest', aspect = 'auto')




# 3d plot
order = np.argsort(phi)
swr_modth = swr_modth[order]
phi = phi[order]
jet = cm = plt.get_cmap('jet') 
cNorm  = colors.Normalize(vmin=phi.min(), vmax=phi.max())
scalarMap = matplotlib.cm.ScalarMappable(norm=cNorm, cmap=jet)

fig = plt.figure()
ax = fig.add_subplot(111,projection = '3d')
tmp = np.arange(len(phi))
for idx in range(len(swr_modth)):
	line = swr_modth[idx]
	colorVal = scalarMap.to_rgba(phi[idx])
	ax.plot(times, np.ones(len(swr_modth[idx]))*tmp[idx], line, color = colorVal)

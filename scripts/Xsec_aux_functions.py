#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep 25 16:10:11 2020

@author: Manfred Brath

This file contains the functions that are needed for the harmonization of the Hitran
absorption cross section data and for the calculations of the fit coefficients.
"""
from glob import glob
from os import path

import matplotlib.patches as ptch
import matplotlib.pyplot as plt
import numpy as np
import pyarts
from matplotlib.font_manager import FontProperties
from scipy.interpolate import interp1d
from scipy.linalg import lstsq

# %% constants

# speed of light
c0 = 299792458.0  # [m/s]


# %% fit related functions


def fit_poly22(xdata, ydata, zdata):
    '''
    2d quadratic fit:
    z = p00 + p10*x + p01*y + p20*x**2 + p11*x*y + p02*y**2

    Args:
        xdata:  vector
                independent data.
        ydata:  vector
                independent data.
        zdata:  vector
                data, which depends on xdata and ydata.

    Returns:
        poly:   vector
                coefficients of fit, see above for the order.
        res:    float
                summed residuums.
        rnk:    int
                Effective rank of design matrix M.
        s:      ndarray or None
                Singular values of M.

    '''

    M = np.ones((len(xdata), 6))
    M[:, 1] = xdata  # p01
    M[:, 2] = ydata  # p01
    M[:, 3] = xdata ** 2  # p20
    M[:, 4] = xdata * ydata  # p11
    M[:, 5] = ydata ** 2  # p02

    poly, res, rnk, s = lstsq(M, zdata)

    return poly, res, rnk, s


def fit_poly11(xdata, ydata, zdata):
    '''
    2d linear fit:
    z = p00 + p10*x + p01*y

    Args:
        xdata:  vector
                independent data.
        ydata:  vector
                independent data.
        zdata:  vector
                data, which depends on xdata and ydata.

    Returns:
        poly:   vector
                coefficients of fit, see above for the order.
        res:    float
                summed residuums.
        rnk:    int
                Effective rank of design matrix M.
        s:      ndarray or None
                Singular values of M.

    '''

    M = np.ones((len(xdata), 6))
    M[:, 1] = xdata  # p01
    M[:, 2] = ydata  # p01

    poly, res, rnk, s = lstsq(M, zdata)

    return poly, res, rnk, s


def fit_poly2(xdata, zdata):
    '''
    1d quadratic fit:
    # z= p0 + p1*x + p2*x**2

    Args:
        xdata:  vector
                independent data.
        zdata:  vector
                data, which depends on xdata.

    Returns:
        poly:   vector
                coefficients of fit, see above for the order.
        res:    float
                summed residuums.
        rnk:    int
                Effective rank of design matrix M.
        s:      ndarray or None
                Singular values of M.

    '''

    # 1d quadratic fit:
    # z = p0 + p1*x + p2*x**2

    M = np.ones((len(xdata), 3))
    M[:, 1] = xdata  # p1
    M[:, 2] = xdata ** 2  # p2

    poly, res, rnk, s = lstsq(M, zdata)

    return poly, res, rnk, s


def fit_poly1(xdata, zdata):
    '''
    1d linear fit:
    z = p0 + p1*x

    Args:
        xdata:  vector
                independent data
        zdata:  vector
                data, which depends on xdata

    Returns:
        poly:   vector
                coefficients of fit, see above for the order
        res:    float
                summed residuums
        rnk:    int
                Effective rank of design matrix M
        s:      ndarray or None
                Singular values of M

    '''

    M = np.ones((len(xdata), 2))
    M[:, 1] = xdata  # p1

    poly, res, rnk, s = lstsq(M, zdata)

    return poly, res, rnk, s


def calc_Rsquare(y, yfit, Ncoeffs):
    '''
    calculates the adjusted R-square statistic
    Args:
        y:  vector
            true value.
        yfit: vector
            fited value.
        Ncoeffs: int
            number of fit coefficients.

    Returns:
        rsquare: float
            adjusted R-square statistic.

    '''

    Delta_y = y - yfit
    Var_y = y - np.nanmean(y)
    SSE = np.nansum(Delta_y ** 2)
    SST = np.nansum(Var_y ** 2)
    n = len(y)

    if SST == 0 or (n - Ncoeffs) == 0:
        SST = np.nan
        n = np.nan

    return 1. - SSE * (n - 1.) / (SST * (n - Ncoeffs))


def calculate_xsec(T, P, coeffs):
    '''
    Low level function to calculate the absorption cross section from the fitted
    coefficients

    Args:
        T: float
            Temperature in K.
        P: float
            Pressure in Pa.
        coeffs: matrix
            fit coefficients.

    Returns:
        Xsec: vector
            Absorption cross section in m**2.


    The fit model
    2d quadratic fit:
    z= p00 + p10*x + p01*y + p20*x**2 + p11*x*y + p02*y**2

    z=sqrt(Xsec)
    x=T
    y=log10(P) or y=log10(P/T)

    coeffs[0,:]           p00
    coeffs[1,:]           p10
    coeffs[2,:]           p01
    coeffs[3,:]           p20
    coeffs[4,:]           p11
    coeffs[5,:]           p02
    '''

    logP = np.log10(P)

    poly = np.zeros(6)
    poly[0] = 1
    poly[1] = T
    poly[2] = logP
    poly[3] = T ** 2
    poly[4] = T * logP
    poly[5] = logP ** 2

    # allocate
    sqrtXsec = np.zeros(np.shape(coeffs))

    for i in range(6):
        sqrtXsec[i, :] = coeffs[i, :] * poly[i]

    Xsec = np.sum(sqrtXsec, axis=0) ** 2

    return Xsec


def calculate_xsec_fullmodel(T, P, coeffs, minT=0., maxT=np.inf, minP=0, maxP=np.inf):
    '''
    Function to calculate the absorption cross section from the fitted
    coefficients including extrapolation

    Args:
        T: float
            Temperature in K.
        P: float
            Pressure in Pa.
        coeffs: matrix
            fit coefficients.
        minT: float
            minimum temperature of the data in K.
        maxT: float
            maximum temperature of the data in K.
        minP: float
            minimum pressure of the data in Pa.
        maxP: float
            maximum pressure of the data in Pa.

    Returns:
        Xsec: vector
            Absorption cross section in m**2.


    The fit model
    2d quadratic fit:
    z= p00 + p10*x + p01*y + p20*x**2 + p11*x*y + p02*y**2

    z=sqrt(Xsec)
    x=T
    y=log10(P) or y=log10(P/T)

    coeffs[0,:]           p00
    coeffs[1,:]           p10
    coeffs[2,:]           p01
    coeffs[3,:]           p20
    coeffs[4,:]           p11
    coeffs[5,:]           p02
    '''

    if (P < minP or P > maxP or
            T < minT or T > maxT):

        if P < minP:
            P0 = minP

        elif P > maxP:
            P0 = maxP
        else:
            P0 = P
        # P=P0

        if T < minT:
            T0 = minT

        elif T > maxT:
            T0 = maxT

        else:
            T0 = T

        xsec_0 = calculate_xsec(T0, P0, coeffs)

        DxsecDT, DxsecDp = xsec_derivative(T0, P0, coeffs)

        xsec = xsec_0 + DxsecDT * (T - T0) + DxsecDp * (P - P0)

    else:
        # calculate raw xsecs
        xsec = calculate_xsec(T, P, coeffs)

    return xsec


def xsec_derivative(T, P, coeffs):
    '''
    Fucntion to calculate the derivative of the absorption cross section
    from the fitted coefficients.

    Args:
        T: float
            Temperature in K.
        P: float
            Pressure in Pa.
        coeffs: matrix
            fit coefficients.

    Returns:
        DxsecDT: vector
            Temperature derivative.
        DxsecDp: vector
            Pressure derivative.

    The fit model
    2d quadratic fit:
    z= p00 + p10*x + p01*y + p20*x**2 + p11*x*y + p02*y**2

    z=sqrt(Xsec)
    x=T
    y=log10(P)

    '''

    p00 = coeffs[0, :]
    p10 = coeffs[1, :]
    p01 = coeffs[2, :]
    p20 = coeffs[3, :]
    p11 = coeffs[4, :]
    p02 = coeffs[5, :]

    log10 = np.log(10.)
    logP = np.log(P) / log10
    Plog = P * log10

    DxsecDT = (2.
               * (p10 + 2. * p20 * T + p11 * logP)
               * (p00 + p10 * T + p20 * T ** 2 + p01 * logP + p11 * T * logP + p02 * logP ** 2)
               )

    DxsecDp = (2.
               * (p01 / Plog + p11 * T / Plog + 2. * p02 * logP / Plog)
               * (p00 + p10 * T + p20 * T ** 2 + p01 * logP + p11 * T * logP + p02 * logP ** 2)
               )

    return DxsecDT, DxsecDp


def fit_xsec_data(T, P, Xsec, min_deltaLogP=0.2, min_deltaT=20.):
    '''
    FUnction to calculate the fit of the xsec at an arbitrary frequency

    Args:
        T: vector
            temperatures.
        P: vector
            pressures same lenghth as `T`.
        Xsec: vector
            cross section same length as `T`.
        min_deltaLogP: float, optional
            minimum variability of log10(`P`) for fit. Defaults to 0.2.
        min_deltaT: float, optional
            minimum variability of `T` for fit. Defaults to 20.

    Returns:
        fit_result: dictionary
            results of the fit.

    The fit model
    2d quadratic fit:
    z= p00 + p10*x + p01*y + p20*x**2 + p11*x*y + p02*y**2

    z=sqrt(Xsec)
    x=T
    y=log10(P) or y=log10(P/T)

    coeffs[0,:]           p00
    coeffs[1,:]           p10
    coeffs[2,:]           p01
    coeffs[3,:]           p20
    coeffs[4,:]           p11
    coeffs[5,:]           p02
    '''

    logP = np.log10(P)

    sqrtXsec = np.sqrt(Xsec)

    # check for bad values
    logic_inf = np.isinf(T) | np.isinf(logP) | np.isinf(sqrtXsec)
    logic_nan = np.isnan(T) | np.isnan(logP) | np.isnan(sqrtXsec)
    logic_bad = logic_inf | logic_nan

    if np.sum(logic_bad) < len(T):

        # remove bad values
        xData = T[~logic_bad]
        yData = logP[~logic_bad]
        zData = sqrtXsec[~logic_bad]

        # get some information about the data distribution
        Ndata = np.sum(~logic_bad)
        Delta_logP = max(yData) - min(yData)
        Delta_T = max(xData) - min(xData)

        # quadratic fit in temperature and pressure
        if Delta_logP >= min_deltaLogP and Delta_T > min_deltaT and Ndata > 5:

            p, res, rnk, s = fit_poly22(xData, yData, zData)

            coeffs = p

        # linear fit in temperature and pressure
        elif Delta_logP >= min_deltaLogP and Delta_T > min_deltaT and Ndata > 2:

            p, res, rnk, s = fit_poly11(xData, yData, zData)

            coeffs = np.zeros(6)
            coeffs[0] = p[0]
            coeffs[1] = p[1]
            coeffs[2] = p[2]

        # quadratic fit in temperature
        elif Delta_logP < min_deltaLogP and Delta_T > min_deltaT and Ndata > 2:

            p, res, rnk, s = fit_poly2(xData, zData)

            coeffs = np.zeros(6)
            coeffs[0] = p[0]
            coeffs[1] = p[1]
            coeffs[3] = p[2]

        # linear fit in temperature
        elif Delta_logP < min_deltaLogP and Delta_T > min_deltaT and Ndata > 1:

            p, res, rnk, s = fit_poly1(xData, zData)

            coeffs = np.zeros(6)
            coeffs[0] = p[0]
            coeffs[1] = p[1]

        # quadratic fit in pressure
        elif Delta_logP > min_deltaLogP and Delta_T < min_deltaT and Ndata > 2:

            p, res, rnk, s = fit_poly2(yData, zData)

            coeffs = np.zeros(6)
            coeffs[0] = p[0]
            coeffs[2] = p[1]
            coeffs[5] = p[2]

        # linear fit in pressure
        elif Delta_logP > min_deltaLogP and Delta_T < min_deltaT and Ndata > 1:

            p, res, rnk, s = fit_poly1(yData, zData)

            coeffs = np.zeros(6)
            coeffs[0] = p[0]
            coeffs[2] = p[1]

        # no fit, just mean value
        else:
            coeffs = np.zeros(6)
            coeffs[0] = np.mean(zData)

            res = np.sum((zData - coeffs[0]) ** 2)
            rnk = np.nan
            s = np.nan

        MinP = min(10. ** yData)
        MaxP = max(10. ** yData)

        MinT = min(xData)
        MaxT = max(xData)

        fit_result = {}
        fit_result['formula'] = 'p00 + p10*x + p01*y + p20*x**2 + p11*x*y + p02*y**2'
        fit_result['coeff_names'] = ['p00', 'p10', 'p01', 'p20', 'p11', 'p02']
        fit_result['coefficients'] = coeffs
        fit_result['residuum'] = res
        fit_result['rank'] = rnk
        fit_result['sgl_val'] = s
        fit_result['MinP'] = MinP
        fit_result['MaxP'] = MaxP
        fit_result['MinT'] = MinT
        fit_result['MaxT'] = MaxT
        fit_result['NumberOfPoints'] = Ndata
        # fit_result['R2']=R2

    else:
        fit_result = {}
        fit_result['formula'] = 'p00 + p10*x + p01*y + p20*x**2 + p11*x*y + p02*y**2'
        fit_result['coeff_names'] = ['p00', 'p10', 'p01', 'p20', 'p11', 'p02']
        fit_result['coefficients'] = np.zeros(6)
        fit_result['residuum'] = np.nan
        fit_result['rank'] = np.nan
        fit_result['sgl_val'] = np.nan
        fit_result['MinP'] = np.inf
        fit_result['MaxP'] = -np.inf
        fit_result['MinT'] = np.inf
        fit_result['MaxT'] = -np.inf
        fit_result['NumberOfPoints'] = 0

    return fit_result


# %% Apllication functions

def get_coeff_species(coefficients_folder):
    '''
    Convinience function that returns a list with the species inside the coefficients folders.

    Args:
        coefficients_folder (str): Path of the coefficients folder

    Returns:
        all_species (List): List with the Name of each species within the
                            coefficients folder

    '''

    filelist = glob(coefficients_folder + '*.xml.bin')
    filelist.sort()

    # Get species
    all_species = []
    for file in filelist:

        filename = path.basename(file)
        species = filename.split('.')[0]

        if species not in all_species:
            all_species.append(species)

    return all_species


def load_xsec_data(species, coeff_folder):
    '''
    Load the xsec data

    Args:
        species (str): Species name.
        coeff_folder (str): Path to the coefficient folder.

    Returns:
        xsec_data (XsecRecord): Xsec data.

    '''
    xsec_file = path.join(coeff_folder, f'{species}.xml')
    xsec_data = pyarts.xml.load(xsec_file)

    return xsec_data


def calculate_cross_sections(wvn_user, xsec_data, temperature=273., pressure=1013e2):
    '''
    Calculates absorption cross sections for desired wavenumbers.

    Args:
        wvn_user (Vector): Wavenumbers in [cm⁻¹].
        xsec_data (XsecRecord): Xsec data.
        temperature (Float, optional): Temperature in [K]. Default to 273..
        pressure (Float, optional): Pressure in [Pa]. Default to 1013e2.

    Returns:
        xsec_user (Vector): Absorption cross section in [m²].

    '''

    # convert desired wavenumber to frequency in [Hz]
    freq_user = wvn_user * c0 * 100

    # xsec_coeffs=xsec_data.fitcoeffs

    xsec_user = np.zeros(np.shape(wvn_user))

    for m in range(len(xsec_data.fitcoeffs)):
        # frequency of data in [Hz]
        freq_data = xsec_data.fitcoeffs[m].grids[0].data

        # fit coefficients of band m
        coeffs_m = xsec_data.fitcoeffs[m].data.data.transpose()

        # Limits of the data. Outside of this limits the cross section are linearly
        # extrapolated.
        MinP = xsec_data.fitminpressures.data[m]
        MaxP = xsec_data.fitmaxpressures.data[m]
        MinT = xsec_data.fitmintemperatures.data[m]
        MaxT = xsec_data.fitmaxtemperatures.data[m]

        # Calculate the cross section on their internal frequency grid
        xsec_temp = calculate_xsec_fullmodel(temperature, pressure, coeffs_m,
                                             minT=MinT, maxT=MaxT, minP=MinP, maxP=MaxP)

        # Interpolate cross sections to user grid
        f_int = interp1d(freq_data, xsec_temp, fill_value=0., bounds_error=False)
        xsec_user_m = f_int(freq_user)

        xsec_user = xsec_user + xsec_user_m

    return xsec_user


# %% aux function

def getOverlap(a, b):
    '''
    Function to calculate the overlapp between two ranges given
    by the edges of  each range.

    Args:
        a: vector
            Edges of range 1.
        b:  vector
            Edges of range 2.

    Returns:
        overlap: float
            overlap

    '''

    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


# %% plotting routines

def cmap_matlab_lines():
    '''

    Returns:
        cmap: matrix
            Color  map with matlab like line colors.

    '''

    cmap = np.array([[0, 0.44701, 0.74101, 1],
                     [0.85001, 0.32501, 0.09801, 1],
                     [0.92901, 0.69401, 0.12501, 1],
                     [0.49401, 0.18401, 0.55601, 1],
                     [0.46601, 0.67401, 0.18801, 1],
                     [0.30101, 0.74501, 0.93301, 1],
                     [0.63501, 0.07801, 0.18401, 1]])

    return cmap


def default_figure(rows, columns, width_in_cm=29.7, height_in_cm=20.9,
                   sharey='all', sharex='all', dpi=150):
    '''
    simple function to define basic properties of a figure

    Args:
        rows: int
            rows of plots/axis.
        columns: int
            columns of plots/axis.
        width_in_cm: float
            figure width in cm.
        height_in_cm: float
            figure height in cm.
        sharey: str
            marker which y-axis are shared.
        sharex: str
            marker which x-axis are shared.
        dpi: float
            resolution for inline plots.

    Returns:
        fig: matplotlib figure object
            figure object.
        ax: matplotlib axis object or ndarray of axis objects
            matplotlib axis object or ndarray of axis objects.

    '''

    fig, ax = plt.subplots(rows, columns, sharey=sharey, sharex=sharex, dpi=dpi)
    fig.set_size_inches(width_in_cm / 2.54, h=height_in_cm / 2.54)

    return fig, ax


def set_tick_font(ax, font_name):
    '''
    Function to set tick font of x- and y-axis

    Args:
        ax: matplotlib axis object
            axis object.

        font_name: str
            font name.

    Returns:

    '''

    for tick in ax.get_xticklabels():
        tick.set_fontname(font_name)

    for tick in ax.get_yticklabels():
        tick.set_fontname(font_name)


def default_plot_format(ax, font_name=None):
    '''
    simple function to define basic properties of a plot

    Args:
        ax: matplotlib axis object
            axis object

        font_name: str
            font name

    Returns:
        ax: matplotlib axis object
            axis object

        font: font properties object
            font properties

    '''

    font = FontProperties()
    if font_name is not None:
        font.set_name(font_name)

    ax.set_prop_cycle(color=cmap_matlab_lines())

    ax.grid(which='both', linestyle=':', linewidth=0.25)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.axes.tick_params(direction='in', which='both')

    return ax, font


def plot_xsec(wvn, Xsec, XsecFit, ax, xlim=None, xlabel=None, ylabel=None,
              plot_title=None, legend=False, font_name=None):
    '''
    Wrapper to plot up to two crossections in a plot. If only one cross section
    should be plotted set XsecFit to an empty list.

    Args:
        wvn: vector
            wavenumbers.
        Xsec: vector
            cross sections 1.
        XsecFit:
            cross sections 2.
        ax: matplotlib axis object
            axis object.
        xlim: vector
            x-axis limits.
        xlabel: str
            label of x-axis.
        ylabel: str
            label of y-axis.
        plot_title: str
            plot title.
        legend: boolean
            flag to switch on or off the plot legend. default is False.
        font_name: str
            font name.


    Returns:
        ax: matplotlib axis object or ndarray of axis objects

    '''

    ax, font = default_plot_format(ax, font_name)

    linewidth = 0.25

    ax.plot(wvn, Xsec, label='obs', linewidth=linewidth)

    if len(XsecFit) > 0:
        ax.plot(wvn, XsecFit, '-.', label='fit', linewidth=linewidth)

    if xlim != None:
        ax.set_xlim(xlim[0], xlim[1])

    if xlabel != None:
        ax.set_xlabel(xlabel, fontproperties=font)

    if ylabel != None:
        ax.set_ylabel(ylabel, fontproperties=font)

    if plot_title != None:
        ax.set_title(plot_title, fontproperties=font)  # Add a title to the axes.
        ax.title.set_fontsize(10)

    if legend:
        ax.legend()

    return ax


def scatter_plot(T, P, data, fig, ax, clim=None, xlabel='Temperature [K]',
                 ylabel='Pressure [hPa]', plot_title='', cbar_label='',
                 font_name=None, cmap='speed'):
    '''

    Args:
        T: vector
            temperatures.
        P: vector
            pressures same lenghth as `T`.
        data: vector
            data same length as `T`.
        fig: matplotlib figure object
            figure object.
        ax: matplotlib axis object or ndarray of axis objects
            matplotlib axis object or ndarray of axis objects.
        clim: vector or None
            value limits for the coloring.
        xlabel: str
            label of x-axis
        ylabel: str
            label of y-axis
        plot_title: str
            plot title
        cbar_label: str
            label of colorbar
        font_name: str
             font name
        cmap: str
            name of colormap

    Returns:
        fig: matplotlib figure object
            figure object.
        ax: matplotlib axis object or ndarray of axis objects
            matplotlib axis object or ndarray of axis objects.

    '''

    ax, font = default_plot_format(ax, font_name)

    if clim == None:
        clim = [None, None]

    MarkerSize = 50
    sca = ax.scatter(T, P / 100, MarkerSize, data, cmap=cmap, vmin=clim[0], vmax=clim[1])
    ax.set_yscale('log')

    cbar = fig.colorbar(sca, ax=ax, shrink=1)
    cbar.set_label(cbar_label, fontproperties=font)

    ax.set_xlabel(xlabel, fontproperties=font)
    ax.set_ylabel(ylabel, fontproperties=font)
    ax.set_title(plot_title, fontproperties=font)

    return fig, ax


def pcolor_plot(x, y, Z, fig, ax, minZ, maxZ, font_name=None, xlabel=None, ylabel=None,
                cmap=None, title=None, cbar_label=None):
    '''
    wrapper to plot a 2d field

    Args:
        x: vector
            grid in x direction.
        y: vector
            grid in y direction.
        Z: matrix
            2d field, which will be plotted, with dimensions according to x and y
        fig: matplotlib figure object
            figure object.
        ax: matplotlib axis object or ndarray of axis objects
            matplotlib axis object or ndarray of axis objects.
        minZ: float
            minimum value of colorbar.
        maxZ: float
            minimum value of colorbar.
        font_name: str
             font name.
        xlabel: str
            label of x-axis.
        ylabel: str
            label of y-axis.
        cmap: str
            name of colormap.
        title: str
            plot title
        cbar_label: str
            label of colorbar.

    Returns:
        fig: matplotlib figure object
            figure object.
        ax: matplotlib axis object or ndarray of axis objects
            axis object or ndarray of axis objects.
        pcm: matplotlib pcolormesh object
            pcolormesh object.

        cbar: matplotlib colorbar object
            colorbar object.

    '''

    ax, font = default_plot_format(ax, font_name)

    if cmap == None:
        cmap = plt.get_cmap("Blues")

    # make plot and add colorbar
    pcm = ax.pcolormesh(x, y, Z, shading='nearest', cmap=cmap, vmin=minZ, vmax=maxZ)
    pcm.set_rasterized(True)
    cbar = fig.colorbar(pcm, ax=ax, shrink=1)
    ax.set_yscale('log')

    # set the Make-Up and writings
    ax.set_title(title, fontproperties=font)
    ax.set_xlabel(xlabel, fontproperties=font)
    ax.set_ylabel(ylabel, fontproperties=font)

    cbar.set_label(cbar_label, fontproperties=font)

    return fig, ax, pcm, cbar


def make_band_patches(ax, bandwidths, verticalwidth, edgecolor='None', alpha=0.25):
    '''
    function to plot patches in plot to mark the band ranges
    Args:
        ax: matplotlib axis object or ndarray of axis objects
            axis object or ndarray of axis objects.
        bandwidths: list of two component vectors
            lower and upper border of defined bands

        verticalwidth: vector
            upper and lower vertical border for plotting
        edgecolor: colormarker
            colormarker for the edges of the patches
        alpha: float
            alpha blending value, between 0 (transparent) and 1 (opaque).


    Returns:
        ax: matplotlib axis object or ndarray of axis objects
            axis object or ndarray of axis objects.

    '''

    cmap = cmap_matlab_lines()

    for x, i in zip(bandwidths, range(len(bandwidths))):
        idx = i % np.size(cmap, axis=0)

        color = cmap[idx, :]

        patch = ptch.Rectangle((x[0], verticalwidth[0]), x[1] - x[0],
                               verticalwidth[1] - verticalwidth[0], facecolor=color,
                               alpha=alpha, edgecolor=edgecolor)

        ax.add_patch(patch)

    return ax


def plot_raw_data(xsec_data, species, font_name=None, max_num=10000):
    '''
    Function to plot overviews of the raw xsec data
    Args:
        xsec_data: list of xsec data
        species: str
            name of the species
        font_name: str
            font name
        max_num: int
            defines how many points of a spectrum is shown. If a
            spectrum has more more points than only a subset is shown.


    Returns:
        fig: matplotlib figure object
            figure object.
        ax: matplotlib axis object or ndarray of axis objects
            matplotlib axis object or ndarray of axis objects.

    '''

    number_of_sets = len(xsec_data)

    fig1, ax1 = default_figure(number_of_sets, 1, width_in_cm=20.9, height_in_cm=29.7)

    if number_of_sets == 1:
        ax1 = [ax1]

    for j in range(number_of_sets):

        ax1[j], font = default_plot_format(ax1[j], font_name)

        for k in range(len(xsec_data[j])):

            wvn = np.linspace(xsec_data[j][k]['wmin'], xsec_data[j][k]['wmax'],
                              len(xsec_data[j][k]['xsec']))

            XSECS = xsec_data[j][k]['xsec']

            # if xsec are too detailed, make it it coarser.
            # it is just an overview plot, so not all details are needed.
            if len(XSECS) > max_num:
                idx = int(np.round(len(XSECS) / max_num))
                ax1[j].plot(wvn[0::idx], XSECS[0::idx], linewidth=0.1)
            else:
                ax1[j].plot(wvn, XSECS, linewidth=0.1)

        ax1[j].set_yscale('log')
        ax1[j].set_ylim(1e-24, 1e-15)
        ax1[j].grid(which='both', linestyle=':', linewidth=0.25)
        ax1[j].set_ylabel('$a_{xsec} $[cm$^2$]')
        ax1[j].set_title(species + ': set ' + str(j) + '; $N_{obs}=$' + str(len(xsec_data[j])) +
                         ' $; N_{sample}$=' + str(len(wvn)))

        if j == number_of_sets:
            ax1[j].set_xlabel('wavenumber [cm$^{-1}$]')

    return fig1, ax1

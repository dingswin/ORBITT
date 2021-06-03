#!/usr/bin/env python
"""
written in python3.
"""
import bilby, inspect
from astropy.time import Time
import numpy as np
import astropy.units as u
from astropy import constants
import os, sys
import howfun
from astropy.table import Table
#from sterne.model.calculate as position
def simulate(refepoch, pmparin, *args, **kwargs):
    """
    args for more pmparin files.
    kwargs for unshare (unshare parameters).
    """
    args = list(args)
    args.reverse()
    args.append(pmparin)
    args.reverse() #put the major pmparin at first
    pmparins = args
    try:
        unshares = kwargs['unshares']
    except KeyError:
        unshares = []
        

    list_of_dict = []
    for pmparin in pmparins:
        t = readpmparin(pmparin)
        radecs = np.concatenate([t['RA'], t['DEC']])
        errs = np.concatenate([t['errRA'], t['errDEC']])
        epochs = np.array(t['epoch'])
        dictionary = {}
        dictionary['epochs'] = epochs
        dictionary['radecs'] = radecs
        dictionary['errs'] = errs
        list_of_dict.append(dictionary)
    print(unshares)
    print(list_of_dict)
    likelihood = Gaussianlikelihood(refepoch, list_of_dict, unshares, positions)
    initsfile = pmparins[0].replace('pmpar.in', 'inits')
    #if not os.path.exists(initsfile):
    #    generate_prior_range(pmparin, refepoch)
    generate_prior_range(pmparins, unshares, refepoch, 20)
    limits = read_inits(initsfile)
    print(limits)
    priors = {}
    for parameter in limits.keys():
        priors[parameter] = bilby.core.prior.Uniform(minimum=limits[parameter][0],\
            maximum=limits[parameter][1], name=parameter, latex_label=parameter)
    result = bilby.run_sampler(likelihood=likelihood, priors=priors,\
        sampler='emcee', nwalkers=100, iterations=100)
    result.plot_corner()
    result.save_posterior_samples()

def infer_estimates_from_bilby_results(samplefile):
    t = Table.read(samplefile, format='ascii')
    parameters = t.colnames[:-2]
    dict_median = {}
    dict_bound = {} #16% and 84% percentiles
    outputfile = samplefile.replace('posterior_samples', 'bayesian_estimates')
    writefile = open(outputfile, 'w')
    writefile.write('#Units: px in mas, ra and dec in rad, mu_a and mu_d in mas/yr\n')
    for p in parameters:
        dict_median[p] = howfun.sample2median(t[p])
        dict_bound[p] = howfun.sample2median_range(t[p], 1)
        writefile.write('%s = %f + %.11f - %.11f\n' % (p, dict_median[p],\
            dict_bound[p][1]-dict_median[p], dict_median[p]-dict_bound[p][0]))
    writefile.close()






def __________get_a_prior(chain, HowManyTimesStd=20):
    """
    deprecated.
    prior for ra and dec is set using generate_prior_range() now.
    """
    chain_average = np.mean(chain)
    chain_std = np.std(chain)
    lower_limit = chain_average - HowManyTimesStd*chain_std
    upper_limit = chain_average + HowManyTimesStd*chain_std
    return lower_limit, upper_limit

def read_inits(initsfile):
    #initsfile = pmparin.replace('pmpar.in', 'inits')
    readfile = open(initsfile, 'r')
    lines = readfile.readlines()
    readfile.close()
    dict_limits = {}
    for line in lines:
        for keyword in ['ra', 'dec', 'mu_a', 'mu_d', 'px']:
            if keyword in line:
                parameter = line.split(':')[0].strip()
                limits = line.split(':')[-1].strip().split(',')
                limits = [float(limit) for limit in limits]
                if parameter in dict_limits.keys():
                    limits[0] = min(limits[0], dict_limits[parameter][0])
                    limits[1] = max(limits[1], dict_limits[parameter][1])
                dict_limits[parameter] = limits
    return dict_limits 


def generate_prior_range(pmparins, unshares, epoch, HowManySigma=20):
    """
    Common parameters might have more than 1 list of priors.
    In such cases, the larger outer bound will be adopted.
    """
    HMS = HowManySigma
    inits = pmparins[0].replace('pmpar.in','inits')
    writefile = open(inits, 'w')
    writefile.write('#Prior info at MJD %f.\n' % epoch)
    writefile.write('#%d reduced-chi-squre-corrected sigma limits are used.\n' % HMS)
    writefile.write('#The prior info is based on the pmpar results.\n')
    for i in range(len(pmparins)):
        pmparout = pmparins[i].replace('pmpar.in','pmpar.out')
        replace_pmparin_epoch(pmparins[i], epoch)
        os.system("pmpar %s > %s" % (pmparins[i], pmparout))
        [ra, error_ra, dec, error_dec, mu_a, error_mu_a, mu_d, error_mu_d, px, error_px, rchsq, junk] = readpmparout(pmparout)
        errors = np.array([error_ra, error_dec, error_mu_a, error_mu_d, error_px])
        print(errors, rchsq)
        errors *= rchsq**0.5
        print(errors)
        error_ra, error_dec, error_mu_a, error_mu_d, error_px = errors
        ra_low, ra_up = ra - HMS * error_ra, ra + HMS * error_ra
        dec_low, dec_up = dec - HMS * error_dec, dec + HMS * error_dec
        mu_a_low, mu_a_up = mu_a - HMS * error_mu_a, mu_a + HMS * error_mu_a
        mu_d_low, mu_d_up = mu_d - HMS * error_mu_d, mu_d + HMS * error_mu_d
        px_low, px_up = px - HMS * error_px, px + HMS * error_px
        
        writefile.write('ra%d: %.11f,%.11f\n' % (i, ra_low, ra_up))
        writefile.write('dec%d: %.11f,%.11f\n' % (i, dec_low, dec_up))
        if 'mu_a' in unshares:
            writefile.write('mu_a%d: %f,%f\n' % (i, mu_a_low, mu_a_up))
        else:
            writefile.write('mu_a: %f,%f\n' % (mu_a_low, mu_a_up))
        if 'mu_d' in unshares:
            writefile.write('mu_d%d: %f,%f\n' % (i, mu_d_low, mu_d_up))
        else:
            writefile.write('mu_d: %f,%f\n' % (mu_d_low, mu_d_up))
        if 'px' in unshares:
            writefile.write('px%d: %f,%f\n' % (i, px_low, px_up))
        else:
            writefile.write('px: %f,%f\n' % (px_low, px_up))
    writefile.close()



def readpmparout(pmparout):
    """
    The function serves to offer priors for the simulation.
    """
    rchsq = 0
    lines = open(pmparout).readlines()
    for line in lines:
        if 'epoch' in line:
            epoch = line.split('=')[1].strip()
        if 'Reduced' in line:
            rchsq = float(line.split('=')[1].strip())
        for estimate in ['mu_a', 'mu_d', 'pi']:
            if estimate in line:
                #globals()['line'] = line
                #string = ("%s = " % estimate.strip())
                value = line.split('=')[-1].split('+')[0].strip()
                #print(value)
                #print(estimate.strip())
                exec("%s='%s'" % (estimate.strip(), value), globals())
        if 'RA' in line: #here, due to a bug in exec(), it is not combined with the other three parameters
            RA = line.split('=')[-1].split('+')[0].strip()
            RA = howfun.dms2deg(RA)
        if 'Dec  ' in line:
            Dec = line.split('=')[-1].split('+')[0].strip()
            Dec = howfun.dms2deg(Dec)

    for line in lines:
        if 'RA' in line:
            error_RA = float(line.split('+-')[1].strip().split(' ')[0])
        if 'Dec  ' in line:
            error_Dec = float(line.split('+-')[1].strip().split(' ')[0])
        for estimate in ['mu_a', 'mu_d', 'pi']:
            if estimate in line:
                error = line.split('+-')[1].strip().split(' ')[0]
                exec("error_%s = %s" % (estimate.strip(), error), globals())
                #exec("print(error_%s)" % estimate)
                exec("%s = float(%s)" % (estimate.strip(), estimate.strip()), globals())
    RA *= 15 * np.pi/180. #rad
    Dec *= np.pi/180. #rad
    error_RA *= 15 * np.pi/180./3600. #rad
    error_Dec *= np.pi/180./3600. #rad
    return RA, error_RA, Dec, error_Dec, mu_a, error_mu_a, mu_d, error_mu_d, pi, error_pi, rchsq, float(epoch)
    


def replace_pmparin_epoch(pmparin, epoch):
    """
    epoch in MJD
    """
    readfile = open(pmparin, 'r')
    lines = readfile.readlines()
    for i in range(len(lines)):
        if 'epoch' in lines[i] and (not lines[i].strip().startswith('#')):
            lines[i] = 'epoch = ' + str(epoch) + '\n'
    readfile.close()
    writefile = open(pmparin, 'w')
    writefile.writelines(lines)
    writefile.close()

class Gaussianlikelihood(bilby.Likelihood):
    def __init__(self, refepoch, list_of_dict, unshares, positions):
        """
        Addition of multiple Gaussian likelihoods

        Parameters
        ----------
        data: array_like
            The data to analyse
        """
        self.refepoch = refepoch
        self.list_of_dict = list_of_dict
        self.positions = positions
        self.number_of_pmparins = len(self.list_of_dict)

        #parameters = inspect.getargspec(positions).args
        #parameters.pop(0)
        parameters = {}
        for parameter in ['mu_a', 'mu_d', 'px']:
            if not parameter in unshares:
                parameters[parameter] = None
        for i in range(self.number_of_pmparins):
            exec("parameters['ra%d'] = None" % i)
            exec("parameters['dec%d'] = None" % i)
            for parameter in unshares:
                exec("parameters['%s%d'] = None" % (parameter ,i))

        print(parameters)
        super().__init__(parameters)

    def log_likelihood(self):
        """
        the name has to be log_likelihood, and the PDF has to do the log calculation.
        """
        log_p = 0
        for i in range(self.number_of_pmparins):
            res = self.list_of_dict[i]['radecs'] - self.positions(self.refepoch, self.list_of_dict[i]['epochs'], i, self.parameters)
            log_p += -0.5 * np.sum((res/self.list_of_dict[i]['errs'])**2) #if both RA and errRA are weighted by cos(DEC), the weighting is canceled out
        return log_p




def positions(refepoch, epochs, parameter_filter_index, dict_parameters):
    FP = filter_dictionary_of_parameter_with_index(dict_parameters, parameter_filter_index)
    Ps = list(FP.keys())
    Ps.sort()
    ra_models = np.array([])
    dec_models = np.array([])
    for i in range(len(epochs)):
        ra_model, dec_model = position(refepoch, epochs[i], FP[Ps[0]],\
            FP[Ps[1]], FP[Ps[2]], FP[Ps[3]], FP[Ps[4]])
        ra_models = np.append(ra_models, ra_model)
        dec_models = np.append(dec_models, dec_model)
    return np.concatenate([ra_models, dec_models])
def filter_dictionary_of_parameter_with_index(dict_of_parameters, filter_index):
    """
    Input parameters
    ----------------
    dict_of_parameters : dict
        Dictionary of astrometric parameters.
    filter_index : int
        A number (for the pmparin file) used to choose the right paramters for each gaussian distribution.

    Return parameters
    -----------------
    filtered_dict_of_parameters : dict
        Dictionary after the filtering with the filter index.
    """
    filtered_dict_of_parameters = dict_of_parameters.copy()
    for parameter in dict_of_parameters.keys():
        if any(char.isdigit() for char in parameter) and (not str(filter_index) in parameter):
            del filtered_dict_of_parameters[parameter]
    if len(filtered_dict_of_parameters) != 5:
        print('Filtered parameters are not 5, which might be related to invalid filter index.')
        sys.exit()
    return filtered_dict_of_parameters



def position(refepoch, epoch, dec_rad, mu_a, mu_d, px, ra_rad):
    """
    Outputs position given reference position, proper motion and parallax 
    (at a reference epoch) and time of interest.

    Input parameters
    ----------------
    refepoch : float
        Reference epoch, in MJD.
    ra_rad : rad
        Right ascension for barycentric frame, in hh:mm:ss.ssss;
        Also see inputgeocentricposition.
    dec_rad : rad
        Declination for barycentric frame, in dd:mm:ss.sss;
        Also see inputgeocentricposition.
    mu_a : float
        Proper motion in right ascension, in mas/yr.
    mu_d : float
        Proper motion in declination, in mas/yr.
    px : float 
        Parallax, in mas.
    epoch : float
        Time of interest, in MJD.
    useDE421 : bool
        Use DE421 if True (default), use DE405 if False.
    inputgeocentricposition : bool
        Use input ra and dec for barycentric frame if False (default);
        Use input ra and dec for geocentric frame if True.

    Return parameters
    -----------------
    ra_rad : float
        Right ascension for geocentric frame, in rad.
    dec_rad : float
        Declination for geocentric frame, in rad.

    Notes
    -----
    """
    #ra_rad, dec_rad = dms2rad(ra, dec) 
    dT = (epoch - refepoch) * (u.d).to(u.yr) #in yr
    ### proper motion effect ###
    dRA = dT * mu_a / np.cos(dec_rad) # in mas
    dDEC = dT * mu_d #in mas
    ### parallax effect ###
    dRA, dDEC = np.array([dRA, dDEC]) + parallax_related_position_offset_from_the_barycentric_frame(epoch, ra_rad, dec_rad, px)  # in mas
    ra_rad += dRA * (u.mas).to(u.rad)
    dec_rad += dDEC * (u.mas).to(u.rad)
    #print(howfun.deg2dms(ra_rad*180/np.pi/15.), howfun.deg2dms(dec_rad*180/np.pi))
    return  ra_rad, dec_rad #rad

def plot_model_given_astrometric_parameters(refepoch, ra, dec, mu_a, mu_d, px, start_epoch, end_epoch,\
        useDE421=True, inputgeocentricposition=False):
    """
    Input parameters
    ----------------
    start_epoch : float
        Epoch when the plot starts, in MJD.
    end_epoch : float
        Epoch when the plot ends, in MJD.
    """
    import matplotlib.pyplot as plt
    epoch_step = (end_epoch - start_epoch) / 100.
    epochs = np.arange(start_epoch, end_epoch+epoch_step, epoch_step)
    #print(epochs)
    ra_rads, dec_rads = np.array([]), np.array([])
    dRA_pxs, dDEC_pxs = np.array([]), np.array([])
    for epoch in epochs:
        ra_rad, dec_rad = position(refepoch, epoch, dec, mu_a, mu_d, px, ra, useDE421, inputgeocentricposition)
        dRA_px, dDEC_px = parallax_related_position_offset_from_the_barycentric_frame(epoch, ra, dec, px)
        ra_rads = np.append(ra_rads, ra_rad)
        dec_rads = np.append(dec_rads, dec_rad)
        dRA_pxs = np.append(dRA_pxs, dRA_px)
        dDEC_pxs = np.append(dDEC_pxs, dDEC_px)
    #print(ra_rads, dec_rads)
    fig = plt.figure()
    ax1 = fig.add_subplot(221)
    ax1.set_xlabel('RA. (rad)')
    ax1.set_ylabel('Decl. (rad)')
    ax1.plot(ra_rads, dec_rads)
    
    ax2 = fig.add_subplot(222)
    ax2.set_ylabel('Decl. offset (mas)')
    ax2.set_xlabel('RA. offset (mas)')
    ax2.plot(dRA_pxs, dDEC_pxs)

    ax3 = fig.add_subplot(223)
    ax3.set_ylabel('RA. offset (mas)')
    ax3.set_xlabel('epoch (MJD)')
    ax3.plot(epochs, dRA_pxs)
    
    ax4 = fig.add_subplot(224)
    ax4.set_ylabel('Decl. offset (mas)')
    ax4.set_xlabel('epoch (MJD)')
    ax4.plot(epochs, dDEC_pxs)
    
    fig.tight_layout() #always put this before savefig
    directory_to_save = 'sterne_figures/'
    if not os.path.exists(directory_to_save):
        os.mkdir(directory_to_save)
    plt.savefig(directory_to_save + '/astrometric_model.pdf')

def dms2rad(ra, dec):
    """
    Input parameters
    ----------------
    ra : str
        Right ascension, in hh:mm:ss.sss.
    dec : str
        Declination, in dd:mm:ss.ssss.

    Return parameters
    -----------------
    ra : float
        Right ascension, in rad.
    dec : float
        Declination, in rad.
    """
    ra = howfun.dms2deg(ra)
    ra *= 15 * np.pi/180 #in rad
    dec = howfun.dms2deg(dec)
    dec *= np.pi/180 #in rad
    return ra, dec
    
def parallax_related_position_offset_from_the_barycentric_frame(epoch, ra, dec, px):
    """
    Originality note
    ----------------
    This function is adopted from astrometryfit written by Adam Deller and Scott Ransom.

    Return parameters
    -----------------
    np.array([dRA, dDEC])
        dRA : float
            Right asension offset, in mas.
        dDEC : float
            Declination offset, in mas.

    References
    ---------
    1. Explanatory Supplement to Astronomical Almanac.
    2. NOVAS
    """
    import novas.compat.solsys as solsys
    from novas.compat.eph_manager import ephem_open
    #ra, dec = dms2rad(ra, dec) 
    #if not useDE421:
    #    ephem_open()
    #else:
    ephem_open(os.path.join(os.getenv("TEMPO2"), "T2runtime/ephemeris/DE421.1950.2050"))
    # This is the Earth position in X, Y, Z (AU) in ICRS wrt SSB 
    X, Y, Z = solsys.solarsystem(epoch+2400000.5, 3, 0)[0]  
    #print(X,Y,Z)
    # Following is from Astronomical Almanac Explanatory Supplement p 125-126
    dRA = px * (X * np.sin(ra) - Y * np.cos(ra)) / np.cos(dec) #in mas
    dDEC = px * (X * np.cos(ra) * np.sin(dec) + Y * np.sin(ra) * np.sin(dec) - Z * np.cos(dec)) #in mas
    return np.array([dRA, dDEC]) #in mas






def readpmparin(pmparin):
    """
    """
    epochs = RAs = errRAs = DECs = errDECs = np.array([])
    lines = open(pmparin).readlines()
    for line in lines:
        #if 'epoch' in line and not line.strip().startswith('#'):
        #    refepoch = line.split('=')[1].strip()
        if line.count(':')==4 and (not line.strip().startswith('#')): 
            epoch, RA, errRA, DEC, errDEC = line.strip().split(' ')
            epoch = decyear2mjd(float(epoch.strip())) #in MJD
            DEC = howfun.dms2deg(DEC.strip()) #in deg
            DEC *= np.pi/180. #in rad
            RA = howfun.dms2deg(RA.strip()) #in hr
            RA *= 15*np.pi/180. #in rad
            errRA = float(errRA.strip()) #in s
            errRA *= 15 * np.pi/180./3600. #in rad
            errDEC = float(errDEC.strip()) #in arcsecond
            errDEC *= np.pi/180./3600 #in rad

            epochs = np.append(epochs, epoch)
            RAs = np.append(RAs, RA)
            DECs = np.append(DECs, DEC)
            errRAs = np.append(errRAs, errRA)
            errDECs = np.append(errDECs, errDEC)
    t = Table([epochs, RAs, errRAs, DECs, errDECs], names=['epoch', 'RA', 'errRA', 'DEC', 'errDEC'])
    return t

def decyear2mjd(epoch):
    """
    """
    threshold = 10000
    if epoch > threshold:
        return epoch
    else:
        decyear = Time(epoch, format='decimalyear')
        MJD = float(format(decyear.mjd))
        return MJD

def reflex_motion(epoch, px):
    """

    mathematical formalism found in tempo2 paper;
    when e=0;

    Input paramters
    ---------------
    px : float
        in mas.

    Return parameters
    -----------------
    e1 (RA eastward), e2 (DEC northward), R0 (line of sight)
    """
    epoch *= u.d
    T0 = 56001.38381 * u.d #MJD
    Pb0 = 2.445759995469 * u.d
    Pbdot = 0.2586e-12 #s/s
    incl = 85.29 * u.deg
    #print(incl)
    a = 10.8480239 * constants.c * u.s
    om = 119.900 * u.deg
    Om_asc = 190 * u.deg
    #print(Om_asc)


    n = (2*np.pi/Pb0 + np.pi*Pbdot*(epoch-T0)/(Pb0)**2) * u.rad #angular velocity
    u1 = n * (epoch - T0)
    b_abs = a
    b_AU = b_abs.to(u.AU).value
    offset = b_AU * px
    #print(b_abs)
    theta = om + u1
    #print(theta)
    matr1 = np.mat([[np.sin(Om_asc), -np.cos(Om_asc), 0],
                    [np.cos(Om_asc), np.sin(Om_asc), 0],
                    [0, 0, 1]])
    matr2 = np.mat([[1, 0, 0],
                    [0, -np.cos(incl), -np.sin(incl)],
                    [0, np.sin(incl), -np.cos(incl)]])
    matr3 = np.mat([[offset*np.cos(theta)],
                    [offset*np.sin(theta)],
                    [0]])
    b = matr1 * matr2 * matr3
    return b #in mas

    


# STERNE (stars in German) -- aStromeTry bayEsian infeReNcE

## Authors:  
Hao Ding and Adam Deller

## Installation:  
This package can be installed using
```
pip install sterne
```

## Code Description:  
This code generalises on [astrometryfit](https://github.com/adamdeller/astrometryfit) by Adam Deller and Scott Ransom. The generalisation enables one to infer astrometric parameters for sources sharing some identical astrometric parameters (but different on other astrometric parameters). The scope of the code is mainly VLBI astrometry of nearby pulsars, preferably the astrometry having multiple in-beam calibrators. However, there is no doubt the code can be applied to astrometry of other targets carried out beyond VLBI.

## Functions:  
1) infer up to 8 parameters -- parallax, proper motion, reference position, longitude of ascending node, inclination angle (already realized by astrometryfit) and EFAC. For the two (binary) orbital-motion parameters, the Tempo2 convention is adopted to assist comparison with pulsar timing results.
2) for sources sharing some identical astrometric parameters (e.g. parallax, proper motion), parameters can be inferred together (new feature).

## Requisites to use Sterne:  
1) planetary ephemerides used by tempo2 are needed, which were downloaded
along with [TEMPO2](https://bitbucket.org/psrsoft/tempo2/downloads/).
2) input positions (normally measured with VLBI) in the traditional "pmpar.in" format (for [pmpar](https://github.com/walterfb/pmpar)).
3) initsfile (.inits) containing priors for each parameter; a priminary initsfile can be produced with priors.generate_initsfile().
4) parfile (.par) containing timing parameters (provided by [PSRCAT](https://www.atnf.csiro.au/research/pulsar/psrcat/)); latest numbers beyond PSRCAT should be updated if possible.
See sterne.simulate.py for more details.

## Outputs:  
The output will be provided in the "outdir" (or a folder name specified by the user) folder under the current directory. Publication-level corner plots can be made with plot.corner() that consumes posterior_samples.dat (or its like).

## Usage tips:  
1) be sure to clear away the outdir folder before new inference.
2) make sure the refepoch for priors match with the one used in the simulation.

## Citation guide:  
STERNE was first used in [Ding et al. 2021](https://iopscience.iop.org/article/10.3847/2041-8213/ac3091/meta). The EFAC feature was added and first employed for [Ding et al. 2023](https://doi.org/10.1093/mnras/stac3725).

## Acknowledgement:  
STERNE makes use of other python packages including [numpy](https://numpy.org/), [astropy](https://www.astropy.org/), [bilby](https://git.ligo.org/lscsoft/bilby), [psrqpy](https://github.com/mattpitkin/psrqpy), [novas](https://aa.usno.navy.mil/software/novas_info), [matplotlib](https://matplotlib.org/) and [corner](https://github.com/dfm/corner.py).

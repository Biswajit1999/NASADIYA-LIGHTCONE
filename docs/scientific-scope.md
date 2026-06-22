# Scientific scope

NĀSADĪYA LIGHTCONE is an exploratory visual interface for public survey catalogues. It is not a cosmology-analysis pipeline, a replacement for a survey archive, or a complete physical reconstruction of the Universe.

## 2MRS v0.1 placement

The 2MRS source table reports sky positions and barycentric recession velocities. The build step defines a displayed redshift `z = cz / c`, preserving both `cz` and `e_cz`. It then evaluates the Planck18 comoving distance relation to place each object in an observer-centred Cartesian frame.

This is transparent but limited. At local distances, peculiar velocities can be important relative to cosmological recession. A plotted radial position must not be read as a flow-corrected individual distance measurement.

## Survey incompleteness

The 2MRS principal sample has explicit magnitude and Galactic-latitude selection. It covers most, not all, of the sky. The Galactic Zone of Avoidance and the survey selection function mean that an apparent absence of points may arise from measurement coverage or selection rather than matter under-density.

## Future survey layers

Photometric catalogues must display radial uncertainty. Spectroscopic catalogue releases must retain redshift-quality and completeness fields. Derived density or cosmic-web layers must have a distinct layer class, algorithm description, and source citation.

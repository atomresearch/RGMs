function xyz   = spm_spherical2rectang(origin,ph,th,d)
% Returns the Cartesian coordinates from spherical coordinates (and origin)
% origin   - [x,y,z]
% ph       - azimuthal angle (radians) (in x-y plane)
% th       - polar (radians)
% d        - radial distance
%--------------------------------------------------------------------------
% Staged verbatim from DEM_drone_vi.m subfunction (OPTIM2FULL F5 oracle).
x   = origin(1) + d*cos(ph)*cos(th);
y   = origin(2) + d*sin(ph)*cos(th);
z   = origin(3) - d*sin(th);
xyz = [x,y,z];

return

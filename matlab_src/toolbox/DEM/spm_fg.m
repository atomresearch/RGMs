function par = spm_fg(g,s)
% projective geometry
% FORMAT loc = spm_fg(g,s)
%
% s(1) - location (x)
% s(2) - location (y)
% s(3) - location (z)
% s(4) - drone angles
%
% par  - parents of g
%--------------------------------------------------------------------------
% Staged verbatim from DEM_drone_vi.m subfunction (OPTIM2FULL F5 oracle).
% Dependencies: spm_index, spm_sub2ind, spm_spherical2rectang (staged).
global PG

Nu    = PG.Nu;                               % domain factors
Ng    = PG.Nr*PG.Nr;                         % number of rays
Np    = PG.Nx*PG.Ny*PG.Nz;                   % number of places

% check modality
%--------------------------------------------------------------------------
if g > (Ng + Ng)

    % telemetry
    %----------------------------------------------------------------------
    par = g - (Ng + Ng);
    par = uint16(par);
    return

elseif g > Ng

    % class (same factors as depth)
    %----------------------------------------------------------------------
    g = g - Ng;

end

% factors on ray g: depth and class
%==========================================================================

% get centre and angles of drone
%--------------------------------------------------------------------------
origin = [s(1:3)];
angle  = PG.phi(s(4));

% get sampled locations for this modality
%--------------------------------------------------------------------------
theta  = PG.FOV;                            % ray angles (60 degree FOV)
d      = spm_index([PG.Nr,PG.Nr],g);        % ray (line of sight) angle
ph     = angle - theta(d(2));               % azimuthal angle
th     = theta(d(1)) - theta(1);            % polar angle

% location of (animate) object
%--------------------------------------------------------------------------
No    = (numel(s) - Nu)/3;
jo    = 0;
for o = 1:No
    so    = s(Nu + (o - 1)*3 + (1:3));           % place
    fo(o) = Nu + Np + o*4;                       % class
    jo(o) = spm_sub2ind([PG.Nx,PG.Ny,PG.Nz],so(1),so(2),so(3));
end

% for each depth along ray (i.e., line of sight)
%--------------------------------------------------------------------------
par   = zeros(1,0);
for d = 1:PG.Nd

    % find nearest location in the latent state space
    %----------------------------------------------------------------------
    xyz = ceil(spm_spherical2rectang(origin,ph,th,d));
    x   = uint8(xyz(1));
    y   = uint8(xyz(2));
    z   = uint8(xyz(3));
    if x > 0 && x <= PG.Nx && y > 0 && y <= PG.Ny && z > 0 && z <= PG.Nz

        % within scene location
        %------------------------------------------------------------------
        j      = spm_sub2ind([PG.Nx,PG.Ny,PG.Nz],x,y,z);

        % is this location occupied by an (animate) object?
        %------------------------------------------------------------------
        par(d) = j + Nu;
        for o = 1:No
            if j == jo(o)
                par(d) = fo(o);
            end
        end
    else
        break
    end
end

% save parents of A{g} - latent locations
%--------------------------------------------------------------------------
par   = uint16(par);

return

function O = spm_depth(s)
% likelihood of depth given some states (s)
% FORMAT O = spm_depth(s)
% s  - class or state along ray
%--------------------------------------------------------------------------
% Staged verbatim from DEM_drone_vi.m subfunction (OPTIM2FULL F5 oracle).
global PG

% depth outcome
%--------------------------------------------------------------------------
O   = zeros(PG.Nd + 1,1);
d   = find(s > 1,1,'first');             % first nonempty class
if numel(d)
    O(d,1)         = 1;                  % depth of first occluder
else
    O(PG.Nd + 1,1) = 1;                  % nothing in range
end
return

function O = spm_state(s)
% likelihood of class given some states (s)
% FORMAT O = spm_state(s)
% s  - class or state along ray
%--------------------------------------------------------------------------
% Staged verbatim from DEM_drone_vi.m subfunction (OPTIM2FULL F5 oracle).
global PG

% class (state)
%--------------------------------------------------------------------------
O   = zeros(PG.Nc,1);
d   = find(s > 1,1,'first');           % first nonempty class
if numel(d)
    O(s(d)) = 1;                       % class of first occluder
else
    O(1)    = 1;                       % nothing in range (null)
end
return

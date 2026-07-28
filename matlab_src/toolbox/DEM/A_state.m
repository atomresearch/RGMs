function [O,r] = A_state(P,f,Q)
% likelihood of states
% FORMAT [O,r] = A_state(P,f,Q)
% P  - marginal over states along ray / outcomes
% f  - indices of nonzero elements
% Q  - marginal over states along ray
%--------------------------------------------------------------------------
% This is a dual use function. If the first argument (P) is a cell, that
% this function returns the posterior predictive densities over outcomes,
% given that the posterior over states in P. Conversely, if P is a vector,
% then the marginal likelihoods over states are returned, given the
% outcomes in P. These marginals can be selected on the basis of posteriors
% over states in Q. The indices of the reduced marginals are returned in r.
% depth outcome
%==========================================================================
% Staged verbatim from DEM_drone_vi.m subfunction (OPTIM2FULL F5 oracle).
global PG

if iscell(P)

    % outcome likelihood requested: O = spm_dot(A,P(n));
    %----------------------------------------------------------------------
    d       = A_depth(P);                 % depth of first occluder
    q       = spm_cat(P);                 % P(state)
    q(1,:)  = 0;                          % P(state | occupied)
    q(1,PG.Nd + 1) = 1;                   % out of range

    q = spm_dir_norm(q);                  % normalise
    O = q*d;                              % P(outcome)

elseif nargin == 1

    % generate from states
    %----------------------------------------------------------------------
    O = spm_state(P);

else

    % un-normalised likelihood of states: P = spm_dot(A,O);
    %----------------------------------------------------------------------
    % Only return a marginal likelihood for any state for which there is a
    % precise posterior belief it is at an occluding location: i.e., the
    % first occluder
    %----------------------------------------------------------------------
    O = {};
    r = [];
    d = A_depth(Q);                       % depth of first occluder
    d = find(d > (1 - 1/32),1,'first');
    if numel(d)
        if d <= PG.Nd && d <= numel(f)
            r = d;
            O = {P(f{r})};
        end
    end

end
return

function [O,r] = A_depth(P,f,Q)
% likelihood of depth
% FORMAT [O,r] = A_depth(P,f,Q)
% P  - marginal over states along ray / outcomes
% f  - indices of nonzero elements
% Q  - marginal over states along ray
%__________________________________________________________________________
% This is a dual use function. If the first argument (P) is a cell, that
% this function returns the posterior predictive densities over outcomes,
% given that the posterior over states in P. Conversely, if P is a vector,
% then the marginal likelihoods over states are returned, given the
% outcomes in P. These marginals can be selected on the basis of posteriors
% over states in Q. The indices of the reduced marginals are returned in r.
%--------------------------------------------------------------------------
% Staged verbatim from DEM_drone_vi.m subfunction (OPTIM2FULL F5 oracle).
global PG


% depth outcome
%==========================================================================
if iscell(P)

    % outcome likelihood: O = spm_dot(A,P(n));
    %----------------------------------------------------------------------
    q = spm_cat(P);                        % marginals along ray
    q = q(1,:);                            % P(empty)
    p = 1 - q;                             % P(occupied)
    O = p.*cumprod([1 q(1:end - 1)]);      % P(first occupied)
    O = O(:);                              % P(outcome)
    O(PG.Nd + 1,1) = max(1 - sum(O),0);
    O = O/sum(O);

elseif nargin == 1

    % generate from states
    %----------------------------------------------------------------------
    O = spm_depth(P);

else

    % un-normalised likelihood of states: P = spm_dot(A,O);
    %======================================================================

    % return marginal likelihoods as cells
    %----------------------------------------------------------------------
    d  = find(P,1,'first');                % depth on this ray
    if d > PG.Nd
        o = false(PG.Nc,PG.Nd);
        o(1,:) = true;                     % all empty
    else
        o = false(PG.Nc,d);
        o(1,1:end - 1) = true;             % all empty
        o(2:end,end)   = true;             % until first occluder
    end

    % convert to cell array
    %----------------------------------------------------------------------
    d  = min(size(o,2),numel(f));
    O  = cell(1,d);
    for j = 1:d
        O{j} = o(f{j},j);
    end
    r  = 1:d;

end

return

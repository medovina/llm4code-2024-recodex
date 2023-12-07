% A Prolog wrapper for AnonSys.
%

% Print a single var/val pair, e.g. "X = [3, 6]".
% The call to numbervars modifies singleton variables such as _56094
% so that they will be printed as _.
anonsys_showVar(Var, Val, N) :-
    (N > 1 -> write(', ') ; true), write(Var), write(' = '),
    numbervars(Val, 0, _, [singletons(true)]),
    write_term(Val, [numbervars]).

% Print a set of var/val pairs, e.g. "X = [3, 6], Y = [2, 5]".
anonsys_showVars(VarNames, Solution) :-
    length(VarNames, N), numlist(1, N, Nums),
    maplist(anonsys_showVar, VarNames, Solution, Nums), nl.

% helper predicate for unzipping
anonsys_eq(A = B, A, B).

% Handle queries with no variables: just print 'true' or 'false'.
anonsys_perform_query(Query, []) :-
    (call(Query) -> writeln('true') ; writeln('false')).

% Handle queries with variables.
% We use findall to gather all solutions into a single list.  A query may contain
% anonymous variables ('_'), which will not appear in the list VN.  We use
% findall rather than bagof, because bagof will succeed once for each separate value
% of an anonymous variable.  findall succeeds only once and generates a single list.
anonsys_perform_query(Query, VN) :-
    VN = [_ | _],                  % matches a non-empty list, e.g. ['X'=_8242, 'Y'=_8248]
    maplist(anonsys_eq, VN, Names, Vars),  % unzip into Names = ['X', 'Y'], Vars = [_8242, _8248]
    (findall(Vars, Query, Solutions) -> true ; Solutions = []),  % find all solutions
    sort(Solutions, SortedSolutions),
    maplist(anonsys_showVars(Names), SortedSolutions).     % print them nicely

% Read a query from standard input, gather its solutions, and print them to standard output.
anonsys_main :-
  prompt(_, ''),    % disable input prompt
  read_term(Query, [variable_names(VN)]),
  anonsys_perform_query(Query, VN),
  halt.

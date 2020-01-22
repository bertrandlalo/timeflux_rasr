"""pymanopt vendoring addition for hessian and gradien verification
To be committed in pymanopt (and therefore this code will be obsolete)

Author: Sylvain Chevallier, December 2019
"""

# checkgrad and checkhess
import autograd.numpy as np
import matplotlib.pyplot as plt
from pymanopt.core.problem import Problem
from pymanopt.solvers import TrustRegions
from pymanopt.manifolds import Grassmann


def identify_linear_piece(x, y, window_length):
    """Identify a segment of the curve (x, y) that appears to be linear.

    This function attempts to identify a contiguous segment of the curve
    defined by the vectors x and y that appears to be linear. A line is fit
    through the data over all windows of length window_length and the best
    fit is retained. The output specifies the range of indices such that
    x(segment) is the portion over which (x, y) is the most linear and the
    output poly specifies a first order polynomial that best fits (x, y) over
    that segment, following the usual matlab convention for polynomials
    (highest degree coefficients first).

    See also: checkdiff checkgradient checkhessian
    """
    residues = np.zeros(len(x) - window_length)
    polys = np.zeros(shape=(2, len(residues)))
    for i in range(len(residues)):
        segment = range(i, (i + window_length) + 1)
        poly, residuals, _, _, _ = np.polyfit(x[segment], y[segment],
                                              1, full=True)
        residues[i] = np.linalg.norm(residuals)
        polys[:, i] = poly
    best = np.argmin(residues)
    segment = range(best, best + window_length + 1)
    poly = polys[:, best]
    return segment, poly


def directionalDerivative(problem, x, d):
    """Computes the directional derivative of the cost function at x along d.

    Returns the derivative at x along d of the cost function described in the
    problem structure.
    """
    if hasattr(problem.manifold, 'diff'):
        diff = problem.manifold.diff(x, d)
    else:
        grad = problem.manifold.grad(x)
        diff = problem.manifold.inner(x, grad, d)
    return diff


def checkdiff(problem, x=None, d=None, force_gradient=False):
    """Checks the consistency of the cost function and directional derivatives.

    checkdiff performs a numerical test to check that the directional
    derivatives defined in the problem structure agree up to first order with
    the cost function at some point x, along some direction d. The test is
    based on a truncated Taylor series (see online pymanopt documentation).

    Both x and d are optional and will be sampled at random if omitted.

    See also: checkgradient checkhessian

    If force_gradient is True, then the function will call getGradient and
    infer the directional derivative, rather than call getDirectionalDerivative
    directly. This is used by checkgradient.
    """
    #  If x and / or d are not specified, pick them at random.
    if d is not None and x is None:
        raise ValueError("If d is provided, x must be too, since d is tangent at x.")
    if x is None:
        x = problem.manifold.rand()
    elif x.shape != problem.manifold.rand().shape:
        x = np.reshape(x, problem.manifold.rand().shape)
    if d is None:
        d = problem.manifold.randvec(x)
    elif d.shape != problem.manifold.randvec(x).shape:
        d = np.reshape(d, problem.manifold.randvec(x).shape)

    # Compute the value f0 at f and directional derivative at x along d.
    f0 = problem.cost(x)
    if not force_gradient:
        df0 = directionalDerivative(problem, x, d)
        pass
    else:
        grad = problem.grad(x)
        df0 = problem.manifold.inner(x, grad, d)

    #  Pick a stepping function: exponential or retraction?
    if hasattr(problem.manifold, 'exp'):
        stepper = problem.manifold.exp
    else:
        # No need to issue a warning: to check the gradient, any retraction
        # (which is first-order by definition) is appropriate.
        stepper = problem.manifold.retr

    # Compute the value of f at points on the geodesic (or approximation
    # of it) originating from x, along direction d, for stepsizes in a
    # large range given by h.
    h = np.logspace(-8, 0, 51)
    value = np.zeros_like(h)
    for i, h_k in enumerate(h):
        y = stepper(x, h_k * d)
        value[i] = problem.cost(y)

    # Compute the linear approximation of the cost function using f0 and
    # df0 at the same points.
    model = np.polyval([df0, f0], h)

    # Compute the approximation error
    err = np.abs(model - value)

    if not np.all(err < 1e-12):
        isModelExact = False
        # In a numerically reasonable neighborhood, the error should
        # decrease as the square of the stepsize, i.e., in loglog scale,
        # the error should have a slope of 2.
        window_len = 10
        segment, poly = identify_linear_piece(np.log10(h), np.log10(err),
                                              window_len)
    else:
        isModelExact = True
        # The 1st order model is exact: all errors are (numerically) zero
        # Fit line from all points, use log scale only in h.
        segment = range(len(h))
        poly = np.polyfit(np.log10(h), err, 1)
        # Set mean error in log scale for plot.
        poly[-1] = np.log10(poly[-1])

    # plot
    # if isModelExact:
    #     plt.title('Directional derivative check.'
    #               'It seems the linear model is exact:'
    #               'Model error is numerically zero for all h.')
    # else:
    #     plt.title('Directional derivative check. The slope of the'
    #               'continuous line should match that of the dashed'
    #               '(reference) line over at least a few orders of'
    #               'magnitude for h.')
    return h, err, segment, poly, isModelExact


def checkgradient(problem, x=None, d=None):
    """Checks the consistency of the cost function and the gradient.

    checkgradient performs a numerical test to check that the gradient
    defined in the problem structure agrees up to first order with the cost
    function at some point x, along some direction d. The test is based on a
    truncated Taylor series (see online pymanopt documentation).

    It is also tested that the gradient is indeed a tangent vector.

    Both x and d are optional and will be sampled at random if omitted.
    """
    #  If x and / or d are not specified, pick them at random.
    if d is not None and x is None:
        raise ValueError("If d is provided, x must be too,"
                         "since d is tangent at x.")
    if x is None:
        x = problem.manifold.rand()
    elif x.shape != problem.manifold.rand().shape:
        x = np.reshape(x, problem.manifold.rand().shape)
    if d is None:
        d = problem.manifold.randvec(x)
    elif d.shape != problem.manifold.randvec(x).shape:
        d = np.reshape(d, problem.manifold.randvec(x).shape)

    h, err, segment, poly, isModelExact = checkdiff(problem, x, d,
                                                    force_gradient=True)

    # plot
    plt.figure()
    plt.loglog(h, err)
    plt.xlabel('h')
    plt.ylabel('Approximation error')
    plt.loglog(h[segment], 10 ** np.polyval(poly, np.log10(h[segment])),
               linewidth=3)
    plt.autoscale(False)
    plt.plot([1e-8, 1e0], [1e-8, 1e8], linestyle="--", color='k')

    plt.title('Gradient check\nThe slope of the continuous line '
              'should match that of the dashed\n(reference) line '
              'over at least a few orders of magnitude for h.')
    plt.show()

    # Try to check that the gradient is a tangent vector
    if hasattr(problem.manifold, 'tangent'):
        # problem_cp = Problem(manifold=problem.manifold, cost=problem.cost)
        # grad=problem_cp.grad(x)
        grad = problem.grad(x)
        pgrad = problem.manifold.tangent(x, grad)
        residual = grad - pgrad
        err = problem.manifold.norm(x, residual)
        print('The residual should be 0, or very close. '
              'Residual: {:g}.'.format(err))
        print('If it is far from 0, then the gradient '
              'is not in the tangent space.')
    else:
        # print('Unfortunately, pymanopt was unable to verify that the gradient'
        #       'is indeed a tangent vector. Please verify this manually or'
        #       'implement the ''tangent'' function in your manifold structure.')
        problem_cp = Problem(manifold=problem.manifold, cost=problem.cost)
        grad = problem_cp.grad(x)
        pgrad = problem.manifold.proj(x, grad)
        residual = grad - pgrad
        err = problem.manifold.norm(x, residual)
        print('The residual should be 0, or very close. '
              'Residual: {:g}.'.format(err))
        print('If it is far from 0, then the gradient '
              'is not in the tangent space.')



def nonlinear_eigh(L, p, alpha=1):
    """Example of nonlinear eigenvalue problem: total energy minimization.

    This example demonstrates how to use the Grassmann geometry factory
    to solve the nonlinear eigenvalue problem as the optimization problem:
    minimize 0.5*trace(X'*L*X) + (alpha/4)*(rho(X)*L\(rho(X)))
    over X such that X'*X = Identity,
    where L is of size n-by-n,
    X is an n-by-k matrix, and
    rho(X) is the diagonal part of X*X'.

    Parameters
    ----------
    L: ndarray, shape (n, n)
        A discrete Laplacian operator: the SPD covariance matrix
    alpha: float
        is a given constant for optimization problem
    p: int
        determines how many eigenvalues are returned

    Returns
    ----------


    Reference
    ----------
    "A Riemannian Newton Algorithm for Nonlinear Eigenvalue Problems",
    Zhi Zhao, Zheng-Jian Bai, and Xiao-Qing Jin,
    SIAM Journal on Matrix Analysis and Applications, 36(2), 752-774, 2015.

    Author
    ----------
    Ported to python by Louis Korczowski, December 2019
    based on Bamdev Mishra's Matlab implementation for manopt, June 19, 2015
    """

    # Make sure the input matrix is square and symmetric
    n = L.shape[0]
    assert type(L) == np.ndarray, 'A must be a numpy array.'
    assert np.isreal(L).all(), 'A must be real.'
    assert L.shape[1] == n, 'A must be square.'
    assert np.linalg.norm(L-np.transpose(L)) < n * np.spacing(1), 'A must be symmetric.'
    assert p <= n, 'p must be smaller than n.'

    # Define the cost on the Grassmann manifold
    Gr = Grassmann(n, p)

    # defined cost function
    def cost(X):  # matlab comparison with simulation OK <LK>
        rhoX = np.sum(X ** 2, axis=1)
        return 0.5 * np.trace(np.dot(np.transpose(X), np.dot(L, X))) + \
               (alpha/4) * np.dot(np.transpose(rhoX), np.dot(np.linalg.inv(L), rhoX))

    def egrad(X): # checkgradien validation (delta = 1e-15)
        rhoX = np.sum(X ** 2, axis=1)
        return np.dot(L, X) + alpha * np.dot(np.diag(np.dot(np.linalg.inv(L), rhoX)), X)

    def ehess(X, U):
        rhoX = np.sum(X ** 2, axis=1)
        rhoXdot = 2 * np.sum(X*U, axis=1)
        return np.dot(L, U) + \
               alpha * np.dot(np.diag(np.dot(np.linalg.inv(L), rhoXdot)), X) + \
               alpha * np.dot(np.diag(np.dot(np.linalg.inv(L), rhoX)), U)



    # Setup the problem
    problem = Problem(manifold=Gr, cost=cost, egrad=egrad, ehess=ehess)

    # Create a solver object
    solver = TrustRegions()

    # Solve
    # Xopt = solver.solve(problem, Delta_bar=8*np.sqrt(p))
    Xopt = solver.solve(problem)

    return Xopt

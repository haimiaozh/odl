# Copyright 2014-2016 The ODL development group
#
# This file is part of ODL.
#
# ODL is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ODL is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ODL.  If not, see <http://www.gnu.org/licenses/>.

"""Test for the default functionals."""

# External
import numpy as np
import pytest

# Internal
import odl
from odl.util.testutils import all_almost_equal, almost_equal, noise_element

# Places for the accepted error when comparing results
PLACES = 8


space_params = ['r10', 'uniform_discr']
space_ids = [' space = {}'.format(p.ljust(10)) for p in space_params]


@pytest.fixture(scope="module", ids=space_ids, params=space_params)
def space(request, fn_impl):
    name = request.param.strip()

    if name == 'r10':
        return odl.rn(10, impl=fn_impl)
    elif name == 'uniform_discr':
        return odl.uniform_discr(0, 1, 7, impl=fn_impl)


def test_L1_norm(space):
    """Test the L1-norm."""
    func = odl.solvers.L1Norm(space)
    x = noise_element(space)

    # Evaluation of the functional
    expected_result = (np.abs(x)).inner(space.one())
    assert almost_equal(func(x), expected_result, places=PLACES)

    # The gradient is the sign-function
    expected_result = np.sign(x)
    assert all_almost_equal(func.gradient(x), expected_result,
                            places=PLACES)

    # The proximal operator
    sigma = np.random.rand()
    # Explicit computation:      |  x_i - sigma, x_i > sigma
    #                      z_i = {  0,           -sigma <= x_i <= sigma
    #                            |  x_i + sigma,     x_i < -sigma
    tmp = np.zeros(space.size)
    orig = x.asarray()
    tmp[orig > sigma] = orig[orig > sigma] - sigma
    tmp[orig < -sigma] = orig[orig < -sigma] + sigma
    expected_result = space.element(tmp)
    assert all_almost_equal(func.proximal(sigma)(x), expected_result,
                            places=PLACES)

    # The convex conjugate functional
    cc_func = func.convex_conj

    # Evaluation of convex conjugate
    # Explicit calculation: 0 if |x|_inf <= 1, infty else
    norm_larger_than_one = 1.1 * x / np.max(np.abs(x))
    assert cc_func(norm_larger_than_one) == np.inf

    norm_less_than_one = 0.9 * x / np.max(np.abs(x))
    assert cc_func(norm_less_than_one) == 0

    norm_equal_to_one = x / np.max(np.abs(x))
    assert cc_func(norm_equal_to_one) == 0

    # The gradient of the convex conjugate (not implemeted)
    with pytest.raises(NotImplementedError):
        cc_func.gradient

    # The proximal of the convex conjugate
    # Explicit computation: x / max(1, |x|)
    expected_result = x / np.maximum(1, np.abs(x))
    assert all_almost_equal(cc_func.proximal(sigma)(x), expected_result,
                            places=PLACES)

    # The biconjugate, which is the functional itself since it is proper,
    # convex and lower-semicontinuous
    cc_cc_func = cc_func.convex_conj
    assert isinstance(cc_cc_func, odl.solvers.L1Norm)


def test_indicator_lp_unit_ball(space):
    """Test for indicator function on unit ball."""
    x = noise_element(space)
    one_elem = space.one()

    # Used du to numerical errors
    accuracy = 1 - 10**(-PLACES)

    # Exponent = 1
    exponent = 1
    func = odl.solvers.IndicatorLpUnitBall(space, exponent)

    # Evaluation of the functional
    one_norm = np.abs(x).inner(one_elem)

    norm_larger_than_one = 1.1 * x / one_norm
    assert func(norm_larger_than_one) == np.inf

    norm_less_than_one = 0.9 * x / one_norm
    assert func(norm_less_than_one) == 0

    # Slightly less than 1 due to potential numerical errors
    norm_equal_to_one = accuracy * x / one_norm
    assert func(norm_equal_to_one) == 0

    # Negative, noninteger power
    exponent = -1 * np.random.rand()
    func = odl.solvers.IndicatorLpUnitBall(space, exponent)

    # Evaluation of the functional
    p_norm_x = np.power(np.power(np.abs(x), exponent).inner(one_elem),
                        1 / exponent)

    norm_larger_than_one = 1.1 * x / p_norm_x
    assert func(norm_larger_than_one) == np.inf

    norm_less_than_one = 0.9 * x / p_norm_x
    assert func(norm_less_than_one) == 0

    # Slightly less than 1 due to potential numerical errors
    norm_equal_to_one = accuracy * x / p_norm_x
    assert func(norm_equal_to_one) == 0


def test_L2_norm(space):
    """Test the L2-norm."""
    func = odl.solvers.L2Norm(space)
    x = noise_element(space)

    # Evaluation of the functional
    expected_result = np.sqrt((x**2).inner(space.one()))
    assert almost_equal(func(x), expected_result, places=PLACES)

    # The gradient
    expected_result = x / x.norm()
    assert all_almost_equal(func.gradient(x), expected_result,
                            places=PLACES)

    # Testing gradient for zero element
    with pytest.raises(ValueError):
        func.gradient(func.domain.zero())

    # The proximal operator
    sigma = np.random.rand()
    # Explicit computation: x * (1 - sigma/||x||) if ||x|| > 1, 0 else
    norm_less_than_sigma = 0.9 * sigma * x / x.norm()
    assert all_almost_equal(func.proximal(sigma)(norm_less_than_sigma),
                            space.zero(), places=PLACES)

    norm_larger_than_sigma = 1.1 * sigma * x / x.norm()
    expected_result = (norm_larger_than_sigma *
                       (1.0 - sigma / norm_larger_than_sigma.norm()))
    assert all_almost_equal(func.proximal(sigma)(norm_larger_than_sigma),
                            expected_result, places=PLACES)

    # The convex conjugate functional
    cc_func = func.convex_conj

    # Evaluation of convex conjugate
    # Explicit calculation: 0 if ||x|| < 1, infty else
    norm_larger_than_one = 1.1 * x / x.norm()
    assert cc_func(norm_larger_than_one) == np.inf

    norm_less_than_one = 0.9 * x / x.norm()
    assert cc_func(norm_less_than_one) == 0

    # The gradient of the convex conjugate (not implemeted)
    with pytest.raises(NotImplementedError):
        cc_func.gradient

    # The proximal of the convex conjugate
    # Explicit calculation: x if ||x||_2 < 1, x/||x|| else.
    if x.norm() < 1:
        expected_result = x
    else:
        expected_result = x / x.norm()
    assert all_almost_equal(cc_func.proximal(sigma)(x), expected_result,
                            places=PLACES)

    # The biconjugate, which is the functional itself since it is proper,
    # convex and lower-semicontinuous
    cc_cc_func = cc_func.convex_conj
    assert isinstance(cc_cc_func, odl.solvers.L2Norm)


def test_L2_norm_squared(space):
    """Test the squared L2-norm."""
    func = odl.solvers.L2NormSquared(space)
    x = noise_element(space)

    # Evaluation of the functional
    expected_result = (x**2).inner(space.one())
    assert almost_equal(func(x), expected_result, places=PLACES)

    # The gradient
    expected_result = 2.0 * x
    assert all_almost_equal(func.gradient(x), expected_result,
                            places=PLACES)

    # The proximal operator
    sigma = np.random.rand()
    expected_result = x / (1 + 2.0 * sigma)
    assert all_almost_equal(func.proximal(sigma)(x), expected_result,
                            places=PLACES)

    # The convex conjugate functional
    cc_func = func.convex_conj

    # Evaluation of convex conjugate
    expected_result = x.norm()**2 / 4.0
    assert almost_equal(cc_func(x), expected_result, places=PLACES)

    # The gradient of the convex conjugate (not implemeted)
    expected_result = x / 2.0
    assert all_almost_equal(cc_func.gradient(x), expected_result,
                            places=PLACES)

    # The proximal of the convex conjugate
    expected_result = x / (1 + sigma / 2.0)
    assert all_almost_equal(cc_func.proximal(sigma)(x), expected_result,
                            places=PLACES)

    # The biconjugate, which is the functional itself since it is proper,
    # convex and lower-semicontinuous
    cc_cc_func = cc_func.convex_conj

    # Check that they evaluate the same
    assert almost_equal(cc_cc_func(x), func(x), places=PLACES)

    # Check that they evaluate the gradient the same
    assert all_almost_equal(cc_cc_func.gradient(x), func.gradient(x),
                            places=PLACES)


def test_constant_functional(space):
    """Test the constant functional."""
    constant = np.random.randn()
    func = odl.solvers.ConstantFunctional(space, constant=constant)
    x = noise_element(space)

    # Checking that constant is stored correctly
    assert func.constant == constant

    # Evaluation of the functional
    expected_result = constant
    assert almost_equal(func(x), expected_result, places=PLACES)

    # The gradient
    # Given by the zero-operator
    assert isinstance(func.gradient, odl.ZeroOperator)

    # The proximal operator
    sigma = np.random.rand()
    # This is the identity operator
    assert isinstance(func.proximal(sigma), odl.IdentityOperator)

    # The convex conjugate functional
    cc_func = func.convex_conj

    # Evaluation of convex conjugate
    # Explicit calculation: -constant if x=0, infty else
    assert cc_func(x) == np.inf
    assert cc_func(space.zero()) == -constant

    # The gradient of the convex conjugate (not implemeted)
    with pytest.raises(NotImplementedError):
        cc_func.gradient

    # The proximal of the convex conjugate
    sigma = np.random.rand()
    # This is the zero operator
    assert isinstance(cc_func.proximal(sigma), odl.ZeroOperator)

    # The biconjugate, which is the functional itself since it is proper,
    # convex and lower-semicontinuous
    expected_functional = odl.solvers.ConstantFunctional(space, constant)
    cc_cc_func = cc_func.convex_conj
    assert isinstance(cc_cc_func, type(expected_functional))


def test_zero_functional(space):
    """Test the zero functional."""
    assert isinstance(odl.solvers.ZeroFunctional(space),
                      odl.solvers.ConstantFunctional)
    assert odl.solvers.ZeroFunctional(space).constant == 0


if __name__ == '__main__':
    pytest.main(str(__file__.replace('\\', '/')) + ' -v')
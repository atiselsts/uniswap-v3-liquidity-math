#!/usr/bin/env python3
"""

See the technical note "Liquidity Math in Uniswap v3" and the Uniswap v3 whitepaper
for the description of the purpose of this code.

"""

#
# Liquidity math adapted from https://github.com/Uniswap/uniswap-v3-periphery/blob/main/contracts/libraries/LiquidityAmounts.sol
#

def get_liquidity_0(x, sa, sb):
    return x * sa * sb / (sb - sa)

def get_liquidity_1(y, sa, sb):
    return y / (sb - sa)

def get_liquidity(x, y, sp, sa, sb):
    if sp <= sa:
        liquidity = get_liquidity_0(x, sa, sb)
    elif sp < sb:
        liquidity0 = get_liquidity_0(x, sp, sb)
        liquidity1 = get_liquidity_1(y, sa, sp)
        liquidity = min(liquidity0, liquidity1)
    else:
        liquidity = get_liquidity_1(y, sa, sb)
    return liquidity


#
# Calculate x and y given liquidity and price range
#
def calculate_x(L, sp, sa, sb):
    sp = max(min(sp, sb), sa)     # if the price is outside the range, use the range endpoints instead
    return L * (sb - sp) / (sp * sb)

def calculate_y(L, sp, sa, sb):
    sp = max(min(sp, sb), sa)     # if the price is outside the range, use the range endpoints instead
    return L * (sp - sa)


#
# Two different ways how to calculate p_a. calculate_a1() uses liquidity as an input, calculate_a2() does not.
#
def calculate_a1(L, sp, sb, x, y):
    # https://www.wolframalpha.com/input/?i=solve+L+%3D+y+%2F+%28sqrt%28P%29+-+a%29+for+a
    # sqrt(a) = sqrt(P) - y / L
    return (sp - y / L) ** 2

def calculate_a2(sp, sb, x, y):
    # https://www.wolframalpha.com/input/?i=solve+++x+sqrt%28P%29+sqrt%28b%29+%2F+%28sqrt%28b%29++-+sqrt%28P%29%29+%3D+y+%2F+%28sqrt%28P%29+-+a%29%2C+for+a
    # sqrt(a) = (y/sqrt(b) + sqrt(P) x - y/sqrt(P))/x
    #    simplify:
    # sqrt(a) = y/(sqrt(b) x) + sqrt(P) - y/(sqrt(P) x)
    sa = y / (sb * x) + sp - y / (sp * x)
    return sa ** 2

#
# Two different ways how to calculate p_b. calculate_b1() uses liquidity as an input, calculate_b2() does not.
#
def calculate_b1(L, sp, sa, x, y):
    # https://www.wolframalpha.com/input/?i=solve+L+%3D+x+sqrt%28P%29+sqrt%28b%29+%2F+%28sqrt%28b%29+-+sqrt%28P%29%29+for+b
    # sqrt(b) = (L sqrt(P)) / (L - sqrt(P) x)
    return ((L * sp) / (L - sp * x)) ** 2

def calculate_b2(sp, sa, x, y):
    # find the square root of b:
    # https://www.wolframalpha.com/input/?i=solve+++x+sqrt%28P%29+b+%2F+%28b++-+sqrt%28P%29%29+%3D+y+%2F+%28sqrt%28P%29+-+sqrt%28a%29%29%2C+for+b
    # sqrt(b) = (sqrt(P) y)/(sqrt(a) sqrt(P) x - P x + y)
    P = sp ** 2
    return (sp * y / ((sa * sp - P) * x + y)) ** 2

#
# Calculating c and d
#
def calculate_c(p, d, x, y):
    return y / ((d - 1) * p * x + y)

def calculate_d(p, c, x, y):
    return 1 + y * (1 - c) / (c * p * x)


#
# Test a known good combination of values against the functions provided above.
#
# Some errors are expected because:
#  -- the floating point math is meant for simplicity, not accurate calculations!
#  -- ticks and tick ranges are ignored for simplicity
#  -- the test values taken from Uniswap v3 UI and are approximate
#
def test(x, y, p, a, b):
    sp = p ** 0.5
    sa = a ** 0.5
    sb = b ** 0.5

    L = get_liquidity(x, y, sp, sa, sb)
    print("L: {:.2f}".format(L))

    ia = calculate_a1(L, sp, sb, x, y)
    error = 100.0 * (1 - ia / a)
    print("a: {:.2f} vs {:.2f}, error {:.6f}%".format(a, ia, error))

    ia = calculate_a2(sp, sb, x, y)
    error = 100.0 * (1 - ia / a)
    print("a: {:.2f} vs {:.2f}, error {:.6f}%".format(a, ia, error))

    ib = calculate_b1(L, sp, sa, x, y)
    error = 100.0 * (1 - ib / b)
    print("b: {:.2f} vs {:.2f}, error {:.6f}%".format(b, ib, error))

    ib = calculate_b2(sp, sa, x, y)
    error = 100.0 * (1 - ib / b)
    print("b: {:.2f} vs {:.2f}, error {:.6f}%".format(b, ib, error))


    c = sb / sp
    d = sa / sp
    
    ic = calculate_c(p, d, x, y)
    error = 100.0 * (1 - ic / c)
    print("c^2: {:.2f} vs {:.2f}, error {:.6f}%".format(c**2, ic**2, error))

    id = calculate_d(p, c, x, y)
    error = 100.0 * (1 - id**2 / d**2)
    print("d^2: {:.2f} vs {:.2f}, error {:.6f}%".format(d**2, id**2, error))


    ix = calculate_x(L, sp, sa, sb)
    error = 100.0 * (1 - ix / x)
    print("x: {:.2f} vs {:.2f}, error {:.6f}%".format(x, ix, error))

    iy = calculate_y(L, sp, sa, sb)
    error = 100.0 * (1 - iy / y)
    print("y: {:.2f} vs {:.2f}, error {:.6f}%".format(y, iy, error))
    print("")


def test_1():
    print("test case 1")
    p = 20.0
    a = 19.027
    b = 25.993
    x = 1
    y = 4
    test(x, y, p, a, b)

def test_2():
    print("test case 2")
    p = 3227.02
    a = 1626.3
    b = 4846.3
    x = 1
    y = 5096.06
    test(x, y, p, a, b)

def tests():
    test_1()
    test_2()

#
# Example 1 from the technical note
#
def example_1():
    print("Example 1: how much of USDC I need when providing 2 ETH at this price and range?")
    p = 2000
    a = 1500
    b = 2500
    x = 2

    sp = p ** 0.5
    sa = a ** 0.5
    sb = b ** 0.5
    L = get_liquidity_0(x, sp, sb)
    y = calculate_y(L, sp, sa, sb)
    print("amount of USDC y={:.2f}".format(y))

    # demonstrate that with the calculated y value, the given range is correct
    c = sb / sp
    d = sa / sp
    ic = calculate_c(p, d, x, y)
    id = calculate_d(p, c, x, y)
    C = ic ** 2
    D = id ** 2
    print("p_a={:.2f} ({:.2f}% of P), p_b={:.2f} ({:.2f}% of P)".format(
        D * p, D * 100, C * p, C * 100))
    print("")

#
# Example 2 from the technical note
#
def example_2():
    print("Example 2: I have 2 ETH and 4000 USDC, range top set to 3000 USDC. What's the bottom of the range?")
    p = 2000
    b = 3000
    x = 2
    y = 4000

    sp = p ** 0.5
    sb = b ** 0.5

    a = calculate_a2(sp, sb, x, y)
    print("lower bound of the price p_a={:.2f}".format(a))
    print("")


#
# Example 3 from the technical note
#
def example_3():
    print("Example 3: Using the position created in Example 2, what are asset balances at 2500 USDC per ETH?")
    p = 2000
    a = 1333.33
    b = 3000
    x = 2
    y = 4000

    sp = p ** 0.5
    sa = a ** 0.5
    sb = b ** 0.5
    # calculate the initial liquidity
    L = get_liquidity(x, y, sp, sa, sb)

    P1 = 2500
    sp1 = P1 ** 0.5

    x1 = calculate_x(L, sp1, sa, sb)
    y1 = calculate_y(L, sp1, sa, sb)
    print("Amount of ETH x={:.2f} amount of USDC y={:.2f}".format(x1, y1))

    # alternative way, directly based on the whitepaper

    # this delta math only works if the price is in the range (including at its endpoints),
    # so limit the square roots of prices to the range first
    sp = max(min(sp, sb), sa)
    sp1 = max(min(sp1, sb), sa)

    delta_p = sp1 - sp
    delta_inv_p = 1/sp1 - 1/sp
    delta_x = delta_inv_p * L
    delta_y = delta_p * L
    x1 = x + delta_x
    y1 = y + delta_y
    print("delta_x={:.2f} delta_y={:.2f}".format(delta_x, delta_y))
    print("Amount of ETH x={:.2f} amount of USDC y={:.2f}".format(x1, y1))


def examples():
    example_1()
    example_2()
    example_3()

def main():
    # test with some values taken from Uniswap UI
    tests()
    # demonstrate the examples given in the paper
    examples()

if __name__ == "__main__":
    main()

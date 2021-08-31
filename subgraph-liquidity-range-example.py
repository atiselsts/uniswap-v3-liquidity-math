#!/usr/bin/env python3

#
# Example that shows the full range of the current liquidity distribution
# in the 0.3% USDC/ETH pool using data from the Uniswap v3 subgraph.
#

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

POOL_ID = "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8"

TICK_BASE = 1.0001

# If set to true, all tick in the pool's liquidity range are printed.
# Otherwise, only ticks with nonzero liquidityNet are printed.
# Nonzero liquidityNet means that the amount of liquidity changes on the tick boundary.
# Setting this to false will make the output shorter, especially for pools with huge liquidity ranges.
PRINT_ALL_TICKS = False

pool_query = """query {
  pools (where: {id: "%POOL_ID"}){
    tick
    sqrtPrice
    liquidity
    feeTier
    token0 {
      symbol
      decimals
    }
    token1 {
      symbol
      decimals
    }
  }
}"""

tick_query = """query {
  ticks(skip:%NUM_SKIP, where:{pool:"%POOL_ID"}) {
    tickIdx
    liquidityNet
  }
}"""


def tick_to_price(tick):
    return TICK_BASE ** tick

# Not all ticks can be initialized. Tick spacing is determined by the pool's fee tier.
def fee_tier_to_tick_spacing(fee_tier):
    return {
        500: 10,
        3000: 60,
        10000: 200
    }.get(fee_tier, 60)


client = Client(
    transport=RequestsHTTPTransport(
        url='https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3',
        verify=True,
        retries=5,
    ))

# get pool info
try:
    response = client.execute(gql(
        pool_query.replace("%POOL_ID", POOL_ID)))

    pool = response['pools'][0]
    current_tick = int(pool["tick"])
    tick_spacing = fee_tier_to_tick_spacing(int(pool["feeTier"]))

    token0 = pool["token0"]["symbol"]
    token1 = pool["token1"]["symbol"]
    decimals0 = int(pool["token0"]["decimals"])
    decimals1 = int(pool["token1"]["decimals"])
except Exception as ex:
    print("got exception", ex)

# get tick info
tick_mapping = {}
num_skip = 0
try:
    while True:
        response = client.execute(gql(
            tick_query.replace("%NUM_SKIP", str(num_skip)).replace("%POOL_ID", POOL_ID)))
        if len(response["ticks"]) == 0:
            break
        num_skip += len(response["ticks"])
        for item in response["ticks"]:
            tick_mapping[int(item["tickIdx"])] = int(item["liquidityNet"])
except Exception as ex:
    print(ex)

    
# Start from zero; if we were iterating from the current tick, would start from the pool's total liquidity
liquidity = 0

# Find the boundaries of the price range
min_tick = min(tick_mapping.keys())
max_tick = max(tick_mapping.keys())

current_range_bottom_tick = current_tick // tick_spacing * tick_spacing

# Sum up all tokens in the pool
total_amount0 = 0
total_amount1 = 0

# Iterate over the tick map starting from the bottom
tick = min_tick
while tick < max_tick:
    liquidity_delta = tick_mapping.get(tick, 0)
    liquidity += liquidity_delta

    should_print_tick = PRINT_ALL_TICKS or liquidity_delta != 0

    # Compute square roots of prices corresponding to the bottom and top ticks
    bottom_tick = tick
    top_tick = tick + tick_spacing
    sa = tick_to_price(bottom_tick // 2)
    sb = tick_to_price(top_tick // 2)

    price = tick_to_price(tick)
    adjusted_price = price / (10 ** (decimals1 - decimals0))
    if should_print_tick:
        print("tick={} price={:.6f} {} for {}".format(tick, 1 / adjusted_price, token0, token1))

    # Compute the real amounts of both tokens potentially present in the range
    amount0 = liquidity * (sb - sa) / (sa * sb)
    amount1 = liquidity * (sb - sa)

    adjusted_amount0 = amount0 / (10 ** decimals0)
    adjusted_amount1 = amount1 / (10 ** decimals1)

    if tick < current_range_bottom_tick:
        # Only asset1 locked
        total_amount1 += adjusted_amount1
        if should_print_tick:
            print("        {:.2f} {} locked (potentially worth {:.2f} {})".format(adjusted_amount1, token1, adjusted_amount0, token0))

    elif tick == current_range_bottom_tick:
        # Always print the current tick. It normally has both assets locked
        print("        Current tick, both assets present!")

        # 1. Print the real amounts of the two assets needed to be swapped to move out of the current tick range
        current_sqrt_price = tick_to_price(current_tick / 2)
        amount0actual = liquidity * (sb - current_sqrt_price) / (current_sqrt_price * sb)
        amount1actual = liquidity * (current_sqrt_price - sa)
        adjusted_amount0actual = amount0actual / 10 ** decimals0
        adjusted_amount1actual = amount1actual / 10 ** decimals1

        total_amount0 += adjusted_amount0
        total_amount1 += adjusted_amount1

        print("        {:.2f} {} and {:.2f} {} remaining in the current tick range".format(
            adjusted_amount0actual, token0, adjusted_amount1actual, token1))

        # 2. Print the amounts of the two assets that would be locked if the tick was only asset0 or asset1
        print("        potentially {:.2f} {} or {:.2f} {} in total in the current tick range".format(
            adjusted_amount0, token0, adjusted_amount1, token1))


    else:
        # Only asset0 locked
        total_amount0 += adjusted_amount0
        if should_print_tick:
            print("        {:.2f} {} locked (potentially worth {:.2f} {})".format(adjusted_amount0, token0, adjusted_amount1, token1))

    tick += tick_spacing

print("In total: {:.2f} {} and {:.2f} {}".format(
      total_amount0, token0, total_amount1, token1))

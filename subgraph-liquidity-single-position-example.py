#!/usr/bin/env python3

#
# Example that shows a single position in the 0.05% USDC/DAI pool,
# using data from the Uniswap v3 subgraph.
#

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import math
import sys

POSITION_ID = "2"

# if passed in command line, use an alternative pool ID
if len(sys.argv) > 1:
    POSITION_ID = sys.argv[1]

TICK_BASE = 1.0001

position_query = """query get_position($position_id: ID!) {
  positions(where: {id: $position_id}) {
    liquidity
    tickLower { tickIdx }
    tickUpper { tickIdx }
    pool { id }
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

# return the tick and the sqrt of the current price
pool_query = """query get_pools($pool_id: ID!) {
  pools(where: {id: $pool_id}) {
    tick
    sqrtPrice
  }
}"""

def tick_to_price(tick):
    return TICK_BASE ** tick

client = Client(
    transport=RequestsHTTPTransport(
        url='https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3',
        verify=True,
        retries=5,
    ))

# get position info
try:
    variables = {"position_id": POSITION_ID}
    response = client.execute(gql(position_query), variable_values=variables)

    if len(response['positions']) == 0:
        print("position not found")
        exit(-1)

    position = response['positions'][0]
    liquidity = int(position["liquidity"])
    tick_lower = int(position["tickLower"]["tickIdx"])
    tick_upper = int(position["tickUpper"]["tickIdx"])
    pool_id = position["pool"]["id"]

    token0 = position["token0"]["symbol"]
    token1 = position["token1"]["symbol"]
    decimals0 = int(position["token0"]["decimals"])
    decimals1 = int(position["token1"]["decimals"])

except Exception as ex:
    print("got exception while querying position data:", ex)
    exit(-1)

#print("pool id=", pool_id)

# get pool info for current price
try:
    variables = {"pool_id": pool_id}
    response = client.execute(gql(pool_query), variable_values=variables)

    if len(response['pools']) == 0:
        print("pool not found")
        exit(-1)

    pool = response['pools'][0]
    current_tick = int(pool["tick"])
    current_sqrt_price = int(pool["sqrtPrice"]) / (2 ** 96)

except Exception as ex:
    print("got exception while querying pool data:", ex)
    exit(-1)

# Compute and print the current price
current_price = tick_to_price(current_tick)
adjusted_current_price = current_price / (10 ** (decimals1 - decimals0))
print("Current price={:.6f} {} for {} at tick {}".format(adjusted_current_price, token1, token0, current_tick))

sa = tick_to_price(tick_lower / 2)
sb = tick_to_price(tick_upper / 2)

if tick_upper <= current_tick:
    # Only token1 locked
    amount0 = 0
    amount1 = liquidity * (sb - sa)
elif tick_lower < current_tick < tick_upper:
    # Both tokens present
    amount0 = liquidity * (sb - current_sqrt_price) / (current_sqrt_price * sb)
    amount1 = liquidity * (current_sqrt_price - sa)
else:
    # Only token0 locked
    amount0 = liquidity * (sb - sa) / (sa * sb)
    amount1 = 0

# print info about the position
adjusted_amount0 = amount0 / (10 ** decimals0)
adjusted_amount1 = amount1 / (10 ** decimals1)
print("  position {: 7d} in range [{},{}]: {:.2f} {} and {:.2f} {} at the current price".format(
      int(POSITION_ID), tick_lower, tick_upper,
      adjusted_amount0, token0, adjusted_amount1, token1))

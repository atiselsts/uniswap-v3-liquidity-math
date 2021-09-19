#!/usr/bin/env python3

#
# Example that prints the current virtual amounts of assets in the 0.3% USDC/ETH pool
# using liquidity data from the Uniswap v3 subgraph.
#

import json
import urllib.request
import math
import sys

# Look at the USDC/ETH 0.3% pool
POOL_ID = '0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8'

# if passed in command line, use an alternative pool ID
if len(sys.argv) > 1:
    POOL_ID = sys.argv[1]

URL = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
TICK_BASE = 1.0001

# GraphQL query to get the pool information
query = """query pools($pool_id: ID!) {
  pools (where: {id: $pool_id}) {
    tick
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

# Convert Uniswap v3 tick to a price (i.e. the ratio between the amounts of tokens: token1/token0)
def tick_to_price(tick):
    return TICK_BASE ** tick

# Not all ticks can be initialized. Tick spacing is determined by the pool's fee tier.
def fee_tier_to_tick_spacing(fee_tier):
    return {
        500: 10,
        3000: 60,
        10000: 200
    }.get(fee_tier, 60)


# Query the subgraph
req = urllib.request.Request(URL)
req.add_header('Content-Type', 'application/json; charset=utf-8')
jsondata = {"query": query, "variables": {"pool_id": POOL_ID}}
jsondataasbytes = json.dumps(jsondata).encode('utf-8')
req.add_header('Content-Length', len(jsondataasbytes))
response = urllib.request.urlopen(req, jsondataasbytes)
obj = json.load(response)
pool = obj['data']['pools'][0]

# Extract liquidity from the response
L = int(pool["liquidity"])
tick = int(pool["tick"])
tick_spacing = fee_tier_to_tick_spacing(int(pool["feeTier"]))

print("L={}".format(L))
print("tick={}".format(tick))

token0 = pool["token0"]["symbol"]
token1 = pool["token1"]["symbol"]
decimals0 = int(pool["token0"]["decimals"]) # USDC has 6 decimals
decimals1 = int(pool["token1"]["decimals"]) # WETH has 18 decimals

# Compute the tick range. This code would work as well in Python: `tick // TICK_SPACING * TICK_SPACING`
# However, using floor() is more portable.
bottom_tick = math.floor(tick / tick_spacing) * tick_spacing
top_tick = bottom_tick + tick_spacing

# Compute the current price and adjust it to a human-readable format
price = tick_to_price(tick)
adjusted_price = price / (10 ** (decimals1 - decimals0))

# Compute square roots of prices corresponding to the bottom and top ticks
sa = tick_to_price(bottom_tick // 2)
sb = tick_to_price(top_tick // 2)
sp = price ** 0.5

# Compute real amounts of the two assets
amount0 = L * (sb - sp) / (sp * sb)
amount1 = L * (sp - sa)

# Adjust them to a human-readable format
adjusted_amount0 = amount0 / 10 ** decimals0
adjusted_amount1 = amount1 / 10 ** decimals1

print("Current price: {:.6f} {} for 1 {} ({:.6f} {} for 1 {})".format(
    adjusted_price, token1, token0, 1 / adjusted_price, token0, token1))

print("Amounts at the current tick range: {:.2f} {} and {:.2f} {}".format(
    adjusted_amount0, token0, adjusted_amount1, token1))

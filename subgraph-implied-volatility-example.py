#!/usr/bin/env python3

#
# Example that shows the implied volatility on USDC/ETH 0.3% pool on the mainnet.
#

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import math
import sys
from datetime import datetime

# default pool id is the 0.3% USDC/ETH pool
POOL_ID = "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8"

# if passed in command line, use an alternative pool ID
if len(sys.argv) > 1:
    POOL_ID = sys.argv[1]

NUM_DAYS = 5

URL = 'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3'

pool_query = """query get_pools($pool_id: ID!, $num_days: Int) {
  pools(where: {id: $pool_id}) {
    tick
    liquidity
    feeTier
    poolDayData (first: $num_days, orderBy: date, orderDirection: desc) {
      volumeUSD
      date
    }
  }
}"""

def tick_to_price(tick):
    return 1.0001 ** tick

# Not all ticks can be initialized. Tick spacing is determined by the pool's fee tier.
def fee_tier_to_tick_spacing(fee_tier):
    return {
        100: 1,
        500: 10,
        3000: 60,
        10000: 200
    }.get(fee_tier, 60)

client = Client(
    transport=RequestsHTTPTransport(
        url=URL,
        verify=True,
        retries=5,
    ))

# get pool info
try:
    variables = {"pool_id": POOL_ID, "num_days": NUM_DAYS + 1}
    response = client.execute(gql(pool_query), variable_values=variables)

    if len(response['pools']) == 0:
        print("pool not found")
        exit(-1)

    pool = response['pools'][0]
    liquidity = int(pool["liquidity"])
    current_tick = int(pool["tick"])
    fee_tier = int(pool["feeTier"])
    tick_spacing = fee_tier_to_tick_spacing(fee_tier)
    # skip the newest day: not full day has passed yet
    volumes = pool["poolDayData"][1:]

except Exception as ex:
    print("got exception while querying pool data:", ex)
    exit(-1)


bottom_tick = current_tick // tick_spacing * tick_spacing
top_tick = bottom_tick + tick_spacing

sa = tick_to_price(bottom_tick // 2)
sb = tick_to_price(top_tick // 2)

# as if all position was USDC only
usd_amount_locked = liquidity * (sb - sa) / (sa * sb)
# convert taking into account USDC decimals
usd_amount_locked *= 1e-6

print(f"{usd_amount_locked:.0f} USDC locked")

# convert from bps to units
fee = fee_tier / (100 * 100)

for day_data in volumes[::-1]:
    volume_usd = float(day_data["volumeUSD"])
    iv = 2 * fee * math.sqrt(volume_usd / usd_amount_locked) * math.sqrt(365)
    dt = datetime.fromtimestamp(int(day_data["date"]))
    day = dt.strftime("%b %d, %Y")
    print(f"{day}: USDC volume={volume_usd:.0f} IV={iv:.2f}%")

import cbpro
from datetime import datetime, date, timedelta
from datetime import time as datetime_time
from time import sleep
import sys


def get_entry_price(currency, k):
    # using Volatility Breakout Strategy by Larry Williams
    yesterday = get_day_in_isoformat(1)
    yesterday_data = get_historic_data(currency, start_date=yesterday, end_date=yesterday)
    hi_lo_range = yesterday_data[0][2] - yesterday_data[0][1]  # high - low
    entry_price_ = yesterday_data[0][4] + (hi_lo_range * k)  # close - (range*k)
    return entry_price_


def get_day_in_isoformat(day):
    day = date.today() - timedelta(days=day)
    day = datetime.strptime(str(day), '%Y-%m-%d').isoformat()

    return day


def get_historic_data(currency, start_date, end_date, granularity=86400):
    historic_data = auth_client.get_product_historic_rates(currency, start_date, end_date, granularity)
    # response: [ time, low, high, open, close, volume ]
    return historic_data


def get_ma(currency, days):
    """ Moving Average """
    yesterday = get_day_in_isoformat(1)
    start_date = get_day_in_isoformat(days)

    # response: [ time, low, high, open, close, volume ]
    historic_data = get_historic_data(currency, start_date, yesterday)
    close_sums = 0

    for i in range(len(historic_data)):
        close_sums += historic_data[i][4]

    sma15 = close_sums / days
    return sma15


def get_currency_balance(currency):
    currency_id = currency_to_id[currency]
    account = auth_client.get_account(currency_id)
    return account["balance"]


if __name__ == '__main__':

    key = sys.argv[1]
    secret = sys.argv[2]
    passphrase = sys.argv[3]
    COIN_ID = sys.argv[4]

    auth_client = cbpro.AuthenticatedClient(key, secret, passphrase)

    print("auto trade start")

    currency_to_id = {}
    accounts = auth_client.get_accounts()

    for coin in accounts:
        currency_to_id[coin['currency']] = coin['id']
    market_open_time, market_reset_time = datetime_time(0, 0, 0), datetime_time(23, 59,
                                                                                50)  # Crypto currency market resets UTC 00:00:00
    entry_price, moving_average = get_entry_price(COIN_ID, k=0.5), get_ma(COIN_ID, days=15)
    now_time, now_date = datetime.utcnow().time(), datetime.now().date()

    while True:
        try:
            now_time = datetime.utcnow().time()
            if market_open_time <= now_time < market_reset_time:
                curr_date = datetime.now().date()
                market_reset = curr_date != now_date

                if market_reset:
                    now_date = curr_date
                    entry_price = get_entry_price(COIN_ID, k=0.5)
                    moving_average = get_ma(COIN_ID, days=15)

                current_price = auth_client.get_product_ticker(
                    COIN_ID)  # {trade_id, price, size, time, bid, ask, volume}

                if entry_price < float(current_price['price']) and moving_average < float(current_price['price']):
                    usd_value_in_wallet = get_currency_balance("USD")
                    if float(usd_value_in_wallet) > 0.0:
                        size = float(usd_value_in_wallet) / float(current_price["price"])
                        size = round(size, 4)
                        res = auth_client.buy(COIN_ID, order_type="market", size=str(size))
            else:
                coin, _ = COIN_ID.split("-")
                coin_balance = get_currency_balance(coin)
                if float(coin_balance) > 0.0:
                    auth_client.sell(COIN_ID, order_type="market", size=coin_balance)
        except Exception as e:
            print(e)

        sleep(5)
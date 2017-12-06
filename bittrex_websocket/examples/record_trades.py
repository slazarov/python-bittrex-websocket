from __future__ import print_function

from time import sleep

from bittrex_websocket.websocket_client import BittrexSocket


def main():
    class MySocket(BittrexSocket):
        def on_open(self):
            self.trade_history = {}

        def on_trades(self, msg):
            # Create entry for the ticker in the trade_history dict
            if msg['ticker'] not in self.trade_history:
                self.trade_history[msg['ticker']] = []
            # Add history nounce
            self.trade_history[msg['ticker']].append(msg)
            # Ping
            print('[Trades]: {}'.format(msg['ticker']))

    ws = MySocket()
    tickers = ['BTC-ETH', 'BTC-XMR']
    ws.subscribe_to_trades(tickers)

    while len(set(tickers) - set(ws.trade_history)) > 0:
        sleep(1)
        continue
    else:
        for ticker in ws.trade_history.keys():
            print('Printing {} trade history.'.format(ticker))
            for trade in ws.trade_history[ticker]:
                print(trade)
        ws.disconnect()


if __name__ == "__main__":
    main()

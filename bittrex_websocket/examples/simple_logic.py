from time import sleep

import bittrex_websocket

if __name__ == "__main__":
    class MyBittrexSocket(bittrex_websocket.BittrexSocket):
        def on_open(self):
            self.nounces = []
            self.msg_count = 0

        def on_debug(self, **kwargs):
            pass

        def on_message(self, *args, **kwargs):
            self.nounces.append(args[0])
            self.msg_count += 1


    t = ['BTC-ETH', 'ETH-1ST', 'BTC-1ST', 'BTC-NEO', 'ETH-NEO']
    ws = MyBittrexSocket(t)
    ws.run()
    while ws.msg_count < 20:
        sleep(1)
        continue
    else:
        for msg in ws.nounces:
            print(msg)
    ws.stop()

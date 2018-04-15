#!/usr/bin/python
# -*- coding: utf-8 -*-

# bittrex_websocket/_abc.py
# Stanislav Lazarov
#
# Official Bittrex documentation: https://github.com/Bittrex/beta

from abc import ABCMeta, abstractmethod


class WebSocket(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def subscribe_to_exchange_deltas(self, tickers):
        """
        Allows the caller to receive real-time updates to the state of a SINGLE market.
        Upon subscribing, the callback will be invoked with market deltas as they occur.

        This feed only contains updates to exchange state. To form a complete picture of
        exchange state, users must first call QueryExchangeState and merge deltas into
        the data structure returned in that call.

        :param tickers: A list of tickers you are interested in.
        :type tickers: []

        https://github.com/Bittrex/beta/#subscribetoexchangedeltas

        JSON Payload:
            {
                MarketName: string,
                Nonce: int,
                Buys:
                    [
                        {
                            Type: string - enum(ADD | REMOVE | UPDATE),
                            Rate: decimal,
                            Quantity: decimal
                        }
                    ],
                Sells:
                    [
                        {
                            Type: string - enum(ADD | REMOVE | UPDATE),
                            Rate: decimal,
                            Quantity: decimal
                        }
                    ],
                Fills:
                    [
                        {
                            OrderType: string,
                            Rate: decimal,
                            Quantity: decimal,
                            TimeStamp: date
                        }
                    ]
            }
        """

    @abstractmethod
    def subscribe_to_summary_deltas(self):
        """
        Allows the caller to receive real-time updates of the state of ALL markets.
        Upon subscribing, the callback will be invoked with market deltas as they occur.

        Summary delta callbacks are verbose. A subset of the same data limited to the
        market name, the last price, and the base currency volume can be obtained via
        `subscribe_to_summary_lite_deltas`.

        https://github.com/Bittrex/beta#subscribetosummarydeltas

        JSON Payload:
            {
                Nonce : int,
                Deltas :
                [
                    {
                        MarketName     : string,
                        High           : decimal,
                        Low            : decimal,
                        Volume         : decimal,
                        Last           : decimal,
                        BaseVolume     : decimal,
                        TimeStamp      : date,
                        Bid            : decimal,
                        Ask            : decimal,
                        OpenBuyOrders  : int,
                        OpenSellOrders : int,
                        PrevDay        : decimal,
                        Created        : date
                    }
                ]
            }
        """

    @abstractmethod
    def subscribe_to_summary_lite_deltas(self):
        """
        Similar to `subscribe_to_summary_deltas`.
        Shows only market name, last price and base currency volume.

        JSON Payload:
            {
                Deltas:
                    [
                        {
                            MarketName: string,
                            Last: decimal,
                            BaseVolume: decimal
                        }
                    ]
            }
        """

    @abstractmethod
    def query_summary_state(self):
        """
        Allows the caller to retrieve the full state for all markets.

        JSON payload:
            {
                Nonce: int,
                Summaries:
                    [
                        {
                            MarketName: string,
                            High: decimal,
                            Low: decimal,
                            Volume: decimal,
                            Last: decimal,
                            BaseVolume: decimal,
                            TimeStamp: date,
                            Bid: decimal,
                            Ask: decimal,
                            OpenBuyOrders: int,
                            OpenSellOrders: int,
                            PrevDay: decimal,
                            Created: date
                        }
                    ]
            }
        """

    @abstractmethod
    def query_exchange_state(self, tickers):
        """
        Allows the caller to retrieve the full order book for a specific market.

        :param tickers: A list of tickers you are interested in.
        :type tickers: []

        JSON payload:
            {
                MarketName : string,
                Nonce      : int,
                Buys:
                [
                    {
                        Quantity : decimal,
                        Rate     : decimal
                    }
                ],
                Sells:
                [
                    {
                        Quantity : decimal,
                        Rate     : decimal
                    }
                ],
                Fills:
                [
                    {
                        Id        : int,
                        TimeStamp : date,
                        Quantity  : decimal,
                        Price     : decimal,
                        Total     : decimal,
                        FillType  : string,
                        OrderType : string
                    }
                ]
            }
        """

    @abstractmethod
    def authenticate(self, api_key, api_secret):
        """
        Verifies a user’s identity to the server and begins receiving account-level notifications

        :param api_key: Your api_key with the relevant permissions.
        :type api_key: str
        :param api_secret: Your api_secret with the relevant permissions.
        :type api_secret: str

        https://github.com/slazarov/beta#authenticate
        """

    @abstractmethod
    def on_public(self, msg):
        """
        Streams all incoming messages from public delta channels.
        """

    @abstractmethod
    def on_private(self, msg):
        """
        Streams all incoming messages from private delta channels.
        """

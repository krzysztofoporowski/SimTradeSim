# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 10:11:54 2020

@author: Krzysztof Oporowski
krzysztof.oporowski@gmail.com
"""

import numbers
import pandas as pd


def define_gl(general_ledger):
    '''
    Function returns Pandas dataframe where all transactions are stored
    '''
    cols = ['id', 'open_date', 'stocks_number', 'open_price', 'open_value',
            'open_commission', 'open_total', 'SL_date', 'SL', 'close_date',
            'close_price', 'close_value', 'close_commission', 'close_total',
            'trans_result', 'max_drawdown_pln', 'max_drawdown_perc',
            'max_gain_pln', 'max_gain_proc']
    transactions = pd.DataFrame(general_ledger, columns=cols)
    return transactions


class Budget:
    '''
    Class used to store data with regard to the money avaialbe for trading
    as well as some methods to manage the free_margin
    '''

    def __init__(self, amount=1000):
        '''
        Parameters:
        ----------
        equity - to store the budget based on closed transactions
        '''
        self.equity = amount
        self.free_margin = amount

    def manage_amount(self, change_amount):
        '''
        Method used to manage the equity changes as new transactions appears.
        The idea is to deal as follows:
            negative change_amount - transaction is opened and consumes equity
            positivit change_amount - transaction was closed and returns the
                                      equity
        '''
        self.equity = self.equity + change_amount


class Transaction:
    '''
    Class used to store transaction data and provide methods to manage all
    transactions
    '''

    def __init__(self, trans_numb, transaction_gl, comm=0.0039):
        '''
        Parameters:
        -----------
        comm - broker's commision. Default value for DM mBank
        trans_numb - externally provided transaction ID
        transation_gl - list to store transactions
        '''
        # pylint: disable=too-many-instance-attributes

        self.stocks_number = 0  # number of stocks bought
        self.open_price = 0  # price for opening the transaction
        self.open_date = ''  # stores the open date of transaction
        self.close_price = 0  # price for closing the transaction
        self.close_date = ''  # stores the close date
        self.comm_rate = comm  # broker's commision
        self.open_value = 0  # worth of transaction without commission
        self.close_value = 0
        self.comm_open_value = 0  # commision for opening the transaction
        self.comm_close_value = 0  # commision for closing the transaction
        self.open_total = 0  # total value of the stocks price + commision
        self.close_total = 0
        self.trans_result = 0
        self.stop_loss = 0  # if below this value, stocks are sold Stop Loss
        self.stop_loss_date = ''  # stores the stop loss date
        self.trans_id = trans_numb  # ID of the transaction
        # self.trans_number = self.trans_number + 1 # ID for next transaction
        self.in_transaction = False  # transaction indicator
        self.general_ledger = transaction_gl
        # added on 02.08.2020 (EU format)
        self.max_drawdown = 0
        self.max_drawdown_perc = 0
        self.max_gain = 0
        self.max_gain_perc = 0 
        self.current_value = 0
        self.risk = 0

    def how_many_stocks(self, price, budget):
        '''
        Function returns how many stocks you can buy
        '''
        number = int((budget - budget * self.comm_rate) / price)
        return number

    def open_transaction(self, number, price, date_open, be_verbose=False):
        '''
        Method to buy stocks.
        Parameters:
        -----------
        numb      - number of stocks bought in single transaction
        buy_price - stock's buy price
        date      - date and time of open
        be_verbose   - to print information or not
        '''
        if not self.in_transaction:
            self.stocks_number = number
            self.open_price = price
            self.open_value = self.stocks_number * self.open_price
            self.comm_open_value = self.open_value * self.comm_rate
            if self.comm_open_value < 3:
                self.comm_open_value = 3
            self.open_total = self.open_value + self.comm_open_value
            self.in_transaction = True
            self.open_date = date_open
            self.register_transaction(verbose=be_verbose)

    def set_sl(self, sl_type, sl_factor, date_sl, price=0, be_verbose=False):
        '''
        Functions sets the SL on the price.
        Parameters:
        -----------
        sl_type   - string, 3 possibilities
                      - atr - stop loss based on ATR calculations
                      - percent - stop loss based on the percentage slippage
                      - fixed - stop loss based on fixed value
        sl_factor - float, if sl_type = 'atr', than is the ATR value,
                    if sl_type = 'percent' it is just the value of the
                    percent, between 0 and 100, when sl_type = 'fixed' it is
                    the value of the stop loss
        price     - current price, default value set for sl_factor='fixed'
        date_SL   - date time of SL
        be_verbose   - to print comments about transaction or not
        '''
        if sl_type not in ['atr', 'percent', 'fixed']:
            print('Value {} of sl_type is not appropriate. Use "atr", "fixed" \
                  or "percent" only. Setting SL to 0'.format(sl_type))
            self.stop_loss = 0
        elif not isinstance(sl_factor, numbers.Number):
            print('number of type int or float is expected, not {}'.
                  format(type(sl_factor)))
        else:
            if sl_type == 'atr':
                new_sl = price - sl_factor
                if new_sl > self.stop_loss:
                    self.stop_loss = new_sl
                    self.stop_loss_date = date_sl
                    self.register_transaction(verbose=be_verbose)
            elif sl_type == 'fixed':
                if sl_factor > self.stop_loss:
                    self.stop_loss = sl_factor
                    self.stop_loss_date = date_sl
                    self.register_transaction(verbose=be_verbose)
            else:
                if sl_factor < 0 or sl_factor > 100:
                    print('sl_factor in percent mode must be 0 -100 value. \
                          Setting SL to 0 PLN.')
                    self.stop_loss = 0
                else:
                    new_sl = price - price * (sl_factor / 100)
                    if new_sl > self.stop_loss:
                        self.stop_loss = new_sl
                        self.stop_loss_date = date_sl
                        self.register_transaction(verbose=be_verbose)

    def close_transaction(self, price, date_close, be_verbose=False):
        '''
        Method to close the transaction
        '''
        if self.in_transaction:
            self.close_price = price
            self.close_value = self.close_price * self.stocks_number
            self.comm_close_value = self.close_value * self.comm_rate
            if self.comm_close_value < 3:
                self.comm_close_value = 3
            self.close_total = self.close_value - self.comm_close_value
            self.trans_result = self.close_total - self.open_total
            self.close_date = date_close
            self.register_transaction(verbose=be_verbose)

    def reset_values(self):
        '''
        Function resets all values after the transaction is closed
        '''
        self.stocks_number = 0
        self.open_price = 0
        self.open_date = ''
        self.close_price = 0
        self.close_date = ''
        self.open_value = 0
        self.close_value = 0
        self.comm_open_value = 0
        self.comm_close_value = 0
        self.open_total = 0
        self.close_total = 0
        self.trans_result = 0
        self.stop_loss = 0
        self.stop_loss_date = ''
        self.in_transaction = False
        self.trans_id = self.trans_id + 1
        # Added on 02.08.2020
        self.max_drawdown = 0
        self.max_drawdown_perc = 0
        self.max_gain = 0
        self.max_gain_perc = 0
        self.current_value = 0
        self.risk = 0

    def register_transaction(self, verbose):
        '''
        Function registers the transaction details in the general ledger.
        '''
        if verbose:
            print('''
                  Transakcja numer: {}, data otwarcia: {} ilosc akcji: {},
                  cena otwarcia {}, wartosc otwarcia: {:.2f},
                  prowizja otwarcia: {:.2f}, koszt otwarcia {:.2f}, 
                  data stopa: {}, SL: {:.2f}, data zamknięcia: {}, 
                  cena zamkn: {}, wartosc zamkn: {:.2f}, 
                  prowizja zamkn: {:.2f}, koszt_zamkn: {:.2f}, 
                  wynik_transkacji: {:.2f}, maks obs. kapitału PLN: {:.2f},
                  maks. obs. kapitalu %: {:.2f}, 
                  maks. zysk chwilowy PLN: {:.2f}, 
                  maks. zysk chwilowy %: {:.2f}
                  '''.format(self.trans_id, self.open_date, self.stocks_number,
                             self.open_price, self.open_value,
                             self.comm_open_value, self.open_total,
                             self.stop_loss_date, self.stop_loss,
                             self.close_date, self.close_price,
                             self.close_value, self.comm_close_value,
                             self.close_total, self.trans_result,
                             self.max_drawdown, self.max_drawdown_perc,
                             self.max_gain, self.max_gain_perc)
                  )
        row = [
            self.trans_id, self.open_date, self.stocks_number,
            self.open_price, self.open_value, self.comm_open_value,
            self.open_total, self.stop_loss_date, self.stop_loss,
            self.close_date, self.close_price, self.close_value,
            self.comm_close_value, self.close_total, self.trans_result,
            self.max_drawdown, self.max_drawdown_perc, self.max_gain,
            self.max_gain_perc]
        self.general_ledger.append(row)

        # Added on 02.08.2020 (EU date format)
    def curr_value(self, price, be_verbose=False):
        '''
        Method to calculate current value of opened trade
        '''
        if self.in_transaction:
            curr_val = price * self.stocks_number
            curr_comm = curr_val * self.comm_rate
            if curr_comm < 3:
                curr_comm = 3
            curr_val = curr_val - curr_comm
            diff = curr_val - self.open_total
            self.current_value = curr_val
            if diff < self.max_drawdown:
                self.max_drawdown = diff
                #diff = self.max_drawdown - self.open_total
                self.max_drawdown_perc = 100 * diff / self.open_total
            if diff > self.max_gain:
                self.max_gain = diff
                #diff = self.max_gain - self.open_total
                self.max_gain_perc = 100 * diff / self.open_total
            if be_verbose:
                print('Drowdawn: {:.2f} PLN {:.2f} %, \
                        Max gain: {:.2f} PLN {:.2f} %'.format(self.max_drawdown,
                                                      self.max_drawdown_perc,
                                                      self.max_gain,
                                                      self.max_gain_perc))

    def define_risk(self, verbose=False):
        '''
        Method to calculate initial risk of a trade.
        '''
        initial_stop = self.stocks_number * self.stop_loss
        comm = initial_stop * self.comm_rate
        if comm < 3:
            comm = 3
        initial_stop = initial_stop - comm
        self.risk = self.open_total - initial_stop
        risk_perc = -100 * self.risk / self.open_total
        if verbose:
            print('Initial risk: {:.2f} PLN, {:.2f}%'.format(self.risk,
                                                             risk_perc))



if __name__ == '__main__':
    print('This is a module, do not run it, import it!')

# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 10:11:54 2020

@author: Krzysztof Oporowski
krzysztof.oporowski@gmail.com
"""

import numbers
import pickle
from datetime import date
from pathlib import Path
import quandl
import pandas as pd


def create_directory(directory_name):
    '''
    Function to create directory for storing data

    Parameters
    ----------
    directory_name : string
        Directory name.

    Returns
    -------
    None.

    '''
    path_to_check = Path(directory_name)
    if path_to_check.exists():
        print('Directory {} already exists'.format(directory_name))
        return True
    else:
        print('Attempting to create path')
        try:
            path_to_check.mkdir()
            return True
        except FileExistsError:
            print('Strange, directory {} cannot be created'.format(
                directory_name))
            return False


def get_own_data(equity_name, quandl_api_token):
    '''
    Function read data of the signle quity using the Quandl. It requires the
    Quandl API to be provided, to make sure that more than 50 queries are
    allowed. Function returns the Pandas Panel data structure.
    Parameters:
    -----------
    equity_names:     String, used for polish stocks. On the Quandl
                      platform polish stocks are listed under the 'WSE/'
                      subfolder (Warsaw Stock Exchnage). Equity_names needs to
                      be the list of strings without the 'WSE/' (which is added
                      by the function).
    quandl_API_token: string, representing the Quandl API token. For more
                      details refer to the http://quandl.com
    Returns:
    --------
    Pandas DataFrame with one entitie's data
    '''
    todays_date = str(date.today())
    file_name = 'Data/' + equity_name + '-' + todays_date + '.pickle'
    try:
        with open(file_name, 'rb') as opened_file:
            data = pickle.load(opened_file)
        # print('data from file {} used'.format(opened_file))
    except FileNotFoundError:
        quandl.ApiConfig.api_key = quandl_api_token
        # for equity_name in equity_names:
        quandl_query = 'WSE/' + equity_name
        data = quandl.get(quandl_query)
        data.drop(['%Change', '# of Trades', 'Turnover (1000)'],
                  axis=1, inplace=True)
        data.columns = ['open', 'high', 'low', 'close', 'volume']
        data.index.names = ['date']
        # data = data[equity_name].resample('1d').mean()
        data.fillna(method='ffill', inplace=True)
        # print('Data for {} collected'.format(quandl_query))
        # save data to avoid downloading again today
        if create_directory('Data'):
            with open(file_name, 'wb') as opened_file:
                pickle.dump(data, opened_file)
            # print('Data from Quandl downloaded')
    return data


def get_data_from_bossa(stooq_name):
    '''
    Parameters
    ----------
    stooq_name : TYPE
        DESCRIPTION.

    Returns
    -------
    data : TYPE
        DESCRIPTION.

    '''
    file_name = 'Data/' + stooq_name + '.mst'
    data = pd.read_csv(file_name,
                       usecols=[1, 2, 3, 4, 5, 6],
                       parse_dates=[0],
                       index_col=[0],
                       header=0,
                       names=['date',
                              'open',
                              'high',
                              'low',
                              'close',
                              'volume']
                       )
    return data


def define_gl(gl):
    '''
    Function returns Pandas dataframe where all transactions are stored
    '''
    cols = ['id', 'open_date', 'stocks_number', 'open_price', 'open_value',
            'open_commission', 'open_total', 'SL_date', 'SL', 'close_date',
            'close_price', 'close_value', 'close_commission', 'close_total',
            'trans_result']
    transactions = pd.DataFrame(gl, columns=cols)
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
        self.SL = 0  # if below this value, stocks are sold Stop Loss
        self.stop_loss_date = ''  # stores the stop loss date
        self.trans_id = trans_numb  # ID of the transaction
        # self.trans_number = self.trans_number + 1 # ID for next transaction
        self.in_transaction = False  # transaction indicator
        self.gl = transaction_gl

    def how_many_stocks(self, price, budget):
        '''
        Function returns how many stocks you can buy
        '''
        number = int((budget - budget * self.comm_rate) / price)
        return number

    def open_transaction(self, number, price, date_open):
        '''
        Method to buy stocks.
        Parameters:
        -----------
        numb      - number of stocks bought in single transaction
        buy_price - stock's buy price
        date      - date and time of open
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
            self.register_transaction(verbose=False)

    def set_sl(self, sl_type, sl_factor, price, date_sl):
        '''
        Functions sets the SL on the price.
        Parameters:
        -----------
        sl_type   - string, 2 possibilities
                      - atr - stop loss based on ATR calculations
                      - percent - stop loss based on the percentage slippage
        sl_factor - float, if sl_type = 'atr', than is the ATR value,
                    if sl_type = 'percent' it is just the value of the
                    percent, between 0 and 100
        price     - current price
        date_SL      - date time of SL
        '''
        if sl_type not in ['atr', 'percent']:
            print('Value {} of sl_type is not appropriate. Use "atr" or \
                  "percent" only. Setting SL to 0'.format(sl_type))
            self.SL = 0
        elif not isinstance(sl_factor, numbers.Number):
            print('number of type int or float is expected, not {}'.
                  format(type(sl_factor)))
        else:
            if sl_type == 'atr':
                new_sl = price - sl_factor
                if new_sl > self.SL:
                    self.SL = new_sl
                    self.stop_loss_date = date_sl
                    self.register_transaction(verbose=False)
            else:
                if sl_factor < 0 or sl_factor > 100:
                    print('sl_factor in percent mode must be 0 -100 value. \
                          Setting SL to 0 PLN.')
                    self.SL = 0
                else:
                    new_sl = price - price * (sl_factor / 100)
                    if new_sl > self.SL:
                        self.SL = new_sl
                        self.stop_loss_date = date_sl
                        self.register_transaction(verbose=False)

    def close_transaction(self, price, date_close):
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
            self.register_transaction(verbose=False)

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
        self.SL = 0
        self.stop_loss_date = ''
        self.in_transaction = False
        self.trans_id = self.trans_id + 1

    def register_transaction(self, verbose=True):
        '''
        Function registers the transaction details in the general ledger.
        '''
        if verbose:
            print('''
                  Transakcja numer: {}, data otwarcia: {} ilosc akcji: {},
                  cena otwarcia {}, wartosc otwarcia: {},prowizja otwarcia: {},
                  koszt otwarcia {}, data stopa: {}, SL: {},
                  data zamknięcia: {}, cena zamkn: {}, wartosc zamkn: {},
                  prowizja zamkn: {}, koszt_zamkn: {}, wynik_transkacji: {}
                  '''.format(self.trans_id, self.open_date, self.stocks_number,
                             self.open_price, self.open_value,
                             self.comm_open_value, self.open_total,
                             self.stop_loss_date, self.SL,
                             self.close_date, self.close_price,
                             self.close_value, self.comm_close_value,
                             self.close_total, self.trans_result)
                  )
        row = [
            self.trans_id, self.open_date, self.stocks_number,
            self.open_price, self.open_value, self.comm_open_value,
            self.open_total, self.stop_loss_date, self.SL,
            self.close_date, self.close_price, self.close_value,
            self.comm_close_value, self.close_total, self.trans_result]
        self.gl.append(row)


def get_date_only(row):
    '''
    To process index date/time value from Quandl to get only date, as a string
    '''
    date_time = row.name
    date_time = pd.to_datetime(date_time)
    date_only = date_time.date()
    return date_only


if __name__ == '__main__':
    print('This is a module, do not run it, import it!')

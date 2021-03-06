import datetime
import pickle

import numpy as np
import pandas as pd

from tf_agents.environments import py_environment
from tf_agents.environments import tf_py_environment
from tf_agents.specs import array_spec
from tf_agents.trajectories import time_step as ts

TRAIN_CUT_PERCENT = 0.8
VAL_CUT_PERCENT = 0.1
TEST_CUT_PERCENT = 0.1

CFTC_NO_USE_COLUMNS = [
    'Market_and_Exchange_Names',
    'As_of_Date_In_Form_YYMMDD',
    'Report_Date_as_YYYY-MM-DD',
    'CFTC_Contract_Market_Code',
    'CFTC_Market_Code',
    'CFTC_Region_Code',
    'CFTC_Commodity_Code',

    'Open_Interest_All',

    'Dealer_Positions_Long_All',
    'Dealer_Positions_Short_All',
    'Dealer_Positions_Spread_All',

    'Asset_Mgr_Positions_Long_All',
    'Asset_Mgr_Positions_Short_All',
    'Asset_Mgr_Positions_Spread_All',

    'Lev_Money_Positions_Long_All',
    'Lev_Money_Positions_Short_All',
    'Lev_Money_Positions_Spread_All',

    'Other_Rept_Positions_Long_All',
    'Other_Rept_Positions_Short_All',
    'Other_Rept_Positions_Spread_All',

    'Tot_Rept_Positions_Long_All',
    'Tot_Rept_Positions_Short_All',

    'NonRept_Positions_Long_All',
    'NonRept_Positions_Short_All',

    'Change_in_Open_Interest_All',

    # 'Change_in_Dealer_Long_All',
    # 'Change_in_Dealer_Short_All',
    'Change_in_Dealer_Spread_All',

    # 'Change_in_Asset_Mgr_Long_All',
    # 'Change_in_Asset_Mgr_Short_All',
    'Change_in_Asset_Mgr_Spread_All',

    # 'Change_in_Lev_Money_Long_All',
    # 'Change_in_Lev_Money_Short_All',
    'Change_in_Lev_Money_Spread_All',

    # 'Change_in_Other_Rept_Long_All',
    # 'Change_in_Other_Rept_Short_All',
    'Change_in_Other_Rept_Spread_All',

    'Change_in_Tot_Rept_Long_All',
    'Change_in_Tot_Rept_Short_All',
    'Change_in_NonRept_Long_All',
    'Change_in_NonRept_Short_All',

    'Pct_of_Open_Interest_All',
    'Pct_of_OI_Dealer_Long_All',
    'Pct_of_OI_Dealer_Short_All',
    'Pct_of_OI_Dealer_Spread_All',
    'Pct_of_OI_Asset_Mgr_Long_All',
    'Pct_of_OI_Asset_Mgr_Short_All',
    'Pct_of_OI_Asset_Mgr_Spread_All',
    'Pct_of_OI_Lev_Money_Long_All',
    'Pct_of_OI_Lev_Money_Short_All',
    'Pct_of_OI_Lev_Money_Spread_All',
    'Pct_of_OI_Other_Rept_Long_All',
    'Pct_of_OI_Other_Rept_Short_All',
    'Pct_of_OI_Other_Rept_Spread_All',
    'Pct_of_OI_Tot_Rept_Long_All',
    'Pct_of_OI_Tot_Rept_Short_All',
    'Pct_of_OI_NonRept_Long_All',
    'Pct_of_OI_NonRept_Short_All',

    'Traders_Tot_All',
    'Traders_Dealer_Long_All',
    'Traders_Dealer_Short_All',
    'Traders_Dealer_Spread_All',
    'Traders_Asset_Mgr_Long_All',
    'Traders_Asset_Mgr_Short_All',
    'Traders_Asset_Mgr_Spread_All',
    'Traders_Lev_Money_Long_All',
    'Traders_Lev_Money_Short_All',
    'Traders_Lev_Money_Spread_All',
    'Traders_Other_Rept_Long_All',
    'Traders_Other_Rept_Short_All',
    'Traders_Other_Rept_Spread_All',
    'Traders_Tot_Rept_Long_All',
    'Traders_Tot_Rept_Short_All',
    'Conc_Gross_LE_4_TDR_Long_All',
    'Conc_Gross_LE_4_TDR_Short_All',
    'Conc_Gross_LE_8_TDR_Long_All',
    'Conc_Gross_LE_8_TDR_Short_All',
    'Conc_Net_LE_4_TDR_Long_All',
    'Conc_Net_LE_4_TDR_Short_All',
    'Conc_Net_LE_8_TDR_Long_All',
    'Conc_Net_LE_8_TDR_Short_All',
    'CFTC_Contract_Market_Code_Quotes',
    'CFTC_Market_Code_Quotes',
    'CFTC_Commodity_Code_Quotes',
    'CFTC_SubGroup_Code',
    'FutOnly_or_Combined',
    'Contract_Units'
]


class TradingEnv(py_environment.PyEnvironment):
    '''
    ???????????????
        1.????????????CFTC???????????????????????????
        2.???????????????????????????
    '''

    def __init__(self, symbol, ob_shape, hold_week, review_week):
        super().__init__()
        self.symbol = symbol
        self.ob_shape = ob_shape
        self.review_week = review_week
        self.hold_how_many_week = hold_week

        self._action_spec = array_spec.BoundedArraySpec(
            shape=(), dtype=np.int64, minimum=0, maximum=1, name='action'
        )
        self._observation_spec = array_spec.BoundedArraySpec(
            shape=(self.ob_shape,), dtype=np.float64, name='observation'
        )
        self.train_data , self.train_date, self.price_data= self.gen_state_data()
        self._state = self.train_data[0:self.review_week].reshape((self.ob_shape,))
        self._state_count = self.review_week - 1
        self._episode_ended = False
        self.mul, self.single_prpfit, self.spread = self.get_base_point(symbol)

    @staticmethod
    def get_base_point(symbol):
        if 'USD' in symbol:
            if 'JPY' in symbol:
                multiplier = 1000
                USDprofit = 0.0102
            else:
                multiplier = 100000
                USDprofit = 0.0103
        elif symbol in ['CADJPY']:
            multiplier = 1000
            USDprofit = 0.0102
        elif symbol in ['EURNZD', 'CADCHF', 'AUDNZD', 'AUDCAD', 'EURGBP', 'GBPCHF']:
            multiplier = 100000
            USDprofit = 0.0103
        elif symbol in ['BRENT_OIL', 'Brent']:
            multiplier = 100
            USDprofit = 0.1
        elif symbol in ['GOLD', 'USD_500', 'WHEAT']:
            multiplier = 100
            USDprofit = 0.01
        elif symbol in ['SUGAR#11']:
            multiplier = 100
            USDprofit = 1
        elif symbol in ['COCOA']:
            multiplier = 1
            USDprofit = 1
        elif symbol == 'SP500m':
            multiplier = 10
            USDprofit = 0.1
        elif symbol in ['SILVER']:
            multiplier = 1000
            USDprofit = 0.1
        elif symbol == 'COPPER':
            multiplier = 10000
            USDprofit = 0.01
        elif symbol == 'NASDAQ100':
            multiplier = 100
            USDprofit = 0.01
        elif symbol == 'SH':
            multiplier = 1000
            USDprofit = 1
        elif symbol == 'CHINA_A50':
            multiplier = 10
            USDprofit = 0.01
        else:
            multiplier = 1
            USDprofit = 1

        if symbol in ['EURUSD']:
            trade_point = 13
        elif symbol == 'USDJPY':
            trade_point = 15
        elif symbol == 'AUDUSD':
            trade_point = 18
        elif symbol == 'GBPUSD':
            trade_point = 20
        elif symbol == 'USDCAD':
            trade_point = 25
        elif symbol == 'USDCHF':
            trade_point = 20
        elif symbol == 'GOLD':
            trade_point = 35
        elif symbol == 'SILVER':
            trade_point = 35
        elif symbol == 'BRENT_OIL':
            trade_point = 6
        elif symbol == 'S&P500':
            trade_point = 50
        elif symbol == 'SP500m':
            trade_point = 5
        elif symbol == 'COPPER':
            trade_point = 60
        elif symbol == 'WHEAT':
            trade_point = 50
        elif symbol == 'CHINA_A50':
            trade_point = 125
        else:
            trade_point = 30
        return multiplier, USDprofit, trade_point

    def action_spec(self):
        return self._action_spec

    def observation_spec(self):
        return self._observation_spec

    def _reset(self):
        self._state_count = self.review_week - 1
        self._state = self.train_data[0:self.review_week].reshape((self.ob_shape,))
        self._state = np.array(self._state, dtype=np.float64)
        self._episode_ended = False
        return ts.restart(self._state)

    def _step(self, action):
        '''
        ?????? ??????state ?????? ??????done
        '''
        if self._episode_ended:
            # The last action ended the episode. Ignore the current action and start
            # a new episode.
            return self.reset()

        report_date = pd.to_datetime(str(self.train_date[self._state_count]))
        entry_date = report_date + datetime.timedelta(days=5)
        entry_date_str = entry_date.strftime(format='%Y.%m.%d')

        price_df = self.price_data[entry_date_str:]
        entry_price = price_df[0:1]['open'].values[0]
        close_price = price_df[self.hold_how_many_week-1:self.hold_how_many_week]['close'].values[0]
        high_price = price_df[self.hold_how_many_week-1:self.hold_how_many_week]['high'].values[0]
        low_price = price_df[self.hold_how_many_week-1:self.hold_how_many_week]['low'].values[0]
        # ?????????
        if action == 0:
            reward = (entry_price - (close_price))*self.mul
        # ?????????
        elif action == 1:
            reward = ((close_price) - entry_price) * self.mul
        # ?????????
        else:
            reward = 0

        new_state = np.array(
            self.train_data[self._state_count-(self.review_week-2):self._state_count+2].reshape((self.ob_shape,)),
            dtype=np.float64)
        self._state_count += 1
        if self._state_count >= len(self.train_data)-self.hold_how_many_week:
            self._episode_ended = True

        if self._episode_ended:
            return ts.termination(new_state, reward=reward)
        else:
            return ts.transition(
                new_state, reward=reward, discount=0
            )

    def gen_state_data(self):
        train_data = pd.read_csv(f'training_data/CFTC_{self.symbol}.csv')
        data_len = len(train_data)
        train_end = int(data_len * TRAIN_CUT_PERCENT)
        train_data = train_data[0:train_end].reset_index(drop=True)
        print(f'????????????????????????0:{train_end}')

        train_data = train_data.reset_index(drop=True)
        train_date = train_data['As_of_Date_In_Form_YYMMDD']

        # ??????????????????
        for i in CFTC_NO_USE_COLUMNS:
            del (train_data[i])

        # ???????????????
        train_data.fillna(0, inplace=True)
        train_mean = train_data.mean()
        train_std = train_data.std()

        # with open(f'CFTC_{self.symbol}_2week_mean.pickle', 'rb') as f:
        #     train_mean = pickle.load(f)
        # with open(f'CFTC_{self.symbol}_2week_std.pickle', 'rb') as f:
        #     train_std = pickle.load(f)

        with open(f'CFTC_{self.symbol}_2week_mean.pickle', 'wb') as f:
            pickle.dump(train_mean, f, True)
        with open(f'CFTC_{self.symbol}_2week_std.pickle', 'wb') as f:
            pickle.dump(train_std, f, True)

        train_data = (train_data - train_mean) / train_std

        # ????????????????????????
        # order = ['funds_hold_long', 'funds_hold_short', 'funds_hold_spread', 'coms_hold_long', 'coms_hold_short',
        #              'all_hold_long', 'all_hold_short', 'non_report_long', 'non_report_short', 'funds_change_long',
        #              'funds_change_short', 'funds_change_spread', 'coms_change_long', 'coms_change_short',
        #              'all_change_long', 'all_change_short', 'non_report_change_long', 'non_report_change_short']
        # train_data = train_data[order]

        train_data_array = train_data.values
        price_data = pd.read_csv(f'training_data/{self.symbol}10080.csv')
        price_data.set_index(['date_time'], inplace=True)
        return train_data_array, train_date, price_data


class TradingEnvVal(py_environment.PyEnvironment):

    def __init__(self, symbol, mode, ob_shape, hold_week, review_week, start_time=None, end_time=None):
        super().__init__()
        self.symbol = symbol
        self.start_time = start_time
        self.end_time = end_time
        self.ob_shape = ob_shape
        self.mode = mode
        self.hold_how_many_week = hold_week
        self.review_week = review_week
        self.mul, self.single_prpfit, self.spread = TradingEnv.get_base_point(symbol)
        self._action_spec = array_spec.BoundedArraySpec(
            shape=(), dtype=np.int64, minimum=0, maximum=1, name='action'
        )
        self._observation_spec = array_spec.BoundedArraySpec(
            shape=(self.ob_shape,), dtype=np.float64, name='observation'
        )
        self.train_data , self.train_date, self.price_data= self.gen_state_data()
        self._state = self.train_data[0:self.review_week].reshape((self.ob_shape,))
        self._state_count = self.review_week - 1
        self._episode_ended = False
        self.entry_date = None

    def action_spec(self):
        return self._action_spec

    def observation_spec(self):
        return self._observation_spec

    def _reset(self):
        self._state_count = self.review_week - 1
        self._state = self.train_data[0:self.review_week].reshape((self.ob_shape,))
        self._state = np.array(self._state, dtype=np.float64)
        self._episode_ended = False
        return ts.restart(self._state)

    def _step(self, action):
        '''
        ?????? ??????state ?????? ??????done
        '''
        if self._episode_ended:
            # The last action ended the episode. Ignore the current action and start
            # a new episode.
            return self.reset()

        report_date = pd.to_datetime(str(self.train_date[self._state_count]))
        entry_date = report_date + datetime.timedelta(days=5)
        entry_date_str = entry_date.strftime(format='%Y.%m.%d')
        self.entry_date = entry_date_str

        price_df = self.price_data[entry_date_str:]
        entry_price = price_df[0:1]['open'].values[0]
        close_price = price_df[self.hold_how_many_week-1:self.hold_how_many_week]['close'].values[0]
        high_price = price_df[self.hold_how_many_week-1:self.hold_how_many_week]['high'].values[0]
        low_price = price_df[self.hold_how_many_week-1:self.hold_how_many_week]['low'].values[0]
        # ?????????
        if action == 0:
            reward = (entry_price - (close_price))*self.mul
        # ?????????
        elif action == 1:
            reward = ((close_price) - entry_price) * self.mul
        # ?????????
        else:
            reward = 0

        new_state = np.array(
            self.train_data[self._state_count-(self.review_week-2):self._state_count+2].reshape((self.ob_shape,)),
            dtype=np.float64
        )
        self._state_count += 1
        if self._state_count >= len(self.train_data)-self.hold_how_many_week:
            self._episode_ended = True

        if self._episode_ended:
            return ts.termination(new_state, reward=reward)
        else:
            return ts.transition(
                new_state, reward=reward, discount=0
            )

    def gen_state_data(self):
        train_data = pd.read_csv(f'training_data/CFTC_{self.symbol}.csv')
        # ??????????????????
        if self.mode == 'dev':
            train_len = len(train_data)
            val_cut_start = int(train_len * TRAIN_CUT_PERCENT)
            val_cut_end = int(train_len * (TRAIN_CUT_PERCENT+VAL_CUT_PERCENT))
            train_data = train_data[val_cut_start:val_cut_end].reset_index(drop=True)
            print(f'????????????????????????{val_cut_start}:{val_cut_end}')
        # ??????????????????
        else:
            train_data = train_data.reset_index(drop=True)
            if self.start_time is None:
                start_index = 0
            else:
                for index, row in train_data.iterrows():
                    time_1 = datetime.datetime.strptime('20' + str(row['As_of_Date_In_Form_YYMMDD']), '%Y%m%d')
                    time_2 = datetime.datetime.strptime('20' + str(train_data[index+1:index+2]['As_of_Date_In_Form_YYMMDD'].values[0]), '%Y%m%d')
                    if time_1 <= self.start_time - datetime.timedelta(days=21) <= time_2:
                        start_index = index
                        break
                else:
                    start_index = 0

            if self.end_time is None:
                end_index = -1
            else:
                for index, row in train_data.iterrows():
                    time_1 = datetime.datetime.strptime('20' + str(row['As_of_Date_In_Form_YYMMDD']), '%Y%m%d')
                    time_2 = datetime.datetime.strptime('20' + str(train_data[index + 1:index + 2]['date_time'].values[0]), '%Y%m%d')
                    if time_1 <= self.end_time <= time_2:
                        end_index = index
                        break
                else:
                    end_index = -1
            if end_index == -1:
                train_data = train_data[start_index:]
            else:
                train_data = train_data[start_index:end_index]
            train_data = train_data.reset_index(drop=True)

        train_date = train_data['As_of_Date_In_Form_YYMMDD']

        # ??????????????????
        for i in CFTC_NO_USE_COLUMNS:
            del (train_data[i])

        # ???????????????
        train_data.fillna(0, inplace=True)
        train_mean = train_data.mean()
        train_std = train_data.std()

        with open(f'CFTC_{self.symbol}_2week_mean.pickle', 'rb') as f:
            train_mean = pickle.load(f)
        with open(f'CFTC_{self.symbol}_2week_std.pickle', 'rb') as f:
            train_std = pickle.load(f)

        # with open(f'CFTC_EURUSD_mean.pickle', 'wb') as f:
        #     pickle.dump(train_mean, f, True)
        # with open(f'CFTC_EURUSD_std.pickle', 'wb') as f:
        #     pickle.dump(train_std, f, True)

        train_data = (train_data - train_mean) / train_std

        # ????????????????????????
        # if self.version == '1.0':
        #     if self.symbol in ['EURUSD']:
        #         order = ['funs_long', 'funs_short', 'com_long', 'com_short']
        #     elif self.symbol in ['GBPUSD', 'GOLD']:
        #         order = ['funs_long', 'funs_short', 'com_long', 'com_short', 'funds_hold']
        #     else:
        #         order = ['funds_hold_long','funds_hold_short','funds_hold_spread','coms_hold_long','coms_hold_short','all_hold_long','all_hold_short','non_report_long','non_report_short','funds_change_long','funds_change_short','funds_change_spread','coms_change_long','coms_change_short','all_change_long','all_change_short','non_report_change_long','non_report_change_short']
        # else:
        #     order = ['funds_hold_long', 'funds_hold_short', 'funds_hold_spread', 'coms_hold_long', 'coms_hold_short',
        #              'all_hold_long', 'all_hold_short', 'non_report_long', 'non_report_short', 'funds_change_long',
        #              'funds_change_short', 'funds_change_spread', 'coms_change_long', 'coms_change_short',
        #              'all_change_long', 'all_change_short', 'non_report_change_long', 'non_report_change_short']

        # train_data = train_data[order]

        train_data_array = train_data.values
        price_data = pd.read_csv(f'training_data/{self.symbol}10080.csv')
        price_data.set_index(['date_time'], inplace=True)
        return train_data_array, train_date, price_data


class TradingEnvTest(py_environment.PyEnvironment):

    def __init__(self, symbol, mode, ob_shape, hold_week, review_week, start_time=None, end_time=None):
        super().__init__()
        self.symbol = symbol
        self.start_time = start_time
        self.end_time = end_time
        self.ob_shape = ob_shape
        self.mode = mode
        self.hold_how_many_week = hold_week
        self.review_week = review_week
        self.mul, self.single_prpfit, self.spread = TradingEnv.get_base_point(symbol)
        self._action_spec = array_spec.BoundedArraySpec(
            shape=(), dtype=np.int64, minimum=0, maximum=1, name='action'
        )
        self._observation_spec = array_spec.BoundedArraySpec(
            shape=(self.ob_shape,), dtype=np.float64, name='observation'
        )
        self.train_data , self.train_date, self.price_data= self.gen_state_data()
        self._state = self.train_data[0:self.review_week].reshape((self.ob_shape,))
        self._state_count = self.review_week - 1
        self._episode_ended = False
        self.entry_date = None

    def action_spec(self):
        return self._action_spec

    def observation_spec(self):
        return self._observation_spec

    def _reset(self):
        self._state_count = self.review_week - 1
        self._state = self.train_data[0:self.review_week].reshape((self.ob_shape,))
        self._state = np.array(self._state, dtype=np.float64)
        self._episode_ended = False
        return ts.restart(self._state)

    def _step(self, action):
        '''
        ?????? ??????state ?????? ??????done
        '''
        if self._episode_ended:
            # The last action ended the episode. Ignore the current action and start
            # a new episode.
            return self.reset()

        report_date = pd.to_datetime(str(self.train_date[self._state_count]))
        entry_date = report_date + datetime.timedelta(days=5)
        entry_date_str = entry_date.strftime(format='%Y.%m.%d')
        self.entry_date = entry_date_str

        price_df = self.price_data[entry_date_str:]
        entry_price = price_df[0:1]['open'].values[0]
        close_price = price_df[self.hold_how_many_week-1:self.hold_how_many_week]['close'].values[0]
        high_price = price_df[self.hold_how_many_week-1:self.hold_how_many_week]['high'].values[0]
        low_price = price_df[self.hold_how_many_week-1:self.hold_how_many_week]['low'].values[0]
        # ?????????
        if action == 0:
            reward = (entry_price - (close_price))*self.mul
        # ?????????
        elif action == 1:
            reward = ((close_price) - entry_price) * self.mul
        # ?????????
        else:
            reward = 0

        new_state = np.array(
            self.train_data[self._state_count-(self.review_week-2):self._state_count+2].reshape((self.ob_shape,)),
            dtype=np.float64
        )
        self._state_count += 1
        if self._state_count >= len(self.train_data)-self.hold_how_many_week:
            self._episode_ended = True

        if self._episode_ended:
            return ts.termination(new_state, reward=reward)
        else:
            return ts.transition(
                new_state, reward=reward, discount=0.1
            )

    def gen_state_data(self):
        train_data = pd.read_csv(f'training_data/CFTC_{self.symbol}csv')
        # ??????????????????
        if self.mode == 'dev':
            train_len = len(train_data)
            test_cut_start = int(train_len * (TRAIN_CUT_PERCENT+VAL_CUT_PERCENT))
            train_data = train_data[test_cut_start:].reset_index(drop=True)
            print(f'????????????????????????{test_cut_start}:')
        # ??????????????????
        else:
            train_data = train_data.reset_index(drop=True)
            if self.start_time is None:
                start_index = 0
            else:
                for index, row in train_data.iterrows():
                    time_1 = datetime.datetime.strptime('20' + str(row['As_of_Date_In_Form_YYMMDD']), '%Y%m%d')
                    time_2 = datetime.datetime.strptime('20' + str(train_data[index+1:index+2]['As_of_Date_In_Form_YYMMDD'].values[0]), '%Y%m%d')
                    if time_1 <= self.start_time - datetime.timedelta(days=21) <= time_2:
                        start_index = index
                        break
                else:
                    start_index = 0

            if self.end_time is None:
                end_index = -1
            else:
                for index, row in train_data.iterrows():
                    time_1 = datetime.datetime.strptime('20' + str(row['As_of_Date_In_Form_YYMMDD']), '%Y%m%d')
                    time_2 = datetime.datetime.strptime('20' + str(train_data[index + 1:index + 2]['date_time'].values[0]), '%Y%m%d')
                    if time_1 <= self.end_time <= time_2:
                        end_index = index
                        break
                else:
                    end_index = -1
            if end_index == -1:
                train_data = train_data[start_index:]
            else:
                train_data = train_data[start_index:end_index]
            train_data = train_data.reset_index(drop=True)

        train_date = train_data['As_of_Date_In_Form_YYMMDD']

        # ??????????????????
        for i in CFTC_NO_USE_COLUMNS:
            del (train_data[i])

        # ???????????????
        train_data.fillna(0, inplace=True)
        train_mean = train_data.mean()
        train_std = train_data.std()

        with open(f'CFTC_{self.symbol}_2week_mean.pickle', 'rb') as f:
            train_mean = pickle.load(f)
        with open(f'CFTC_{self.symbol}_2week_std.pickle', 'rb') as f:
            train_std = pickle.load(f)

        # with open(f'CFTC_EURUSD_mean.pickle', 'wb') as f:
        #     pickle.dump(train_mean, f, True)
        # with open(f'CFTC_EURUSD_std.pickle', 'wb') as f:
        #     pickle.dump(train_std, f, True)

        train_data = (train_data - train_mean) / train_std

        # ????????????????????????
        # if self.version == '1.0':
        #     if self.symbol in ['EURUSD']:
        #         order = ['funs_long', 'funs_short', 'com_long', 'com_short']
        #     elif self.symbol in ['GBPUSD', 'GOLD']:
        #         order = ['funs_long', 'funs_short', 'com_long', 'com_short', 'funds_hold']
        #     else:
        #         order = ['funds_hold_long','funds_hold_short','funds_hold_spread','coms_hold_long','coms_hold_short','all_hold_long','all_hold_short','non_report_long','non_report_short','funds_change_long','funds_change_short','funds_change_spread','coms_change_long','coms_change_short','all_change_long','all_change_short','non_report_change_long','non_report_change_short']
        # else:
        #     order = ['funds_hold_long', 'funds_hold_short', 'funds_hold_spread', 'coms_hold_long', 'coms_hold_short',
        #              'all_hold_long', 'all_hold_short', 'non_report_long', 'non_report_short', 'funds_change_long',
        #              'funds_change_short', 'funds_change_spread', 'coms_change_long', 'coms_change_short',
        #              'all_change_long', 'all_change_short', 'non_report_change_long', 'non_report_change_short']

        # train_data = train_data[order]

        train_data_array = train_data.values
        price_data = pd.read_csv(f'training_data/{self.symbol}10080.csv')
        price_data.set_index(['date_time'], inplace=True)
        return train_data_array, train_date, price_data


class TradingEnvProduct(py_environment.PyEnvironment):

    def __init__(self, symbol):
        super().__init__()
        self.symbol = symbol
        self.ob_shape = 54
        self._action_spec = array_spec.BoundedArraySpec(
            shape=(), dtype=np.int64, minimum=0, maximum=1, name='action'
        )
        self._observation_spec = array_spec.BoundedArraySpec(
            shape=(self.ob_shape,), dtype=np.float64, name='observation'
        )
        self.train_data = self.gen_state_data()
        self._state = self.train_data[0:3].reshape((self.ob_shape,))
        self._episode_ended = False


    def action_spec(self):
        return self._action_spec

    def observation_spec(self):
        return self._observation_spec

    def _reset(self):
        self._state = self.train_data[0:3].reshape((self.ob_shape,))
        self._state = np.array(self._state, dtype=np.float64)
        self._episode_ended = False
        return ts.restart(self._state)

    def _step(self, action):
        '''
        ?????? ??????state ?????? ??????done
        '''
        if self._episode_ended:
            # The last action ended the episode. Ignore the current action and start
            # a new episode.
            return self.reset()

        reward = 0
        new_state = self._state
        self._state_count += 1
        self._episode_ended = True

        if self._episode_ended:
            return ts.termination(new_state, reward=reward)
        else:
            return ts.transition(
                new_state, reward=reward, discount=1
            )

    def gen_state_data(self):
        train_data = pd.read_csv(f'CFTC_{self.symbol}_product.csv')
        del(train_data['date_time'])

        # ???????????????
        with open(f'CFTC_{self.symbol}_2week_mean.pickle', 'rb') as f:
            train_mean = pickle.load(f)
        with open(f'CFTC_{self.symbol}_2week_std.pickle', 'rb') as f:
            train_std = pickle.load(f)
        train_data = (train_data - train_mean) / train_std

        train_data_array = train_data.values

        return train_data_array


#!/usr/bin/env python
# -*- coding: utf-8 -*-
CThostFtdcDisseminationField = {
    "SequenceSeries": "int",
    "SequenceNo": "int",
}

CThostFtdcReqUserLoginField = {
    "TradingDay": "string",
    "BrokerID": "string",
    "UserID": "string",
    "Password": "string",
    "UserProductInfo": "string",
    "InterfaceProductInfo": "string",
    "ProtocolInfo": "string",
    "MacAddress": "string",
    "OneTimePassword": "string",
    "reserve1": "string",
    "LoginRemark": "string",
    "ClientIPPort": "int",
    "ClientIPAddress": "string",
}

CThostFtdcRspUserLoginField = {
    "TradingDay": "string",
    "LoginTime": "string",
    "BrokerID": "string",
    "UserID": "string",
    "SystemName": "string",
    "FrontID": "int",
    "SessionID": "int",
    "MaxOrderRef": "string",
    "SHFETime": "string",
    "DCETime": "string",
    "CZCETime": "string",
    "FFEXTime": "string",
    "INETime": "string",
}

CThostFtdcUserLogoutField = {
    "BrokerID": "string",
    "UserID": "string",
}

CThostFtdcForceUserLogoutField = {
    "BrokerID": "string",
    "UserID": "string",
}

CThostFtdcReqAuthenticateField = {
    "BrokerID": "string",
    "UserID": "string",
    "UserProductInfo": "string",
    "AuthCode": "string",
    "AppID": "string",
}

CThostFtdcRspAuthenticateField = {
    "BrokerID": "string",
    "UserID": "string",
    "UserProductInfo": "string",
    "AppID": "string",
    "AppType": "char",
}

CThostFtdcAuthenticationInfoField = {
    "BrokerID": "string",
    "UserID": "string",
    "UserProductInfo": "string",
    "AuthInfo": "string",
    "IsResult": "int",
    "AppID": "string",
    "AppType": "char",
    "reserve1": "string",
    "ClientIPAddress": "string",
}

CThostFtdcRspUserLogin2Field = {
    "TradingDay": "string",
    "LoginTime": "string",
    "BrokerID": "string",
    "UserID": "string",
    "SystemName": "string",
    "FrontID": "int",
    "SessionID": "int",
    "MaxOrderRef": "string",
    "SHFETime": "string",
    "DCETime": "string",
    "CZCETime": "string",
    "FFEXTime": "string",
    "INETime": "string",
    "RandomString": "string",
}

CThostFtdcTransferHeaderField = {
    "Version": "string",
    "TradeCode": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "TradeSerial": "string",
    "FutureID": "string",
    "BankID": "string",
    "BankBrchID": "string",
    "OperNo": "string",
    "DeviceID": "string",
    "RecordNum": "string",
    "SessionID": "int",
    "RequestID": "int",
}

CThostFtdcTransferBankToFutureReqField = {
    "FutureAccount": "string",
    "FuturePwdFlag": "char",
    "FutureAccPwd": "string",
    "TradeAmt": "double",
    "CustFee": "double",
    "CurrencyCode": "string",
}

CThostFtdcTransferBankToFutureRspField = {
    "RetCode": "string",
    "RetInfo": "string",
    "FutureAccount": "string",
    "TradeAmt": "double",
    "CustFee": "double",
    "CurrencyCode": "string",
}

CThostFtdcTransferFutureToBankReqField = {
    "FutureAccount": "string",
    "FuturePwdFlag": "char",
    "FutureAccPwd": "string",
    "TradeAmt": "double",
    "CustFee": "double",
    "CurrencyCode": "string",
}

CThostFtdcTransferFutureToBankRspField = {
    "RetCode": "string",
    "RetInfo": "string",
    "FutureAccount": "string",
    "TradeAmt": "double",
    "CustFee": "double",
    "CurrencyCode": "string",
}

CThostFtdcTransferQryBankReqField = {
    "FutureAccount": "string",
    "FuturePwdFlag": "char",
    "FutureAccPwd": "string",
    "CurrencyCode": "string",
}

CThostFtdcTransferQryBankRspField = {
    "RetCode": "string",
    "RetInfo": "string",
    "FutureAccount": "string",
    "TradeAmt": "double",
    "UseAmt": "double",
    "FetchAmt": "double",
    "CurrencyCode": "string",
}

CThostFtdcTransferQryDetailReqField = {
    "FutureAccount": "string",
}

CThostFtdcTransferQryDetailRspField = {
    "TradeDate": "string",
    "TradeTime": "string",
    "TradeCode": "string",
    "FutureSerial": "int",
    "FutureID": "string",
    "FutureAccount": "string",
    "BankSerial": "int",
    "BankID": "string",
    "BankBrchID": "string",
    "BankAccount": "string",
    "CertCode": "string",
    "CurrencyCode": "string",
    "TxAmount": "double",
    "Flag": "char",
}

CThostFtdcRspInfoField = {
    "ErrorID": "int",
    "ErrorMsg": "string",
}

CThostFtdcExchangeField = {
    "ExchangeID": "string",
    "ExchangeName": "string",
    "ExchangeProperty": "char",
}

CThostFtdcProductField = {
    "reserve1": "string",
    "ProductName": "string",
    "ExchangeID": "string",
    "ProductClass": "char",
    "VolumeMultiple": "int",
    "PriceTick": "double",
    "MaxMarketOrderVolume": "int",
    "MinMarketOrderVolume": "int",
    "MaxLimitOrderVolume": "int",
    "MinLimitOrderVolume": "int",
    "PositionType": "char",
    "PositionDateType": "char",
    "CloseDealType": "char",
    "TradeCurrencyID": "string",
    "MortgageFundUseRange": "char",
    "reserve2": "string",
    "UnderlyingMultiple": "double",
    "ProductID": "string",
    "ExchangeProductID": "string",
}

CThostFtdcInstrumentField = {
    "reserve1": "string",
    "ExchangeID": "string",
    "InstrumentName": "string",
    "reserve2": "string",
    "reserve3": "string",
    "ProductClass": "char",
    "DeliveryYear": "int",
    "DeliveryMonth": "int",
    "MaxMarketOrderVolume": "int",
    "MinMarketOrderVolume": "int",
    "MaxLimitOrderVolume": "int",
    "MinLimitOrderVolume": "int",
    "VolumeMultiple": "int",
    "PriceTick": "double",
    "CreateDate": "string",
    "OpenDate": "string",
    "ExpireDate": "string",
    "StartDelivDate": "string",
    "EndDelivDate": "string",
    "InstLifePhase": "char",
    "IsTrading": "int",
    "PositionType": "char",
    "PositionDateType": "char",
    "LongMarginRatio": "double",
    "ShortMarginRatio": "double",
    "MaxMarginSideAlgorithm": "char",
    "reserve4": "string",
    "StrikePrice": "double",
    "OptionsType": "char",
    "UnderlyingMultiple": "double",
    "CombinationType": "char",
    "InstrumentID": "string",
    "ExchangeInstID": "string",
    "ProductID": "string",
    "UnderlyingInstrID": "string",
}

CThostFtdcBrokerField = {
    "BrokerID": "string",
    "BrokerAbbr": "string",
    "BrokerName": "string",
    "IsActive": "int",
}

CThostFtdcTraderField = {
    "ExchangeID": "string",
    "TraderID": "string",
    "ParticipantID": "string",
    "Password": "string",
    "InstallCount": "int",
    "BrokerID": "string",
}

CThostFtdcInvestorField = {
    "InvestorID": "string",
    "BrokerID": "string",
    "InvestorGroupID": "string",
    "InvestorName": "string",
    "IdentifiedCardType": "char",
    "IdentifiedCardNo": "string",
    "IsActive": "int",
    "Telephone": "string",
    "Address": "string",
    "OpenDate": "string",
    "Mobile": "string",
    "CommModelID": "string",
    "MarginModelID": "string",
}

CThostFtdcTradingCodeField = {
    "InvestorID": "string",
    "BrokerID": "string",
    "ExchangeID": "string",
    "ClientID": "string",
    "IsActive": "int",
    "ClientIDType": "char",
    "BranchID": "string",
    "BizType": "char",
    "InvestUnitID": "string",
}

CThostFtdcPartBrokerField = {
    "BrokerID": "string",
    "ExchangeID": "string",
    "ParticipantID": "string",
    "IsActive": "int",
}

CThostFtdcSuperUserField = {
    "UserID": "string",
    "UserName": "string",
    "Password": "string",
    "IsActive": "int",
}

CThostFtdcSuperUserFunctionField = {
    "UserID": "string",
    "FunctionCode": "char",
}

CThostFtdcInvestorGroupField = {
    "BrokerID": "string",
    "InvestorGroupID": "string",
    "InvestorGroupName": "string",
}

CThostFtdcTradingAccountField = {
    "BrokerID": "string",
    "AccountID": "string",
    "PreMortgage": "double",
    "PreCredit": "double",
    "PreDeposit": "double",
    "PreBalance": "double",
    "PreMargin": "double",
    "InterestBase": "double",
    "Interest": "double",
    "Deposit": "double",
    "Withdraw": "double",
    "FrozenMargin": "double",
    "FrozenCash": "double",
    "FrozenCommission": "double",
    "CurrMargin": "double",
    "CashIn": "double",
    "Commission": "double",
    "CloseProfit": "double",
    "PositionProfit": "double",
    "Balance": "double",
    "Available": "double",
    "WithdrawQuota": "double",
    "Reserve": "double",
    "TradingDay": "string",
    "SettlementID": "int",
    "Credit": "double",
    "Mortgage": "double",
    "ExchangeMargin": "double",
    "DeliveryMargin": "double",
    "ExchangeDeliveryMargin": "double",
    "ReserveBalance": "double",
    "CurrencyID": "string",
    "PreFundMortgageIn": "double",
    "PreFundMortgageOut": "double",
    "FundMortgageIn": "double",
    "FundMortgageOut": "double",
    "FundMortgageAvailable": "double",
    "MortgageableFund": "double",
    "SpecProductMargin": "double",
    "SpecProductFrozenMargin": "double",
    "SpecProductCommission": "double",
    "SpecProductFrozenCommission": "double",
    "SpecProductPositionProfit": "double",
    "SpecProductCloseProfit": "double",
    "SpecProductPositionProfitByAlg": "double",
    "SpecProductExchangeMargin": "double",
    "BizType": "char",
    "FrozenSwap": "double",
    "RemainSwap": "double",
}

CThostFtdcInvestorPositionField = {
    "reserve1": "string",
    "BrokerID": "string",
    "InvestorID": "string",
    "PosiDirection": "char",
    "HedgeFlag": "char",
    "PositionDate": "char",
    "YdPosition": "int",
    "Position": "int",
    "LongFrozen": "int",
    "ShortFrozen": "int",
    "LongFrozenAmount": "double",
    "ShortFrozenAmount": "double",
    "OpenVolume": "int",
    "CloseVolume": "int",
    "OpenAmount": "double",
    "CloseAmount": "double",
    "PositionCost": "double",
    "PreMargin": "double",
    "UseMargin": "double",
    "FrozenMargin": "double",
    "FrozenCash": "double",
    "FrozenCommission": "double",
    "CashIn": "double",
    "Commission": "double",
    "CloseProfit": "double",
    "PositionProfit": "double",
    "PreSettlementPrice": "double",
    "SettlementPrice": "double",
    "TradingDay": "string",
    "SettlementID": "int",
    "OpenCost": "double",
    "ExchangeMargin": "double",
    "CombPosition": "int",
    "CombLongFrozen": "int",
    "CombShortFrozen": "int",
    "CloseProfitByDate": "double",
    "CloseProfitByTrade": "double",
    "TodayPosition": "int",
    "MarginRateByMoney": "double",
    "MarginRateByVolume": "double",
    "StrikeFrozen": "int",
    "StrikeFrozenAmount": "double",
    "AbandonFrozen": "int",
    "ExchangeID": "string",
    "YdStrikeFrozen": "int",
    "InvestUnitID": "string",
    "PositionCostOffset": "double",
    "TasPosition": "int",
    "TasPositionCost": "double",
    "InstrumentID": "string",
}

CThostFtdcInstrumentMarginRateField = {
    "reserve1": "string",
    "InvestorRange": "char",
    "BrokerID": "string",
    "InvestorID": "string",
    "HedgeFlag": "char",
    "LongMarginRatioByMoney": "double",
    "LongMarginRatioByVolume": "double",
    "ShortMarginRatioByMoney": "double",
    "ShortMarginRatioByVolume": "double",
    "IsRelative": "int",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcInstrumentCommissionRateField = {
    "reserve1": "string",
    "InvestorRange": "char",
    "BrokerID": "string",
    "InvestorID": "string",
    "OpenRatioByMoney": "double",
    "OpenRatioByVolume": "double",
    "CloseRatioByMoney": "double",
    "CloseRatioByVolume": "double",
    "CloseTodayRatioByMoney": "double",
    "CloseTodayRatioByVolume": "double",
    "ExchangeID": "string",
    "BizType": "char",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcDepthMarketDataField = {
    "TradingDay": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "reserve2": "string",
    "LastPrice": "double",
    "PreSettlementPrice": "double",
    "PreClosePrice": "double",
    "PreOpenInterest": "double",
    "OpenPrice": "double",
    "HighestPrice": "double",
    "LowestPrice": "double",
    "Volume": "int",
    "Turnover": "double",
    "OpenInterest": "double",
    "ClosePrice": "double",
    "SettlementPrice": "double",
    "UpperLimitPrice": "double",
    "LowerLimitPrice": "double",
    "PreDelta": "double",
    "CurrDelta": "double",
    "UpdateTime": "string",
    "UpdateMillisec": "int",
    "BidPrice1": "double",
    "BidVolume1": "int",
    "AskPrice1": "double",
    "AskVolume1": "int",
    "BidPrice2": "double",
    "BidVolume2": "int",
    "AskPrice2": "double",
    "AskVolume2": "int",
    "BidPrice3": "double",
    "BidVolume3": "int",
    "AskPrice3": "double",
    "AskVolume3": "int",
    "BidPrice4": "double",
    "BidVolume4": "int",
    "AskPrice4": "double",
    "AskVolume4": "int",
    "BidPrice5": "double",
    "BidVolume5": "int",
    "AskPrice5": "double",
    "AskVolume5": "int",
    "AveragePrice": "double",
    "ActionDay": "string",
    "InstrumentID": "string",
    "ExchangeInstID": "string",
}

CThostFtdcInstrumentTradingRightField = {
    "reserve1": "string",
    "InvestorRange": "char",
    "BrokerID": "string",
    "InvestorID": "string",
    "TradingRight": "char",
    "InstrumentID": "string",
}

CThostFtdcBrokerUserField = {
    "BrokerID": "string",
    "UserID": "string",
    "UserName": "string",
    "UserType": "char",
    "IsActive": "int",
    "IsUsingOTP": "int",
    "IsAuthForce": "int",
}

CThostFtdcBrokerUserPasswordField = {
    "BrokerID": "string",
    "UserID": "string",
    "Password": "string",
    "LastUpdateTime": "string",
    "LastLoginTime": "string",
    "ExpireDate": "string",
    "WeakExpireDate": "string",
}

CThostFtdcBrokerUserFunctionField = {
    "BrokerID": "string",
    "UserID": "string",
    "BrokerFunctionCode": "char",
}

CThostFtdcTraderOfferField = {
    "ExchangeID": "string",
    "TraderID": "string",
    "ParticipantID": "string",
    "Password": "string",
    "InstallID": "int",
    "OrderLocalID": "string",
    "TraderConnectStatus": "char",
    "ConnectRequestDate": "string",
    "ConnectRequestTime": "string",
    "LastReportDate": "string",
    "LastReportTime": "string",
    "ConnectDate": "string",
    "ConnectTime": "string",
    "StartDate": "string",
    "StartTime": "string",
    "TradingDay": "string",
    "BrokerID": "string",
    "MaxTradeID": "string",
    "MaxOrderMessageReference": "string",
}

CThostFtdcSettlementInfoField = {
    "TradingDay": "string",
    "SettlementID": "int",
    "BrokerID": "string",
    "InvestorID": "string",
    "SequenceNo": "int",
    "Content": "string",
    "AccountID": "string",
    "CurrencyID": "string",
}

CThostFtdcInstrumentMarginRateAdjustField = {
    "reserve1": "string",
    "InvestorRange": "char",
    "BrokerID": "string",
    "InvestorID": "string",
    "HedgeFlag": "char",
    "LongMarginRatioByMoney": "double",
    "LongMarginRatioByVolume": "double",
    "ShortMarginRatioByMoney": "double",
    "ShortMarginRatioByVolume": "double",
    "IsRelative": "int",
    "InstrumentID": "string",
}

CThostFtdcExchangeMarginRateField = {
    "BrokerID": "string",
    "reserve1": "string",
    "HedgeFlag": "char",
    "LongMarginRatioByMoney": "double",
    "LongMarginRatioByVolume": "double",
    "ShortMarginRatioByMoney": "double",
    "ShortMarginRatioByVolume": "double",
    "ExchangeID": "string",
    "InstrumentID": "string",
}

CThostFtdcExchangeMarginRateAdjustField = {
    "BrokerID": "string",
    "reserve1": "string",
    "HedgeFlag": "char",
    "LongMarginRatioByMoney": "double",
    "LongMarginRatioByVolume": "double",
    "ShortMarginRatioByMoney": "double",
    "ShortMarginRatioByVolume": "double",
    "ExchLongMarginRatioByMoney": "double",
    "ExchLongMarginRatioByVolume": "double",
    "ExchShortMarginRatioByMoney": "double",
    "ExchShortMarginRatioByVolume": "double",
    "NoLongMarginRatioByMoney": "double",
    "NoLongMarginRatioByVolume": "double",
    "NoShortMarginRatioByMoney": "double",
    "NoShortMarginRatioByVolume": "double",
    "InstrumentID": "string",
}

CThostFtdcExchangeRateField = {
    "BrokerID": "string",
    "FromCurrencyID": "string",
    "FromCurrencyUnit": "double",
    "ToCurrencyID": "string",
    "ExchangeRate": "double",
}

CThostFtdcSettlementRefField = {
    "TradingDay": "string",
    "SettlementID": "int",
}

CThostFtdcCurrentTimeField = {
    "CurrDate": "string",
    "CurrTime": "string",
    "CurrMillisec": "int",
    "ActionDay": "string",
}

CThostFtdcCommPhaseField = {
    "TradingDay": "string",
    "CommPhaseNo": "int",
    "SystemID": "string",
}

CThostFtdcLoginInfoField = {
    "FrontID": "int",
    "SessionID": "int",
    "BrokerID": "string",
    "UserID": "string",
    "LoginDate": "string",
    "LoginTime": "string",
    "reserve1": "string",
    "UserProductInfo": "string",
    "InterfaceProductInfo": "string",
    "ProtocolInfo": "string",
    "SystemName": "string",
    "PasswordDeprecated": "string",
    "MaxOrderRef": "string",
    "SHFETime": "string",
    "DCETime": "string",
    "CZCETime": "string",
    "FFEXTime": "string",
    "MacAddress": "string",
    "OneTimePassword": "string",
    "INETime": "string",
    "IsQryControl": "int",
    "LoginRemark": "string",
    "Password": "string",
    "IPAddress": "string",
}

CThostFtdcLogoutAllField = {
    "FrontID": "int",
    "SessionID": "int",
    "SystemName": "string",
}

CThostFtdcFrontStatusField = {
    "FrontID": "int",
    "LastReportDate": "string",
    "LastReportTime": "string",
    "IsActive": "int",
}

CThostFtdcUserPasswordUpdateField = {
    "BrokerID": "string",
    "UserID": "string",
    "OldPassword": "string",
    "NewPassword": "string",
}

CThostFtdcInputOrderField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "OrderRef": "string",
    "UserID": "string",
    "OrderPriceType": "char",
    "Direction": "char",
    "CombOffsetFlag": "string",
    "CombHedgeFlag": "string",
    "LimitPrice": "double",
    "VolumeTotalOriginal": "int",
    "TimeCondition": "char",
    "GTDDate": "string",
    "VolumeCondition": "char",
    "MinVolume": "int",
    "ContingentCondition": "char",
    "StopPrice": "double",
    "ForceCloseReason": "char",
    "IsAutoSuspend": "int",
    "BusinessUnit": "string",
    "RequestID": "int",
    "UserForceClose": "int",
    "IsSwapOrder": "int",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "AccountID": "string",
    "CurrencyID": "string",
    "ClientID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcOrderField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "OrderRef": "string",
    "UserID": "string",
    "OrderPriceType": "char",
    "Direction": "char",
    "CombOffsetFlag": "string",
    "CombHedgeFlag": "string",
    "LimitPrice": "double",
    "VolumeTotalOriginal": "int",
    "TimeCondition": "char",
    "GTDDate": "string",
    "VolumeCondition": "char",
    "MinVolume": "int",
    "ContingentCondition": "char",
    "StopPrice": "double",
    "ForceCloseReason": "char",
    "IsAutoSuspend": "int",
    "BusinessUnit": "string",
    "RequestID": "int",
    "OrderLocalID": "string",
    "ExchangeID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "reserve2": "string",
    "TraderID": "string",
    "InstallID": "int",
    "OrderSubmitStatus": "char",
    "NotifySequence": "int",
    "TradingDay": "string",
    "SettlementID": "int",
    "OrderSysID": "string",
    "OrderSource": "char",
    "OrderStatus": "char",
    "OrderType": "char",
    "VolumeTraded": "int",
    "VolumeTotal": "int",
    "InsertDate": "string",
    "InsertTime": "string",
    "ActiveTime": "string",
    "SuspendTime": "string",
    "UpdateTime": "string",
    "CancelTime": "string",
    "ActiveTraderID": "string",
    "ClearingPartID": "string",
    "SequenceNo": "int",
    "FrontID": "int",
    "SessionID": "int",
    "UserProductInfo": "string",
    "StatusMsg": "string",
    "UserForceClose": "int",
    "ActiveUserID": "string",
    "BrokerOrderSeq": "int",
    "RelativeOrderSysID": "string",
    "ZCETotalTradedVolume": "int",
    "IsSwapOrder": "int",
    "BranchID": "string",
    "InvestUnitID": "string",
    "AccountID": "string",
    "CurrencyID": "string",
    "reserve3": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "ExchangeInstID": "string",
    "IPAddress": "string",
}

CThostFtdcExchangeOrderField = {
    "OrderPriceType": "char",
    "Direction": "char",
    "CombOffsetFlag": "string",
    "CombHedgeFlag": "string",
    "LimitPrice": "double",
    "VolumeTotalOriginal": "int",
    "TimeCondition": "char",
    "GTDDate": "string",
    "VolumeCondition": "char",
    "MinVolume": "int",
    "ContingentCondition": "char",
    "StopPrice": "double",
    "ForceCloseReason": "char",
    "IsAutoSuspend": "int",
    "BusinessUnit": "string",
    "RequestID": "int",
    "OrderLocalID": "string",
    "ExchangeID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "reserve1": "string",
    "TraderID": "string",
    "InstallID": "int",
    "OrderSubmitStatus": "char",
    "NotifySequence": "int",
    "TradingDay": "string",
    "SettlementID": "int",
    "OrderSysID": "string",
    "OrderSource": "char",
    "OrderStatus": "char",
    "OrderType": "char",
    "VolumeTraded": "int",
    "VolumeTotal": "int",
    "InsertDate": "string",
    "InsertTime": "string",
    "ActiveTime": "string",
    "SuspendTime": "string",
    "UpdateTime": "string",
    "CancelTime": "string",
    "ActiveTraderID": "string",
    "ClearingPartID": "string",
    "SequenceNo": "int",
    "BranchID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "ExchangeInstID": "string",
    "IPAddress": "string",
}

CThostFtdcExchangeOrderInsertErrorField = {
    "ExchangeID": "string",
    "ParticipantID": "string",
    "TraderID": "string",
    "InstallID": "int",
    "OrderLocalID": "string",
    "ErrorID": "int",
    "ErrorMsg": "string",
}

CThostFtdcInputOrderActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "OrderActionRef": "int",
    "OrderRef": "string",
    "RequestID": "int",
    "FrontID": "int",
    "SessionID": "int",
    "ExchangeID": "string",
    "OrderSysID": "string",
    "ActionFlag": "char",
    "LimitPrice": "double",
    "VolumeChange": "int",
    "UserID": "string",
    "reserve1": "string",
    "InvestUnitID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcOrderActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "OrderActionRef": "int",
    "OrderRef": "string",
    "RequestID": "int",
    "FrontID": "int",
    "SessionID": "int",
    "ExchangeID": "string",
    "OrderSysID": "string",
    "ActionFlag": "char",
    "LimitPrice": "double",
    "VolumeChange": "int",
    "ActionDate": "string",
    "ActionTime": "string",
    "TraderID": "string",
    "InstallID": "int",
    "OrderLocalID": "string",
    "ActionLocalID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "BusinessUnit": "string",
    "OrderActionStatus": "char",
    "UserID": "string",
    "StatusMsg": "string",
    "reserve1": "string",
    "BranchID": "string",
    "InvestUnitID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcExchangeOrderActionField = {
    "ExchangeID": "string",
    "OrderSysID": "string",
    "ActionFlag": "char",
    "LimitPrice": "double",
    "VolumeChange": "int",
    "ActionDate": "string",
    "ActionTime": "string",
    "TraderID": "string",
    "InstallID": "int",
    "OrderLocalID": "string",
    "ActionLocalID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "BusinessUnit": "string",
    "OrderActionStatus": "char",
    "UserID": "string",
    "BranchID": "string",
    "reserve1": "string",
    "MacAddress": "string",
    "IPAddress": "string",
}

CThostFtdcExchangeOrderActionErrorField = {
    "ExchangeID": "string",
    "OrderSysID": "string",
    "TraderID": "string",
    "InstallID": "int",
    "OrderLocalID": "string",
    "ActionLocalID": "string",
    "ErrorID": "int",
    "ErrorMsg": "string",
}

CThostFtdcExchangeTradeField = {
    "ExchangeID": "string",
    "TradeID": "string",
    "Direction": "char",
    "OrderSysID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "TradingRole": "char",
    "reserve1": "string",
    "OffsetFlag": "char",
    "HedgeFlag": "char",
    "Price": "double",
    "Volume": "int",
    "TradeDate": "string",
    "TradeTime": "string",
    "TradeType": "char",
    "PriceSource": "char",
    "TraderID": "string",
    "OrderLocalID": "string",
    "ClearingPartID": "string",
    "BusinessUnit": "string",
    "SequenceNo": "int",
    "TradeSource": "char",
    "ExchangeInstID": "string",
}

CThostFtdcTradeField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "OrderRef": "string",
    "UserID": "string",
    "ExchangeID": "string",
    "TradeID": "string",
    "Direction": "char",
    "OrderSysID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "TradingRole": "char",
    "reserve2": "string",
    "OffsetFlag": "char",
    "HedgeFlag": "char",
    "Price": "double",
    "Volume": "int",
    "TradeDate": "string",
    "TradeTime": "string",
    "TradeType": "char",
    "PriceSource": "char",
    "TraderID": "string",
    "OrderLocalID": "string",
    "ClearingPartID": "string",
    "BusinessUnit": "string",
    "SequenceNo": "int",
    "TradingDay": "string",
    "SettlementID": "int",
    "BrokerOrderSeq": "int",
    "TradeSource": "char",
    "InvestUnitID": "string",
    "InstrumentID": "string",
    "ExchangeInstID": "string",
}

CThostFtdcUserSessionField = {
    "FrontID": "int",
    "SessionID": "int",
    "BrokerID": "string",
    "UserID": "string",
    "LoginDate": "string",
    "LoginTime": "string",
    "reserve1": "string",
    "UserProductInfo": "string",
    "InterfaceProductInfo": "string",
    "ProtocolInfo": "string",
    "MacAddress": "string",
    "LoginRemark": "string",
    "IPAddress": "string",
}

CThostFtdcQryMaxOrderVolumeField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "Direction": "char",
    "OffsetFlag": "char",
    "HedgeFlag": "char",
    "MaxVolume": "int",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcSettlementInfoConfirmField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "ConfirmDate": "string",
    "ConfirmTime": "string",
    "SettlementID": "int",
    "AccountID": "string",
    "CurrencyID": "string",
}

CThostFtdcSyncDepositField = {
    "DepositSeqNo": "string",
    "BrokerID": "string",
    "InvestorID": "string",
    "Deposit": "double",
    "IsForce": "int",
    "CurrencyID": "string",
}

CThostFtdcSyncFundMortgageField = {
    "MortgageSeqNo": "string",
    "BrokerID": "string",
    "InvestorID": "string",
    "FromCurrencyID": "string",
    "MortgageAmount": "double",
    "ToCurrencyID": "string",
}

CThostFtdcBrokerSyncField = {
    "BrokerID": "string",
}

CThostFtdcSyncingInvestorField = {
    "InvestorID": "string",
    "BrokerID": "string",
    "InvestorGroupID": "string",
    "InvestorName": "string",
    "IdentifiedCardType": "char",
    "IdentifiedCardNo": "string",
    "IsActive": "int",
    "Telephone": "string",
    "Address": "string",
    "OpenDate": "string",
    "Mobile": "string",
    "CommModelID": "string",
    "MarginModelID": "string",
}

CThostFtdcSyncingTradingCodeField = {
    "InvestorID": "string",
    "BrokerID": "string",
    "ExchangeID": "string",
    "ClientID": "string",
    "IsActive": "int",
    "ClientIDType": "char",
}

CThostFtdcSyncingInvestorGroupField = {
    "BrokerID": "string",
    "InvestorGroupID": "string",
    "InvestorGroupName": "string",
}

CThostFtdcSyncingTradingAccountField = {
    "BrokerID": "string",
    "AccountID": "string",
    "PreMortgage": "double",
    "PreCredit": "double",
    "PreDeposit": "double",
    "PreBalance": "double",
    "PreMargin": "double",
    "InterestBase": "double",
    "Interest": "double",
    "Deposit": "double",
    "Withdraw": "double",
    "FrozenMargin": "double",
    "FrozenCash": "double",
    "FrozenCommission": "double",
    "CurrMargin": "double",
    "CashIn": "double",
    "Commission": "double",
    "CloseProfit": "double",
    "PositionProfit": "double",
    "Balance": "double",
    "Available": "double",
    "WithdrawQuota": "double",
    "Reserve": "double",
    "TradingDay": "string",
    "SettlementID": "int",
    "Credit": "double",
    "Mortgage": "double",
    "ExchangeMargin": "double",
    "DeliveryMargin": "double",
    "ExchangeDeliveryMargin": "double",
    "ReserveBalance": "double",
    "CurrencyID": "string",
    "PreFundMortgageIn": "double",
    "PreFundMortgageOut": "double",
    "FundMortgageIn": "double",
    "FundMortgageOut": "double",
    "FundMortgageAvailable": "double",
    "MortgageableFund": "double",
    "SpecProductMargin": "double",
    "SpecProductFrozenMargin": "double",
    "SpecProductCommission": "double",
    "SpecProductFrozenCommission": "double",
    "SpecProductPositionProfit": "double",
    "SpecProductCloseProfit": "double",
    "SpecProductPositionProfitByAlg": "double",
    "SpecProductExchangeMargin": "double",
    "FrozenSwap": "double",
    "RemainSwap": "double",
}

CThostFtdcSyncingInvestorPositionField = {
    "reserve1": "string",
    "BrokerID": "string",
    "InvestorID": "string",
    "PosiDirection": "char",
    "HedgeFlag": "char",
    "PositionDate": "char",
    "YdPosition": "int",
    "Position": "int",
    "LongFrozen": "int",
    "ShortFrozen": "int",
    "LongFrozenAmount": "double",
    "ShortFrozenAmount": "double",
    "OpenVolume": "int",
    "CloseVolume": "int",
    "OpenAmount": "double",
    "CloseAmount": "double",
    "PositionCost": "double",
    "PreMargin": "double",
    "UseMargin": "double",
    "FrozenMargin": "double",
    "FrozenCash": "double",
    "FrozenCommission": "double",
    "CashIn": "double",
    "Commission": "double",
    "CloseProfit": "double",
    "PositionProfit": "double",
    "PreSettlementPrice": "double",
    "SettlementPrice": "double",
    "TradingDay": "string",
    "SettlementID": "int",
    "OpenCost": "double",
    "ExchangeMargin": "double",
    "CombPosition": "int",
    "CombLongFrozen": "int",
    "CombShortFrozen": "int",
    "CloseProfitByDate": "double",
    "CloseProfitByTrade": "double",
    "TodayPosition": "int",
    "MarginRateByMoney": "double",
    "MarginRateByVolume": "double",
    "StrikeFrozen": "int",
    "StrikeFrozenAmount": "double",
    "AbandonFrozen": "int",
    "ExchangeID": "string",
    "YdStrikeFrozen": "int",
    "InvestUnitID": "string",
    "PositionCostOffset": "double",
    "TasPosition": "int",
    "TasPositionCost": "double",
    "InstrumentID": "string",
}

CThostFtdcSyncingInstrumentMarginRateField = {
    "reserve1": "string",
    "InvestorRange": "char",
    "BrokerID": "string",
    "InvestorID": "string",
    "HedgeFlag": "char",
    "LongMarginRatioByMoney": "double",
    "LongMarginRatioByVolume": "double",
    "ShortMarginRatioByMoney": "double",
    "ShortMarginRatioByVolume": "double",
    "IsRelative": "int",
    "InstrumentID": "string",
}

CThostFtdcSyncingInstrumentCommissionRateField = {
    "reserve1": "string",
    "InvestorRange": "char",
    "BrokerID": "string",
    "InvestorID": "string",
    "OpenRatioByMoney": "double",
    "OpenRatioByVolume": "double",
    "CloseRatioByMoney": "double",
    "CloseRatioByVolume": "double",
    "CloseTodayRatioByMoney": "double",
    "CloseTodayRatioByVolume": "double",
    "InstrumentID": "string",
}

CThostFtdcSyncingInstrumentTradingRightField = {
    "reserve1": "string",
    "InvestorRange": "char",
    "BrokerID": "string",
    "InvestorID": "string",
    "TradingRight": "char",
    "InstrumentID": "string",
}

CThostFtdcQryOrderField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "OrderSysID": "string",
    "InsertTimeStart": "string",
    "InsertTimeEnd": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcQryTradeField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "TradeID": "string",
    "TradeTimeStart": "string",
    "TradeTimeEnd": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcQryInvestorPositionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcQryTradingAccountField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "CurrencyID": "string",
    "BizType": "char",
    "AccountID": "string",
}

CThostFtdcQryInvestorField = {
    "BrokerID": "string",
    "InvestorID": "string",
}

CThostFtdcQryTradingCodeField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "ExchangeID": "string",
    "ClientID": "string",
    "ClientIDType": "char",
    "InvestUnitID": "string",
}

CThostFtdcQryInvestorGroupField = {
    "BrokerID": "string",
}

CThostFtdcQryInstrumentMarginRateField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "HedgeFlag": "char",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcQryInstrumentCommissionRateField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcQryInstrumentTradingRightField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "InstrumentID": "string",
}

CThostFtdcQryBrokerField = {
    "BrokerID": "string",
}

CThostFtdcQryTraderField = {
    "ExchangeID": "string",
    "ParticipantID": "string",
    "TraderID": "string",
}

CThostFtdcQrySuperUserFunctionField = {
    "UserID": "string",
}

CThostFtdcQryUserSessionField = {
    "FrontID": "int",
    "SessionID": "int",
    "BrokerID": "string",
    "UserID": "string",
}

CThostFtdcQryPartBrokerField = {
    "ExchangeID": "string",
    "BrokerID": "string",
    "ParticipantID": "string",
}

CThostFtdcQryFrontStatusField = {
    "FrontID": "int",
}

CThostFtdcQryExchangeOrderField = {
    "ParticipantID": "string",
    "ClientID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "TraderID": "string",
    "ExchangeInstID": "string",
}

CThostFtdcQryOrderActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "ExchangeID": "string",
}

CThostFtdcQryExchangeOrderActionField = {
    "ParticipantID": "string",
    "ClientID": "string",
    "ExchangeID": "string",
    "TraderID": "string",
}

CThostFtdcQrySuperUserField = {
    "UserID": "string",
}

CThostFtdcQryExchangeField = {
    "ExchangeID": "string",
}

CThostFtdcQryProductField = {
    "reserve1": "string",
    "ProductClass": "char",
    "ExchangeID": "string",
    "ProductID": "string",
}

CThostFtdcQryInstrumentField = {
    "reserve1": "string",
    "ExchangeID": "string",
    "reserve2": "string",
    "reserve3": "string",
    "InstrumentID": "string",
    "ExchangeInstID": "string",
    "ProductID": "string",
}

CThostFtdcQryDepthMarketDataField = {
    "reserve1": "string",
    "ExchangeID": "string",
    "InstrumentID": "string",
}

CThostFtdcQryBrokerUserField = {
    "BrokerID": "string",
    "UserID": "string",
}

CThostFtdcQryBrokerUserFunctionField = {
    "BrokerID": "string",
    "UserID": "string",
}

CThostFtdcQryTraderOfferField = {
    "ExchangeID": "string",
    "ParticipantID": "string",
    "TraderID": "string",
}

CThostFtdcQrySyncDepositField = {
    "BrokerID": "string",
    "DepositSeqNo": "string",
}

CThostFtdcQrySettlementInfoField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "TradingDay": "string",
    "AccountID": "string",
    "CurrencyID": "string",
}

CThostFtdcQryExchangeMarginRateField = {
    "BrokerID": "string",
    "reserve1": "string",
    "HedgeFlag": "char",
    "ExchangeID": "string",
    "InstrumentID": "string",
}

CThostFtdcQryExchangeMarginRateAdjustField = {
    "BrokerID": "string",
    "reserve1": "string",
    "HedgeFlag": "char",
    "InstrumentID": "string",
}

CThostFtdcQryExchangeRateField = {
    "BrokerID": "string",
    "FromCurrencyID": "string",
    "ToCurrencyID": "string",
}

CThostFtdcQrySyncFundMortgageField = {
    "BrokerID": "string",
    "MortgageSeqNo": "string",
}

CThostFtdcQryHisOrderField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "OrderSysID": "string",
    "InsertTimeStart": "string",
    "InsertTimeEnd": "string",
    "TradingDay": "string",
    "SettlementID": "int",
    "InstrumentID": "string",
}

CThostFtdcOptionInstrMiniMarginField = {
    "reserve1": "string",
    "InvestorRange": "char",
    "BrokerID": "string",
    "InvestorID": "string",
    "MinMargin": "double",
    "ValueMethod": "char",
    "IsRelative": "int",
    "InstrumentID": "string",
}

CThostFtdcOptionInstrMarginAdjustField = {
    "reserve1": "string",
    "InvestorRange": "char",
    "BrokerID": "string",
    "InvestorID": "string",
    "SShortMarginRatioByMoney": "double",
    "SShortMarginRatioByVolume": "double",
    "HShortMarginRatioByMoney": "double",
    "HShortMarginRatioByVolume": "double",
    "AShortMarginRatioByMoney": "double",
    "AShortMarginRatioByVolume": "double",
    "IsRelative": "int",
    "MShortMarginRatioByMoney": "double",
    "MShortMarginRatioByVolume": "double",
    "InstrumentID": "string",
}

CThostFtdcOptionInstrCommRateField = {
    "reserve1": "string",
    "InvestorRange": "char",
    "BrokerID": "string",
    "InvestorID": "string",
    "OpenRatioByMoney": "double",
    "OpenRatioByVolume": "double",
    "CloseRatioByMoney": "double",
    "CloseRatioByVolume": "double",
    "CloseTodayRatioByMoney": "double",
    "CloseTodayRatioByVolume": "double",
    "StrikeRatioByMoney": "double",
    "StrikeRatioByVolume": "double",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcOptionInstrTradeCostField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "HedgeFlag": "char",
    "FixedMargin": "double",
    "MiniMargin": "double",
    "Royalty": "double",
    "ExchFixedMargin": "double",
    "ExchMiniMargin": "double",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcQryOptionInstrTradeCostField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "HedgeFlag": "char",
    "InputPrice": "double",
    "UnderlyingPrice": "double",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcQryOptionInstrCommRateField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcIndexPriceField = {
    "BrokerID": "string",
    "reserve1": "string",
    "ClosePrice": "double",
    "InstrumentID": "string",
}

CThostFtdcInputExecOrderField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ExecOrderRef": "string",
    "UserID": "string",
    "Volume": "int",
    "RequestID": "int",
    "BusinessUnit": "string",
    "OffsetFlag": "char",
    "HedgeFlag": "char",
    "ActionType": "char",
    "PosiDirection": "char",
    "ReservePositionFlag": "char",
    "CloseFlag": "char",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "AccountID": "string",
    "CurrencyID": "string",
    "ClientID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcInputExecOrderActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "ExecOrderActionRef": "int",
    "ExecOrderRef": "string",
    "RequestID": "int",
    "FrontID": "int",
    "SessionID": "int",
    "ExchangeID": "string",
    "ExecOrderSysID": "string",
    "ActionFlag": "char",
    "UserID": "string",
    "reserve1": "string",
    "InvestUnitID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcExecOrderField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ExecOrderRef": "string",
    "UserID": "string",
    "Volume": "int",
    "RequestID": "int",
    "BusinessUnit": "string",
    "OffsetFlag": "char",
    "HedgeFlag": "char",
    "ActionType": "char",
    "PosiDirection": "char",
    "ReservePositionFlag": "char",
    "CloseFlag": "char",
    "ExecOrderLocalID": "string",
    "ExchangeID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "reserve2": "string",
    "TraderID": "string",
    "InstallID": "int",
    "OrderSubmitStatus": "char",
    "NotifySequence": "int",
    "TradingDay": "string",
    "SettlementID": "int",
    "ExecOrderSysID": "string",
    "InsertDate": "string",
    "InsertTime": "string",
    "CancelTime": "string",
    "ExecResult": "char",
    "ClearingPartID": "string",
    "SequenceNo": "int",
    "FrontID": "int",
    "SessionID": "int",
    "UserProductInfo": "string",
    "StatusMsg": "string",
    "ActiveUserID": "string",
    "BrokerExecOrderSeq": "int",
    "BranchID": "string",
    "InvestUnitID": "string",
    "AccountID": "string",
    "CurrencyID": "string",
    "reserve3": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "ExchangeInstID": "string",
    "IPAddress": "string",
}

CThostFtdcExecOrderActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "ExecOrderActionRef": "int",
    "ExecOrderRef": "string",
    "RequestID": "int",
    "FrontID": "int",
    "SessionID": "int",
    "ExchangeID": "string",
    "ExecOrderSysID": "string",
    "ActionFlag": "char",
    "ActionDate": "string",
    "ActionTime": "string",
    "TraderID": "string",
    "InstallID": "int",
    "ExecOrderLocalID": "string",
    "ActionLocalID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "BusinessUnit": "string",
    "OrderActionStatus": "char",
    "UserID": "string",
    "ActionType": "char",
    "StatusMsg": "string",
    "reserve1": "string",
    "BranchID": "string",
    "InvestUnitID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcQryExecOrderField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "ExecOrderSysID": "string",
    "InsertTimeStart": "string",
    "InsertTimeEnd": "string",
    "InstrumentID": "string",
}

CThostFtdcExchangeExecOrderField = {
    "Volume": "int",
    "RequestID": "int",
    "BusinessUnit": "string",
    "OffsetFlag": "char",
    "HedgeFlag": "char",
    "ActionType": "char",
    "PosiDirection": "char",
    "ReservePositionFlag": "char",
    "CloseFlag": "char",
    "ExecOrderLocalID": "string",
    "ExchangeID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "reserve1": "string",
    "TraderID": "string",
    "InstallID": "int",
    "OrderSubmitStatus": "char",
    "NotifySequence": "int",
    "TradingDay": "string",
    "SettlementID": "int",
    "ExecOrderSysID": "string",
    "InsertDate": "string",
    "InsertTime": "string",
    "CancelTime": "string",
    "ExecResult": "char",
    "ClearingPartID": "string",
    "SequenceNo": "int",
    "BranchID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "ExchangeInstID": "string",
    "IPAddress": "string",
}

CThostFtdcQryExchangeExecOrderField = {
    "ParticipantID": "string",
    "ClientID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "TraderID": "string",
    "ExchangeInstID": "string",
}

CThostFtdcQryExecOrderActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "ExchangeID": "string",
}

CThostFtdcExchangeExecOrderActionField = {
    "ExchangeID": "string",
    "ExecOrderSysID": "string",
    "ActionFlag": "char",
    "ActionDate": "string",
    "ActionTime": "string",
    "TraderID": "string",
    "InstallID": "int",
    "ExecOrderLocalID": "string",
    "ActionLocalID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "BusinessUnit": "string",
    "OrderActionStatus": "char",
    "UserID": "string",
    "ActionType": "char",
    "BranchID": "string",
    "reserve1": "string",
    "MacAddress": "string",
    "reserve2": "string",
    "Volume": "int",
    "IPAddress": "string",
    "ExchangeInstID": "string",
}

CThostFtdcQryExchangeExecOrderActionField = {
    "ParticipantID": "string",
    "ClientID": "string",
    "ExchangeID": "string",
    "TraderID": "string",
}

CThostFtdcErrExecOrderField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ExecOrderRef": "string",
    "UserID": "string",
    "Volume": "int",
    "RequestID": "int",
    "BusinessUnit": "string",
    "OffsetFlag": "char",
    "HedgeFlag": "char",
    "ActionType": "char",
    "PosiDirection": "char",
    "ReservePositionFlag": "char",
    "CloseFlag": "char",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "AccountID": "string",
    "CurrencyID": "string",
    "ClientID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "ErrorID": "int",
    "ErrorMsg": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcQryErrExecOrderField = {
    "BrokerID": "string",
    "InvestorID": "string",
}

CThostFtdcErrExecOrderActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "ExecOrderActionRef": "int",
    "ExecOrderRef": "string",
    "RequestID": "int",
    "FrontID": "int",
    "SessionID": "int",
    "ExchangeID": "string",
    "ExecOrderSysID": "string",
    "ActionFlag": "char",
    "UserID": "string",
    "reserve1": "string",
    "InvestUnitID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "ErrorID": "int",
    "ErrorMsg": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcQryErrExecOrderActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
}

CThostFtdcOptionInstrTradingRightField = {
    "reserve1": "string",
    "InvestorRange": "char",
    "BrokerID": "string",
    "InvestorID": "string",
    "Direction": "char",
    "TradingRight": "char",
    "InstrumentID": "string",
}

CThostFtdcQryOptionInstrTradingRightField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "Direction": "char",
    "InstrumentID": "string",
}

CThostFtdcInputForQuoteField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ForQuoteRef": "string",
    "UserID": "string",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcForQuoteField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ForQuoteRef": "string",
    "UserID": "string",
    "ForQuoteLocalID": "string",
    "ExchangeID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "reserve2": "string",
    "TraderID": "string",
    "InstallID": "int",
    "InsertDate": "string",
    "InsertTime": "string",
    "ForQuoteStatus": "char",
    "FrontID": "int",
    "SessionID": "int",
    "StatusMsg": "string",
    "ActiveUserID": "string",
    "BrokerForQutoSeq": "int",
    "InvestUnitID": "string",
    "reserve3": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "ExchangeInstID": "string",
    "IPAddress": "string",
}

CThostFtdcQryForQuoteField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "InsertTimeStart": "string",
    "InsertTimeEnd": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcExchangeForQuoteField = {
    "ForQuoteLocalID": "string",
    "ExchangeID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "reserve1": "string",
    "TraderID": "string",
    "InstallID": "int",
    "InsertDate": "string",
    "InsertTime": "string",
    "ForQuoteStatus": "char",
    "reserve2": "string",
    "MacAddress": "string",
    "ExchangeInstID": "string",
    "IPAddress": "string",
}

CThostFtdcQryExchangeForQuoteField = {
    "ParticipantID": "string",
    "ClientID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "TraderID": "string",
    "ExchangeInstID": "string",
}

CThostFtdcInputQuoteField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "QuoteRef": "string",
    "UserID": "string",
    "AskPrice": "double",
    "BidPrice": "double",
    "AskVolume": "int",
    "BidVolume": "int",
    "RequestID": "int",
    "BusinessUnit": "string",
    "AskOffsetFlag": "char",
    "BidOffsetFlag": "char",
    "AskHedgeFlag": "char",
    "BidHedgeFlag": "char",
    "AskOrderRef": "string",
    "BidOrderRef": "string",
    "ForQuoteSysID": "string",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "ClientID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcInputQuoteActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "QuoteActionRef": "int",
    "QuoteRef": "string",
    "RequestID": "int",
    "FrontID": "int",
    "SessionID": "int",
    "ExchangeID": "string",
    "QuoteSysID": "string",
    "ActionFlag": "char",
    "UserID": "string",
    "reserve1": "string",
    "InvestUnitID": "string",
    "ClientID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcQuoteField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "QuoteRef": "string",
    "UserID": "string",
    "AskPrice": "double",
    "BidPrice": "double",
    "AskVolume": "int",
    "BidVolume": "int",
    "RequestID": "int",
    "BusinessUnit": "string",
    "AskOffsetFlag": "char",
    "BidOffsetFlag": "char",
    "AskHedgeFlag": "char",
    "BidHedgeFlag": "char",
    "QuoteLocalID": "string",
    "ExchangeID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "reserve2": "string",
    "TraderID": "string",
    "InstallID": "int",
    "NotifySequence": "int",
    "OrderSubmitStatus": "char",
    "TradingDay": "string",
    "SettlementID": "int",
    "QuoteSysID": "string",
    "InsertDate": "string",
    "InsertTime": "string",
    "CancelTime": "string",
    "QuoteStatus": "char",
    "ClearingPartID": "string",
    "SequenceNo": "int",
    "AskOrderSysID": "string",
    "BidOrderSysID": "string",
    "FrontID": "int",
    "SessionID": "int",
    "UserProductInfo": "string",
    "StatusMsg": "string",
    "ActiveUserID": "string",
    "BrokerQuoteSeq": "int",
    "AskOrderRef": "string",
    "BidOrderRef": "string",
    "ForQuoteSysID": "string",
    "BranchID": "string",
    "InvestUnitID": "string",
    "AccountID": "string",
    "CurrencyID": "string",
    "reserve3": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "ExchangeInstID": "string",
    "IPAddress": "string",
}

CThostFtdcQuoteActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "QuoteActionRef": "int",
    "QuoteRef": "string",
    "RequestID": "int",
    "FrontID": "int",
    "SessionID": "int",
    "ExchangeID": "string",
    "QuoteSysID": "string",
    "ActionFlag": "char",
    "ActionDate": "string",
    "ActionTime": "string",
    "TraderID": "string",
    "InstallID": "int",
    "QuoteLocalID": "string",
    "ActionLocalID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "BusinessUnit": "string",
    "OrderActionStatus": "char",
    "UserID": "string",
    "StatusMsg": "string",
    "reserve1": "string",
    "BranchID": "string",
    "InvestUnitID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcQryQuoteField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "QuoteSysID": "string",
    "InsertTimeStart": "string",
    "InsertTimeEnd": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcExchangeQuoteField = {
    "AskPrice": "double",
    "BidPrice": "double",
    "AskVolume": "int",
    "BidVolume": "int",
    "RequestID": "int",
    "BusinessUnit": "string",
    "AskOffsetFlag": "char",
    "BidOffsetFlag": "char",
    "AskHedgeFlag": "char",
    "BidHedgeFlag": "char",
    "QuoteLocalID": "string",
    "ExchangeID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "reserve1": "string",
    "TraderID": "string",
    "InstallID": "int",
    "NotifySequence": "int",
    "OrderSubmitStatus": "char",
    "TradingDay": "string",
    "SettlementID": "int",
    "QuoteSysID": "string",
    "InsertDate": "string",
    "InsertTime": "string",
    "CancelTime": "string",
    "QuoteStatus": "char",
    "ClearingPartID": "string",
    "SequenceNo": "int",
    "AskOrderSysID": "string",
    "BidOrderSysID": "string",
    "ForQuoteSysID": "string",
    "BranchID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "ExchangeInstID": "string",
    "IPAddress": "string",
}

CThostFtdcQryExchangeQuoteField = {
    "ParticipantID": "string",
    "ClientID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "TraderID": "string",
    "ExchangeInstID": "string",
}

CThostFtdcQryQuoteActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "ExchangeID": "string",
}

CThostFtdcExchangeQuoteActionField = {
    "ExchangeID": "string",
    "QuoteSysID": "string",
    "ActionFlag": "char",
    "ActionDate": "string",
    "ActionTime": "string",
    "TraderID": "string",
    "InstallID": "int",
    "QuoteLocalID": "string",
    "ActionLocalID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "BusinessUnit": "string",
    "OrderActionStatus": "char",
    "UserID": "string",
    "reserve1": "string",
    "MacAddress": "string",
    "IPAddress": "string",
}

CThostFtdcQryExchangeQuoteActionField = {
    "ParticipantID": "string",
    "ClientID": "string",
    "ExchangeID": "string",
    "TraderID": "string",
}

CThostFtdcOptionInstrDeltaField = {
    "reserve1": "string",
    "InvestorRange": "char",
    "BrokerID": "string",
    "InvestorID": "string",
    "Delta": "double",
    "InstrumentID": "string",
}

CThostFtdcForQuoteRspField = {
    "TradingDay": "string",
    "reserve1": "string",
    "ForQuoteSysID": "string",
    "ForQuoteTime": "string",
    "ActionDay": "string",
    "ExchangeID": "string",
    "InstrumentID": "string",
}

CThostFtdcStrikeOffsetField = {
    "reserve1": "string",
    "InvestorRange": "char",
    "BrokerID": "string",
    "InvestorID": "string",
    "Offset": "double",
    "OffsetType": "char",
    "InstrumentID": "string",
}

CThostFtdcQryStrikeOffsetField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "InstrumentID": "string",
}

CThostFtdcInputBatchOrderActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "OrderActionRef": "int",
    "RequestID": "int",
    "FrontID": "int",
    "SessionID": "int",
    "ExchangeID": "string",
    "UserID": "string",
    "InvestUnitID": "string",
    "reserve1": "string",
    "MacAddress": "string",
    "IPAddress": "string",
}

CThostFtdcBatchOrderActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "OrderActionRef": "int",
    "RequestID": "int",
    "FrontID": "int",
    "SessionID": "int",
    "ExchangeID": "string",
    "ActionDate": "string",
    "ActionTime": "string",
    "TraderID": "string",
    "InstallID": "int",
    "ActionLocalID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "BusinessUnit": "string",
    "OrderActionStatus": "char",
    "UserID": "string",
    "StatusMsg": "string",
    "InvestUnitID": "string",
    "reserve1": "string",
    "MacAddress": "string",
    "IPAddress": "string",
}

CThostFtdcExchangeBatchOrderActionField = {
    "ExchangeID": "string",
    "ActionDate": "string",
    "ActionTime": "string",
    "TraderID": "string",
    "InstallID": "int",
    "ActionLocalID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "BusinessUnit": "string",
    "OrderActionStatus": "char",
    "UserID": "string",
    "reserve1": "string",
    "MacAddress": "string",
    "IPAddress": "string",
}

CThostFtdcQryBatchOrderActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "ExchangeID": "string",
}

CThostFtdcCombInstrumentGuardField = {
    "BrokerID": "string",
    "reserve1": "string",
    "GuarantRatio": "double",
    "ExchangeID": "string",
    "InstrumentID": "string",
}

CThostFtdcQryCombInstrumentGuardField = {
    "BrokerID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "InstrumentID": "string",
}

CThostFtdcInputCombActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "CombActionRef": "string",
    "UserID": "string",
    "Direction": "char",
    "Volume": "int",
    "CombDirection": "char",
    "HedgeFlag": "char",
    "ExchangeID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "InvestUnitID": "string",
    "FrontID": "int",
    "SessionID": "int",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcCombActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "CombActionRef": "string",
    "UserID": "string",
    "Direction": "char",
    "Volume": "int",
    "CombDirection": "char",
    "HedgeFlag": "char",
    "ActionLocalID": "string",
    "ExchangeID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "reserve2": "string",
    "TraderID": "string",
    "InstallID": "int",
    "ActionStatus": "char",
    "NotifySequence": "int",
    "TradingDay": "string",
    "SettlementID": "int",
    "SequenceNo": "int",
    "FrontID": "int",
    "SessionID": "int",
    "UserProductInfo": "string",
    "StatusMsg": "string",
    "reserve3": "string",
    "MacAddress": "string",
    "ComTradeID": "string",
    "BranchID": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
    "ExchangeInstID": "string",
    "IPAddress": "string",
}

CThostFtdcQryCombActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcExchangeCombActionField = {
    "Direction": "char",
    "Volume": "int",
    "CombDirection": "char",
    "HedgeFlag": "char",
    "ActionLocalID": "string",
    "ExchangeID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "reserve1": "string",
    "TraderID": "string",
    "InstallID": "int",
    "ActionStatus": "char",
    "NotifySequence": "int",
    "TradingDay": "string",
    "SettlementID": "int",
    "SequenceNo": "int",
    "reserve2": "string",
    "MacAddress": "string",
    "ComTradeID": "string",
    "BranchID": "string",
    "ExchangeInstID": "string",
    "IPAddress": "string",
}

CThostFtdcQryExchangeCombActionField = {
    "ParticipantID": "string",
    "ClientID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "TraderID": "string",
    "ExchangeInstID": "string",
}

CThostFtdcProductExchRateField = {
    "reserve1": "string",
    "QuoteCurrencyID": "string",
    "ExchangeRate": "double",
    "ExchangeID": "string",
    "ProductID": "string",
}

CThostFtdcQryProductExchRateField = {
    "reserve1": "string",
    "ExchangeID": "string",
    "ProductID": "string",
}

CThostFtdcQryForQuoteParamField = {
    "BrokerID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "InstrumentID": "string",
}

CThostFtdcForQuoteParamField = {
    "BrokerID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "LastPrice": "double",
    "PriceInterval": "double",
    "InstrumentID": "string",
}

CThostFtdcMMOptionInstrCommRateField = {
    "reserve1": "string",
    "InvestorRange": "char",
    "BrokerID": "string",
    "InvestorID": "string",
    "OpenRatioByMoney": "double",
    "OpenRatioByVolume": "double",
    "CloseRatioByMoney": "double",
    "CloseRatioByVolume": "double",
    "CloseTodayRatioByMoney": "double",
    "CloseTodayRatioByVolume": "double",
    "StrikeRatioByMoney": "double",
    "StrikeRatioByVolume": "double",
    "InstrumentID": "string",
}

CThostFtdcQryMMOptionInstrCommRateField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "InstrumentID": "string",
}

CThostFtdcMMInstrumentCommissionRateField = {
    "reserve1": "string",
    "InvestorRange": "char",
    "BrokerID": "string",
    "InvestorID": "string",
    "OpenRatioByMoney": "double",
    "OpenRatioByVolume": "double",
    "CloseRatioByMoney": "double",
    "CloseRatioByVolume": "double",
    "CloseTodayRatioByMoney": "double",
    "CloseTodayRatioByVolume": "double",
    "InstrumentID": "string",
}

CThostFtdcQryMMInstrumentCommissionRateField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "InstrumentID": "string",
}

CThostFtdcInstrumentOrderCommRateField = {
    "reserve1": "string",
    "InvestorRange": "char",
    "BrokerID": "string",
    "InvestorID": "string",
    "HedgeFlag": "char",
    "OrderCommByVolume": "double",
    "OrderActionCommByVolume": "double",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcQryInstrumentOrderCommRateField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "InstrumentID": "string",
}

CThostFtdcTradeParamField = {
    "BrokerID": "string",
    "TradeParamID": "char",
    "TradeParamValue": "string",
    "Memo": "string",
}

CThostFtdcInstrumentMarginRateULField = {
    "reserve1": "string",
    "InvestorRange": "char",
    "BrokerID": "string",
    "InvestorID": "string",
    "HedgeFlag": "char",
    "LongMarginRatioByMoney": "double",
    "LongMarginRatioByVolume": "double",
    "ShortMarginRatioByMoney": "double",
    "ShortMarginRatioByVolume": "double",
    "InstrumentID": "string",
}

CThostFtdcFutureLimitPosiParamField = {
    "InvestorRange": "char",
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "SpecOpenVolume": "int",
    "ArbiOpenVolume": "int",
    "OpenVolume": "int",
    "ProductID": "string",
}

CThostFtdcLoginForbiddenIPField = {
    "reserve1": "string",
    "IPAddress": "string",
}

CThostFtdcIPListField = {
    "reserve1": "string",
    "IsWhite": "int",
    "IPAddress": "string",
}

CThostFtdcInputOptionSelfCloseField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "OptionSelfCloseRef": "string",
    "UserID": "string",
    "Volume": "int",
    "RequestID": "int",
    "BusinessUnit": "string",
    "HedgeFlag": "char",
    "OptSelfCloseFlag": "char",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "AccountID": "string",
    "CurrencyID": "string",
    "ClientID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcInputOptionSelfCloseActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "OptionSelfCloseActionRef": "int",
    "OptionSelfCloseRef": "string",
    "RequestID": "int",
    "FrontID": "int",
    "SessionID": "int",
    "ExchangeID": "string",
    "OptionSelfCloseSysID": "string",
    "ActionFlag": "char",
    "UserID": "string",
    "reserve1": "string",
    "InvestUnitID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcOptionSelfCloseField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "OptionSelfCloseRef": "string",
    "UserID": "string",
    "Volume": "int",
    "RequestID": "int",
    "BusinessUnit": "string",
    "HedgeFlag": "char",
    "OptSelfCloseFlag": "char",
    "OptionSelfCloseLocalID": "string",
    "ExchangeID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "reserve2": "string",
    "TraderID": "string",
    "InstallID": "int",
    "OrderSubmitStatus": "char",
    "NotifySequence": "int",
    "TradingDay": "string",
    "SettlementID": "int",
    "OptionSelfCloseSysID": "string",
    "InsertDate": "string",
    "InsertTime": "string",
    "CancelTime": "string",
    "ExecResult": "char",
    "ClearingPartID": "string",
    "SequenceNo": "int",
    "FrontID": "int",
    "SessionID": "int",
    "UserProductInfo": "string",
    "StatusMsg": "string",
    "ActiveUserID": "string",
    "BrokerOptionSelfCloseSeq": "int",
    "BranchID": "string",
    "InvestUnitID": "string",
    "AccountID": "string",
    "CurrencyID": "string",
    "reserve3": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "ExchangeInstID": "string",
    "IPAddress": "string",
}

CThostFtdcOptionSelfCloseActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "OptionSelfCloseActionRef": "int",
    "OptionSelfCloseRef": "string",
    "RequestID": "int",
    "FrontID": "int",
    "SessionID": "int",
    "ExchangeID": "string",
    "OptionSelfCloseSysID": "string",
    "ActionFlag": "char",
    "ActionDate": "string",
    "ActionTime": "string",
    "TraderID": "string",
    "InstallID": "int",
    "OptionSelfCloseLocalID": "string",
    "ActionLocalID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "BusinessUnit": "string",
    "OrderActionStatus": "char",
    "UserID": "string",
    "StatusMsg": "string",
    "reserve1": "string",
    "BranchID": "string",
    "InvestUnitID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcQryOptionSelfCloseField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "OptionSelfCloseSysID": "string",
    "InsertTimeStart": "string",
    "InsertTimeEnd": "string",
    "InstrumentID": "string",
}

CThostFtdcExchangeOptionSelfCloseField = {
    "Volume": "int",
    "RequestID": "int",
    "BusinessUnit": "string",
    "HedgeFlag": "char",
    "OptSelfCloseFlag": "char",
    "OptionSelfCloseLocalID": "string",
    "ExchangeID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "reserve1": "string",
    "TraderID": "string",
    "InstallID": "int",
    "OrderSubmitStatus": "char",
    "NotifySequence": "int",
    "TradingDay": "string",
    "SettlementID": "int",
    "OptionSelfCloseSysID": "string",
    "InsertDate": "string",
    "InsertTime": "string",
    "CancelTime": "string",
    "ExecResult": "char",
    "ClearingPartID": "string",
    "SequenceNo": "int",
    "BranchID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "ExchangeInstID": "string",
    "IPAddress": "string",
}

CThostFtdcQryOptionSelfCloseActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "ExchangeID": "string",
}

CThostFtdcExchangeOptionSelfCloseActionField = {
    "ExchangeID": "string",
    "OptionSelfCloseSysID": "string",
    "ActionFlag": "char",
    "ActionDate": "string",
    "ActionTime": "string",
    "TraderID": "string",
    "InstallID": "int",
    "OptionSelfCloseLocalID": "string",
    "ActionLocalID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "BusinessUnit": "string",
    "OrderActionStatus": "char",
    "UserID": "string",
    "BranchID": "string",
    "reserve1": "string",
    "MacAddress": "string",
    "reserve2": "string",
    "OptSelfCloseFlag": "char",
    "IPAddress": "string",
    "ExchangeInstID": "string",
}

CThostFtdcSyncDelaySwapField = {
    "DelaySwapSeqNo": "string",
    "BrokerID": "string",
    "InvestorID": "string",
    "FromCurrencyID": "string",
    "FromAmount": "double",
    "FromFrozenSwap": "double",
    "FromRemainSwap": "double",
    "ToCurrencyID": "string",
    "ToAmount": "double",
    "IsManualSwap": "int",
    "IsAllRemainSetZero": "int",
}

CThostFtdcQrySyncDelaySwapField = {
    "BrokerID": "string",
    "DelaySwapSeqNo": "string",
}

CThostFtdcInvestUnitField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "InvestUnitID": "string",
    "InvestorUnitName": "string",
    "InvestorGroupID": "string",
    "CommModelID": "string",
    "MarginModelID": "string",
    "AccountID": "string",
    "CurrencyID": "string",
}

CThostFtdcQryInvestUnitField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "InvestUnitID": "string",
}

CThostFtdcSecAgentCheckModeField = {
    "InvestorID": "string",
    "BrokerID": "string",
    "CurrencyID": "string",
    "BrokerSecAgentID": "string",
    "CheckSelfAccount": "int",
}

CThostFtdcSecAgentTradeInfoField = {
    "BrokerID": "string",
    "BrokerSecAgentID": "string",
    "InvestorID": "string",
    "LongCustomerName": "string",
}

CThostFtdcMarketDataField = {
    "TradingDay": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "reserve2": "string",
    "LastPrice": "double",
    "PreSettlementPrice": "double",
    "PreClosePrice": "double",
    "PreOpenInterest": "double",
    "OpenPrice": "double",
    "HighestPrice": "double",
    "LowestPrice": "double",
    "Volume": "int",
    "Turnover": "double",
    "OpenInterest": "double",
    "ClosePrice": "double",
    "SettlementPrice": "double",
    "UpperLimitPrice": "double",
    "LowerLimitPrice": "double",
    "PreDelta": "double",
    "CurrDelta": "double",
    "UpdateTime": "string",
    "UpdateMillisec": "int",
    "ActionDay": "string",
    "InstrumentID": "string",
    "ExchangeInstID": "string",
}

CThostFtdcMarketDataBaseField = {
    "TradingDay": "string",
    "PreSettlementPrice": "double",
    "PreClosePrice": "double",
    "PreOpenInterest": "double",
    "PreDelta": "double",
}

CThostFtdcMarketDataStaticField = {
    "OpenPrice": "double",
    "HighestPrice": "double",
    "LowestPrice": "double",
    "ClosePrice": "double",
    "UpperLimitPrice": "double",
    "LowerLimitPrice": "double",
    "SettlementPrice": "double",
    "CurrDelta": "double",
}

CThostFtdcMarketDataLastMatchField = {
    "LastPrice": "double",
    "Volume": "int",
    "Turnover": "double",
    "OpenInterest": "double",
}

CThostFtdcMarketDataBestPriceField = {
    "BidPrice1": "double",
    "BidVolume1": "int",
    "AskPrice1": "double",
    "AskVolume1": "int",
}

CThostFtdcMarketDataBid23Field = {
    "BidPrice2": "double",
    "BidVolume2": "int",
    "BidPrice3": "double",
    "BidVolume3": "int",
}

CThostFtdcMarketDataAsk23Field = {
    "AskPrice2": "double",
    "AskVolume2": "int",
    "AskPrice3": "double",
    "AskVolume3": "int",
}

CThostFtdcMarketDataBid45Field = {
    "BidPrice4": "double",
    "BidVolume4": "int",
    "BidPrice5": "double",
    "BidVolume5": "int",
}

CThostFtdcMarketDataAsk45Field = {
    "AskPrice4": "double",
    "AskVolume4": "int",
    "AskPrice5": "double",
    "AskVolume5": "int",
}

CThostFtdcMarketDataUpdateTimeField = {
    "reserve1": "string",
    "UpdateTime": "string",
    "UpdateMillisec": "int",
    "ActionDay": "string",
    "InstrumentID": "string",
}

CThostFtdcMarketDataExchangeField = {
    "ExchangeID": "string",
}

CThostFtdcSpecificInstrumentField = {
    "reserve1": "string",
    "InstrumentID": "string",
}

CThostFtdcInstrumentStatusField = {
    "ExchangeID": "string",
    "reserve1": "string",
    "SettlementGroupID": "string",
    "reserve2": "string",
    "InstrumentStatus": "char",
    "TradingSegmentSN": "int",
    "EnterTime": "string",
    "EnterReason": "char",
    "ExchangeInstID": "string",
    "InstrumentID": "string",
}

CThostFtdcQryInstrumentStatusField = {
    "ExchangeID": "string",
    "reserve1": "string",
    "ExchangeInstID": "string",
}

CThostFtdcInvestorAccountField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "AccountID": "string",
    "CurrencyID": "string",
}

CThostFtdcPositionProfitAlgorithmField = {
    "BrokerID": "string",
    "AccountID": "string",
    "Algorithm": "char",
    "Memo": "string",
    "CurrencyID": "string",
}

CThostFtdcDiscountField = {
    "BrokerID": "string",
    "InvestorRange": "char",
    "InvestorID": "string",
    "Discount": "double",
}

CThostFtdcQryTransferBankField = {
    "BankID": "string",
    "BankBrchID": "string",
}

CThostFtdcTransferBankField = {
    "BankID": "string",
    "BankBrchID": "string",
    "BankName": "string",
    "IsActive": "int",
}

CThostFtdcQryInvestorPositionDetailField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcInvestorPositionDetailField = {
    "reserve1": "string",
    "BrokerID": "string",
    "InvestorID": "string",
    "HedgeFlag": "char",
    "Direction": "char",
    "OpenDate": "string",
    "TradeID": "string",
    "Volume": "int",
    "OpenPrice": "double",
    "TradingDay": "string",
    "SettlementID": "int",
    "TradeType": "char",
    "reserve2": "string",
    "ExchangeID": "string",
    "CloseProfitByDate": "double",
    "CloseProfitByTrade": "double",
    "PositionProfitByDate": "double",
    "PositionProfitByTrade": "double",
    "Margin": "double",
    "ExchMargin": "double",
    "MarginRateByMoney": "double",
    "MarginRateByVolume": "double",
    "LastSettlementPrice": "double",
    "SettlementPrice": "double",
    "CloseVolume": "int",
    "CloseAmount": "double",
    "TimeFirstVolume": "int",
    "InvestUnitID": "string",
    "SpecPosiType": "char",
    "InstrumentID": "string",
    "CombInstrumentID": "string",
}

CThostFtdcTradingAccountPasswordField = {
    "BrokerID": "string",
    "AccountID": "string",
    "Password": "string",
    "CurrencyID": "string",
}

CThostFtdcMDTraderOfferField = {
    "ExchangeID": "string",
    "TraderID": "string",
    "ParticipantID": "string",
    "Password": "string",
    "InstallID": "int",
    "OrderLocalID": "string",
    "TraderConnectStatus": "char",
    "ConnectRequestDate": "string",
    "ConnectRequestTime": "string",
    "LastReportDate": "string",
    "LastReportTime": "string",
    "ConnectDate": "string",
    "ConnectTime": "string",
    "StartDate": "string",
    "StartTime": "string",
    "TradingDay": "string",
    "BrokerID": "string",
    "MaxTradeID": "string",
    "MaxOrderMessageReference": "string",
}

CThostFtdcQryMDTraderOfferField = {
    "ExchangeID": "string",
    "ParticipantID": "string",
    "TraderID": "string",
}

CThostFtdcQryNoticeField = {
    "BrokerID": "string",
}

CThostFtdcNoticeField = {
    "BrokerID": "string",
    "Content": "string",
    "SequenceLabel": "string",
}

CThostFtdcUserRightField = {
    "BrokerID": "string",
    "UserID": "string",
    "UserRightType": "char",
    "IsForbidden": "int",
}

CThostFtdcQrySettlementInfoConfirmField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "AccountID": "string",
    "CurrencyID": "string",
}

CThostFtdcLoadSettlementInfoField = {
    "BrokerID": "string",
}

CThostFtdcBrokerWithdrawAlgorithmField = {
    "BrokerID": "string",
    "WithdrawAlgorithm": "char",
    "UsingRatio": "double",
    "IncludeCloseProfit": "char",
    "AllWithoutTrade": "char",
    "AvailIncludeCloseProfit": "char",
    "IsBrokerUserEvent": "int",
    "CurrencyID": "string",
    "FundMortgageRatio": "double",
    "BalanceAlgorithm": "char",
}

CThostFtdcTradingAccountPasswordUpdateV1Field = {
    "BrokerID": "string",
    "InvestorID": "string",
    "OldPassword": "string",
    "NewPassword": "string",
}

CThostFtdcTradingAccountPasswordUpdateField = {
    "BrokerID": "string",
    "AccountID": "string",
    "OldPassword": "string",
    "NewPassword": "string",
    "CurrencyID": "string",
}

CThostFtdcQryCombinationLegField = {
    "reserve1": "string",
    "LegID": "int",
    "reserve2": "string",
    "CombInstrumentID": "string",
    "LegInstrumentID": "string",
}

CThostFtdcQrySyncStatusField = {
    "TradingDay": "string",
}

CThostFtdcCombinationLegField = {
    "reserve1": "string",
    "LegID": "int",
    "reserve2": "string",
    "Direction": "char",
    "LegMultiple": "int",
    "ImplyLevel": "int",
    "CombInstrumentID": "string",
    "LegInstrumentID": "string",
}

CThostFtdcSyncStatusField = {
    "TradingDay": "string",
    "DataSyncStatus": "char",
}

CThostFtdcQryLinkManField = {
    "BrokerID": "string",
    "InvestorID": "string",
}

CThostFtdcLinkManField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "PersonType": "char",
    "IdentifiedCardType": "char",
    "IdentifiedCardNo": "string",
    "PersonName": "string",
    "Telephone": "string",
    "Address": "string",
    "ZipCode": "string",
    "Priority": "int",
    "UOAZipCode": "string",
    "PersonFullName": "string",
}

CThostFtdcQryBrokerUserEventField = {
    "BrokerID": "string",
    "UserID": "string",
    "UserEventType": "char",
}

CThostFtdcBrokerUserEventField = {
    "BrokerID": "string",
    "UserID": "string",
    "UserEventType": "char",
    "EventSequenceNo": "int",
    "EventDate": "string",
    "EventTime": "string",
    "UserEventInfo": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "InstrumentID": "string",
}

CThostFtdcQryContractBankField = {
    "BrokerID": "string",
    "BankID": "string",
    "BankBrchID": "string",
}

CThostFtdcContractBankField = {
    "BrokerID": "string",
    "BankID": "string",
    "BankBrchID": "string",
    "BankName": "string",
}

CThostFtdcInvestorPositionCombineDetailField = {
    "TradingDay": "string",
    "OpenDate": "string",
    "ExchangeID": "string",
    "SettlementID": "int",
    "BrokerID": "string",
    "InvestorID": "string",
    "ComTradeID": "string",
    "TradeID": "string",
    "reserve1": "string",
    "HedgeFlag": "char",
    "Direction": "char",
    "TotalAmt": "int",
    "Margin": "double",
    "ExchMargin": "double",
    "MarginRateByMoney": "double",
    "MarginRateByVolume": "double",
    "LegID": "int",
    "LegMultiple": "int",
    "reserve2": "string",
    "TradeGroupID": "int",
    "InvestUnitID": "string",
    "InstrumentID": "string",
    "CombInstrumentID": "string",
}

CThostFtdcParkedOrderField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "OrderRef": "string",
    "UserID": "string",
    "OrderPriceType": "char",
    "Direction": "char",
    "CombOffsetFlag": "string",
    "CombHedgeFlag": "string",
    "LimitPrice": "double",
    "VolumeTotalOriginal": "int",
    "TimeCondition": "char",
    "GTDDate": "string",
    "VolumeCondition": "char",
    "MinVolume": "int",
    "ContingentCondition": "char",
    "StopPrice": "double",
    "ForceCloseReason": "char",
    "IsAutoSuspend": "int",
    "BusinessUnit": "string",
    "RequestID": "int",
    "UserForceClose": "int",
    "ExchangeID": "string",
    "ParkedOrderID": "string",
    "UserType": "char",
    "Status": "char",
    "ErrorID": "int",
    "ErrorMsg": "string",
    "IsSwapOrder": "int",
    "AccountID": "string",
    "CurrencyID": "string",
    "ClientID": "string",
    "InvestUnitID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcParkedOrderActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "OrderActionRef": "int",
    "OrderRef": "string",
    "RequestID": "int",
    "FrontID": "int",
    "SessionID": "int",
    "ExchangeID": "string",
    "OrderSysID": "string",
    "ActionFlag": "char",
    "LimitPrice": "double",
    "VolumeChange": "int",
    "UserID": "string",
    "reserve1": "string",
    "ParkedOrderActionID": "string",
    "UserType": "char",
    "Status": "char",
    "ErrorID": "int",
    "ErrorMsg": "string",
    "InvestUnitID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcQryParkedOrderField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcQryParkedOrderActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcRemoveParkedOrderField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "ParkedOrderID": "string",
    "InvestUnitID": "string",
}

CThostFtdcRemoveParkedOrderActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "ParkedOrderActionID": "string",
    "InvestUnitID": "string",
}

CThostFtdcInvestorWithdrawAlgorithmField = {
    "BrokerID": "string",
    "InvestorRange": "char",
    "InvestorID": "string",
    "UsingRatio": "double",
    "CurrencyID": "string",
    "FundMortgageRatio": "double",
}

CThostFtdcQryInvestorPositionCombineDetailField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "CombInstrumentID": "string",
}

CThostFtdcMarketDataAveragePriceField = {
    "AveragePrice": "double",
}

CThostFtdcVerifyInvestorPasswordField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "Password": "string",
}

CThostFtdcUserIPField = {
    "BrokerID": "string",
    "UserID": "string",
    "reserve1": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "IPAddress": "string",
    "IPMask": "string",
}

CThostFtdcTradingNoticeInfoField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "SendTime": "string",
    "FieldContent": "string",
    "SequenceSeries": "int",
    "SequenceNo": "int",
    "InvestUnitID": "string",
}

CThostFtdcTradingNoticeField = {
    "BrokerID": "string",
    "InvestorRange": "char",
    "InvestorID": "string",
    "SequenceSeries": "int",
    "UserID": "string",
    "SendTime": "string",
    "SequenceNo": "int",
    "FieldContent": "string",
    "InvestUnitID": "string",
}

CThostFtdcQryTradingNoticeField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "InvestUnitID": "string",
}

CThostFtdcQryErrOrderField = {
    "BrokerID": "string",
    "InvestorID": "string",
}

CThostFtdcErrOrderField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "OrderRef": "string",
    "UserID": "string",
    "OrderPriceType": "char",
    "Direction": "char",
    "CombOffsetFlag": "string",
    "CombHedgeFlag": "string",
    "LimitPrice": "double",
    "VolumeTotalOriginal": "int",
    "TimeCondition": "char",
    "GTDDate": "string",
    "VolumeCondition": "char",
    "MinVolume": "int",
    "ContingentCondition": "char",
    "StopPrice": "double",
    "ForceCloseReason": "char",
    "IsAutoSuspend": "int",
    "BusinessUnit": "string",
    "RequestID": "int",
    "UserForceClose": "int",
    "ErrorID": "int",
    "ErrorMsg": "string",
    "IsSwapOrder": "int",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "AccountID": "string",
    "CurrencyID": "string",
    "ClientID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcErrorConditionalOrderField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "OrderRef": "string",
    "UserID": "string",
    "OrderPriceType": "char",
    "Direction": "char",
    "CombOffsetFlag": "string",
    "CombHedgeFlag": "string",
    "LimitPrice": "double",
    "VolumeTotalOriginal": "int",
    "TimeCondition": "char",
    "GTDDate": "string",
    "VolumeCondition": "char",
    "MinVolume": "int",
    "ContingentCondition": "char",
    "StopPrice": "double",
    "ForceCloseReason": "char",
    "IsAutoSuspend": "int",
    "BusinessUnit": "string",
    "RequestID": "int",
    "OrderLocalID": "string",
    "ExchangeID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "reserve2": "string",
    "TraderID": "string",
    "InstallID": "int",
    "OrderSubmitStatus": "char",
    "NotifySequence": "int",
    "TradingDay": "string",
    "SettlementID": "int",
    "OrderSysID": "string",
    "OrderSource": "char",
    "OrderStatus": "char",
    "OrderType": "char",
    "VolumeTraded": "int",
    "VolumeTotal": "int",
    "InsertDate": "string",
    "InsertTime": "string",
    "ActiveTime": "string",
    "SuspendTime": "string",
    "UpdateTime": "string",
    "CancelTime": "string",
    "ActiveTraderID": "string",
    "ClearingPartID": "string",
    "SequenceNo": "int",
    "FrontID": "int",
    "SessionID": "int",
    "UserProductInfo": "string",
    "StatusMsg": "string",
    "UserForceClose": "int",
    "ActiveUserID": "string",
    "BrokerOrderSeq": "int",
    "RelativeOrderSysID": "string",
    "ZCETotalTradedVolume": "int",
    "ErrorID": "int",
    "ErrorMsg": "string",
    "IsSwapOrder": "int",
    "BranchID": "string",
    "InvestUnitID": "string",
    "AccountID": "string",
    "CurrencyID": "string",
    "reserve3": "string",
    "MacAddress": "string",
    "InstrumentID": "string",
    "ExchangeInstID": "string",
    "IPAddress": "string",
}

CThostFtdcQryErrOrderActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
}

CThostFtdcErrOrderActionField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "OrderActionRef": "int",
    "OrderRef": "string",
    "RequestID": "int",
    "FrontID": "int",
    "SessionID": "int",
    "ExchangeID": "string",
    "OrderSysID": "string",
    "ActionFlag": "char",
    "LimitPrice": "double",
    "VolumeChange": "int",
    "ActionDate": "string",
    "ActionTime": "string",
    "TraderID": "string",
    "InstallID": "int",
    "OrderLocalID": "string",
    "ActionLocalID": "string",
    "ParticipantID": "string",
    "ClientID": "string",
    "BusinessUnit": "string",
    "OrderActionStatus": "char",
    "UserID": "string",
    "StatusMsg": "string",
    "reserve1": "string",
    "BranchID": "string",
    "InvestUnitID": "string",
    "reserve2": "string",
    "MacAddress": "string",
    "ErrorID": "int",
    "ErrorMsg": "string",
    "InstrumentID": "string",
    "IPAddress": "string",
}

CThostFtdcQryExchangeSequenceField = {
    "ExchangeID": "string",
}

CThostFtdcExchangeSequenceField = {
    "ExchangeID": "string",
    "SequenceNo": "int",
    "MarketStatus": "char",
}

CThostFtdcQryMaxOrderVolumeWithPriceField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "Direction": "char",
    "OffsetFlag": "char",
    "HedgeFlag": "char",
    "MaxVolume": "int",
    "Price": "double",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcQryBrokerTradingParamsField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "CurrencyID": "string",
    "AccountID": "string",
}

CThostFtdcBrokerTradingParamsField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "MarginPriceType": "char",
    "Algorithm": "char",
    "AvailIncludeCloseProfit": "char",
    "CurrencyID": "string",
    "OptionRoyaltyPriceType": "char",
    "AccountID": "string",
}

CThostFtdcQryBrokerTradingAlgosField = {
    "BrokerID": "string",
    "ExchangeID": "string",
    "reserve1": "string",
    "InstrumentID": "string",
}

CThostFtdcBrokerTradingAlgosField = {
    "BrokerID": "string",
    "ExchangeID": "string",
    "reserve1": "string",
    "HandlePositionAlgoID": "char",
    "FindMarginRateAlgoID": "char",
    "HandleTradingAccountAlgoID": "char",
    "InstrumentID": "string",
}

CThostFtdcQueryBrokerDepositField = {
    "BrokerID": "string",
    "ExchangeID": "string",
}

CThostFtdcBrokerDepositField = {
    "TradingDay": "string",
    "BrokerID": "string",
    "ParticipantID": "string",
    "ExchangeID": "string",
    "PreBalance": "double",
    "CurrMargin": "double",
    "CloseProfit": "double",
    "Balance": "double",
    "Deposit": "double",
    "Withdraw": "double",
    "Available": "double",
    "Reserve": "double",
    "FrozenMargin": "double",
}

CThostFtdcQryCFMMCBrokerKeyField = {
    "BrokerID": "string",
}

CThostFtdcCFMMCBrokerKeyField = {
    "BrokerID": "string",
    "ParticipantID": "string",
    "CreateDate": "string",
    "CreateTime": "string",
    "KeyID": "int",
    "CurrentKey": "string",
    "KeyKind": "char",
}

CThostFtdcCFMMCTradingAccountKeyField = {
    "BrokerID": "string",
    "ParticipantID": "string",
    "AccountID": "string",
    "KeyID": "int",
    "CurrentKey": "string",
}

CThostFtdcQryCFMMCTradingAccountKeyField = {
    "BrokerID": "string",
    "InvestorID": "string",
}

CThostFtdcBrokerUserOTPParamField = {
    "BrokerID": "string",
    "UserID": "string",
    "OTPVendorsID": "string",
    "SerialNumber": "string",
    "AuthKey": "string",
    "LastDrift": "int",
    "LastSuccess": "int",
    "OTPType": "char",
}

CThostFtdcManualSyncBrokerUserOTPField = {
    "BrokerID": "string",
    "UserID": "string",
    "OTPType": "char",
    "FirstOTP": "string",
    "SecondOTP": "string",
}

CThostFtdcCommRateModelField = {
    "BrokerID": "string",
    "CommModelID": "string",
    "CommModelName": "string",
}

CThostFtdcQryCommRateModelField = {
    "BrokerID": "string",
    "CommModelID": "string",
}

CThostFtdcMarginModelField = {
    "BrokerID": "string",
    "MarginModelID": "string",
    "MarginModelName": "string",
}

CThostFtdcQryMarginModelField = {
    "BrokerID": "string",
    "MarginModelID": "string",
}

CThostFtdcEWarrantOffsetField = {
    "TradingDay": "string",
    "BrokerID": "string",
    "InvestorID": "string",
    "ExchangeID": "string",
    "reserve1": "string",
    "Direction": "char",
    "HedgeFlag": "char",
    "Volume": "int",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcQryEWarrantOffsetField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "ExchangeID": "string",
    "reserve1": "string",
    "InvestUnitID": "string",
    "InstrumentID": "string",
}

CThostFtdcQryInvestorProductGroupMarginField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "reserve1": "string",
    "HedgeFlag": "char",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "ProductGroupID": "string",
}

CThostFtdcInvestorProductGroupMarginField = {
    "reserve1": "string",
    "BrokerID": "string",
    "InvestorID": "string",
    "TradingDay": "string",
    "SettlementID": "int",
    "FrozenMargin": "double",
    "LongFrozenMargin": "double",
    "ShortFrozenMargin": "double",
    "UseMargin": "double",
    "LongUseMargin": "double",
    "ShortUseMargin": "double",
    "ExchMargin": "double",
    "LongExchMargin": "double",
    "ShortExchMargin": "double",
    "CloseProfit": "double",
    "FrozenCommission": "double",
    "Commission": "double",
    "FrozenCash": "double",
    "CashIn": "double",
    "PositionProfit": "double",
    "OffsetAmount": "double",
    "LongOffsetAmount": "double",
    "ShortOffsetAmount": "double",
    "ExchOffsetAmount": "double",
    "LongExchOffsetAmount": "double",
    "ShortExchOffsetAmount": "double",
    "HedgeFlag": "char",
    "ExchangeID": "string",
    "InvestUnitID": "string",
    "ProductGroupID": "string",
}

CThostFtdcQueryCFMMCTradingAccountTokenField = {
    "BrokerID": "string",
    "InvestorID": "string",
    "InvestUnitID": "string",
}

CThostFtdcCFMMCTradingAccountTokenField = {
    "BrokerID": "string",
    "ParticipantID": "string",
    "AccountID": "string",
    "KeyID": "int",
    "Token": "string",
}

CThostFtdcQryProductGroupField = {
    "reserve1": "string",
    "ExchangeID": "string",
    "ProductID": "string",
}

CThostFtdcProductGroupField = {
    "reserve1": "string",
    "ExchangeID": "string",
    "reserve2": "string",
    "ProductID": "string",
    "ProductGroupID": "string",
}

CThostFtdcBulletinField = {
    "ExchangeID": "string",
    "TradingDay": "string",
    "BulletinID": "int",
    "SequenceNo": "int",
    "NewsType": "string",
    "NewsUrgency": "char",
    "SendTime": "string",
    "Abstract": "string",
    "ComeFrom": "string",
    "Content": "string",
    "URLLink": "string",
    "MarketID": "string",
}

CThostFtdcQryBulletinField = {
    "ExchangeID": "string",
    "BulletinID": "int",
    "SequenceNo": "int",
    "NewsType": "string",
    "NewsUrgency": "char",
}

CThostFtdcMulticastInstrumentField = {
    "TopicID": "int",
    "reserve1": "string",
    "InstrumentNo": "int",
    "CodePrice": "double",
    "VolumeMultiple": "int",
    "PriceTick": "double",
    "InstrumentID": "string",
}

CThostFtdcQryMulticastInstrumentField = {
    "TopicID": "int",
    "reserve1": "string",
    "InstrumentID": "string",
}

CThostFtdcAppIDAuthAssignField = {
    "BrokerID": "string",
    "AppID": "string",
    "DRIdentityID": "int",
}

CThostFtdcReqOpenAccountField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "CustomerName": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "Gender": "char",
    "CountryCode": "string",
    "CustType": "char",
    "Address": "string",
    "ZipCode": "string",
    "Telephone": "string",
    "MobilePhone": "string",
    "Fax": "string",
    "EMail": "string",
    "MoneyAccountStatus": "char",
    "BankAccount": "string",
    "BankPassWord": "string",
    "AccountID": "string",
    "Password": "string",
    "InstallID": "int",
    "VerifyCertNoFlag": "char",
    "CurrencyID": "string",
    "CashExchangeCode": "char",
    "Digest": "string",
    "BankAccType": "char",
    "DeviceID": "string",
    "BankSecuAccType": "char",
    "BrokerIDByBank": "string",
    "BankSecuAcc": "string",
    "BankPwdFlag": "char",
    "SecuPwdFlag": "char",
    "OperNo": "string",
    "TID": "int",
    "UserID": "string",
    "LongCustomerName": "string",
}

CThostFtdcReqCancelAccountField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "CustomerName": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "Gender": "char",
    "CountryCode": "string",
    "CustType": "char",
    "Address": "string",
    "ZipCode": "string",
    "Telephone": "string",
    "MobilePhone": "string",
    "Fax": "string",
    "EMail": "string",
    "MoneyAccountStatus": "char",
    "BankAccount": "string",
    "BankPassWord": "string",
    "AccountID": "string",
    "Password": "string",
    "InstallID": "int",
    "VerifyCertNoFlag": "char",
    "CurrencyID": "string",
    "CashExchangeCode": "char",
    "Digest": "string",
    "BankAccType": "char",
    "DeviceID": "string",
    "BankSecuAccType": "char",
    "BrokerIDByBank": "string",
    "BankSecuAcc": "string",
    "BankPwdFlag": "char",
    "SecuPwdFlag": "char",
    "OperNo": "string",
    "TID": "int",
    "UserID": "string",
    "LongCustomerName": "string",
}

CThostFtdcReqChangeAccountField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "CustomerName": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "Gender": "char",
    "CountryCode": "string",
    "CustType": "char",
    "Address": "string",
    "ZipCode": "string",
    "Telephone": "string",
    "MobilePhone": "string",
    "Fax": "string",
    "EMail": "string",
    "MoneyAccountStatus": "char",
    "BankAccount": "string",
    "BankPassWord": "string",
    "NewBankAccount": "string",
    "NewBankPassWord": "string",
    "AccountID": "string",
    "Password": "string",
    "BankAccType": "char",
    "InstallID": "int",
    "VerifyCertNoFlag": "char",
    "CurrencyID": "string",
    "BrokerIDByBank": "string",
    "BankPwdFlag": "char",
    "SecuPwdFlag": "char",
    "TID": "int",
    "Digest": "string",
    "LongCustomerName": "string",
}

CThostFtdcReqTransferField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "CustomerName": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "CustType": "char",
    "BankAccount": "string",
    "BankPassWord": "string",
    "AccountID": "string",
    "Password": "string",
    "InstallID": "int",
    "FutureSerial": "int",
    "UserID": "string",
    "VerifyCertNoFlag": "char",
    "CurrencyID": "string",
    "TradeAmount": "double",
    "FutureFetchAmount": "double",
    "FeePayFlag": "char",
    "CustFee": "double",
    "BrokerFee": "double",
    "Message": "string",
    "Digest": "string",
    "BankAccType": "char",
    "DeviceID": "string",
    "BankSecuAccType": "char",
    "BrokerIDByBank": "string",
    "BankSecuAcc": "string",
    "BankPwdFlag": "char",
    "SecuPwdFlag": "char",
    "OperNo": "string",
    "RequestID": "int",
    "TID": "int",
    "TransferStatus": "char",
    "LongCustomerName": "string",
}

CThostFtdcRspTransferField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "CustomerName": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "CustType": "char",
    "BankAccount": "string",
    "BankPassWord": "string",
    "AccountID": "string",
    "Password": "string",
    "InstallID": "int",
    "FutureSerial": "int",
    "UserID": "string",
    "VerifyCertNoFlag": "char",
    "CurrencyID": "string",
    "TradeAmount": "double",
    "FutureFetchAmount": "double",
    "FeePayFlag": "char",
    "CustFee": "double",
    "BrokerFee": "double",
    "Message": "string",
    "Digest": "string",
    "BankAccType": "char",
    "DeviceID": "string",
    "BankSecuAccType": "char",
    "BrokerIDByBank": "string",
    "BankSecuAcc": "string",
    "BankPwdFlag": "char",
    "SecuPwdFlag": "char",
    "OperNo": "string",
    "RequestID": "int",
    "TID": "int",
    "TransferStatus": "char",
    "ErrorID": "int",
    "ErrorMsg": "string",
    "LongCustomerName": "string",
}

CThostFtdcReqRepealField = {
    "RepealTimeInterval": "int",
    "RepealedTimes": "int",
    "BankRepealFlag": "char",
    "BrokerRepealFlag": "char",
    "PlateRepealSerial": "int",
    "BankRepealSerial": "string",
    "FutureRepealSerial": "int",
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "CustomerName": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "CustType": "char",
    "BankAccount": "string",
    "BankPassWord": "string",
    "AccountID": "string",
    "Password": "string",
    "InstallID": "int",
    "FutureSerial": "int",
    "UserID": "string",
    "VerifyCertNoFlag": "char",
    "CurrencyID": "string",
    "TradeAmount": "double",
    "FutureFetchAmount": "double",
    "FeePayFlag": "char",
    "CustFee": "double",
    "BrokerFee": "double",
    "Message": "string",
    "Digest": "string",
    "BankAccType": "char",
    "DeviceID": "string",
    "BankSecuAccType": "char",
    "BrokerIDByBank": "string",
    "BankSecuAcc": "string",
    "BankPwdFlag": "char",
    "SecuPwdFlag": "char",
    "OperNo": "string",
    "RequestID": "int",
    "TID": "int",
    "TransferStatus": "char",
    "LongCustomerName": "string",
}

CThostFtdcRspRepealField = {
    "RepealTimeInterval": "int",
    "RepealedTimes": "int",
    "BankRepealFlag": "char",
    "BrokerRepealFlag": "char",
    "PlateRepealSerial": "int",
    "BankRepealSerial": "string",
    "FutureRepealSerial": "int",
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "CustomerName": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "CustType": "char",
    "BankAccount": "string",
    "BankPassWord": "string",
    "AccountID": "string",
    "Password": "string",
    "InstallID": "int",
    "FutureSerial": "int",
    "UserID": "string",
    "VerifyCertNoFlag": "char",
    "CurrencyID": "string",
    "TradeAmount": "double",
    "FutureFetchAmount": "double",
    "FeePayFlag": "char",
    "CustFee": "double",
    "BrokerFee": "double",
    "Message": "string",
    "Digest": "string",
    "BankAccType": "char",
    "DeviceID": "string",
    "BankSecuAccType": "char",
    "BrokerIDByBank": "string",
    "BankSecuAcc": "string",
    "BankPwdFlag": "char",
    "SecuPwdFlag": "char",
    "OperNo": "string",
    "RequestID": "int",
    "TID": "int",
    "TransferStatus": "char",
    "ErrorID": "int",
    "ErrorMsg": "string",
    "LongCustomerName": "string",
}

CThostFtdcReqQueryAccountField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "CustomerName": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "CustType": "char",
    "BankAccount": "string",
    "BankPassWord": "string",
    "AccountID": "string",
    "Password": "string",
    "FutureSerial": "int",
    "InstallID": "int",
    "UserID": "string",
    "VerifyCertNoFlag": "char",
    "CurrencyID": "string",
    "Digest": "string",
    "BankAccType": "char",
    "DeviceID": "string",
    "BankSecuAccType": "char",
    "BrokerIDByBank": "string",
    "BankSecuAcc": "string",
    "BankPwdFlag": "char",
    "SecuPwdFlag": "char",
    "OperNo": "string",
    "RequestID": "int",
    "TID": "int",
    "LongCustomerName": "string",
}

CThostFtdcRspQueryAccountField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "CustomerName": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "CustType": "char",
    "BankAccount": "string",
    "BankPassWord": "string",
    "AccountID": "string",
    "Password": "string",
    "FutureSerial": "int",
    "InstallID": "int",
    "UserID": "string",
    "VerifyCertNoFlag": "char",
    "CurrencyID": "string",
    "Digest": "string",
    "BankAccType": "char",
    "DeviceID": "string",
    "BankSecuAccType": "char",
    "BrokerIDByBank": "string",
    "BankSecuAcc": "string",
    "BankPwdFlag": "char",
    "SecuPwdFlag": "char",
    "OperNo": "string",
    "RequestID": "int",
    "TID": "int",
    "BankUseAmount": "double",
    "BankFetchAmount": "double",
    "LongCustomerName": "string",
}

CThostFtdcFutureSignIOField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "InstallID": "int",
    "UserID": "string",
    "Digest": "string",
    "CurrencyID": "string",
    "DeviceID": "string",
    "BrokerIDByBank": "string",
    "OperNo": "string",
    "RequestID": "int",
    "TID": "int",
}

CThostFtdcRspFutureSignInField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "InstallID": "int",
    "UserID": "string",
    "Digest": "string",
    "CurrencyID": "string",
    "DeviceID": "string",
    "BrokerIDByBank": "string",
    "OperNo": "string",
    "RequestID": "int",
    "TID": "int",
    "ErrorID": "int",
    "ErrorMsg": "string",
    "PinKey": "string",
    "MacKey": "string",
}

CThostFtdcReqFutureSignOutField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "InstallID": "int",
    "UserID": "string",
    "Digest": "string",
    "CurrencyID": "string",
    "DeviceID": "string",
    "BrokerIDByBank": "string",
    "OperNo": "string",
    "RequestID": "int",
    "TID": "int",
}

CThostFtdcRspFutureSignOutField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "InstallID": "int",
    "UserID": "string",
    "Digest": "string",
    "CurrencyID": "string",
    "DeviceID": "string",
    "BrokerIDByBank": "string",
    "OperNo": "string",
    "RequestID": "int",
    "TID": "int",
    "ErrorID": "int",
    "ErrorMsg": "string",
}

CThostFtdcReqQueryTradeResultBySerialField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "Reference": "int",
    "RefrenceIssureType": "char",
    "RefrenceIssure": "string",
    "CustomerName": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "CustType": "char",
    "BankAccount": "string",
    "BankPassWord": "string",
    "AccountID": "string",
    "Password": "string",
    "CurrencyID": "string",
    "TradeAmount": "double",
    "Digest": "string",
    "LongCustomerName": "string",
}

CThostFtdcRspQueryTradeResultBySerialField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "ErrorID": "int",
    "ErrorMsg": "string",
    "Reference": "int",
    "RefrenceIssureType": "char",
    "RefrenceIssure": "string",
    "OriginReturnCode": "string",
    "OriginDescrInfoForReturnCode": "string",
    "BankAccount": "string",
    "BankPassWord": "string",
    "AccountID": "string",
    "Password": "string",
    "CurrencyID": "string",
    "TradeAmount": "double",
    "Digest": "string",
}

CThostFtdcReqDayEndFileReadyField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "FileBusinessCode": "char",
    "Digest": "string",
}

CThostFtdcReturnResultField = {
    "ReturnCode": "string",
    "DescrInfoForReturnCode": "string",
}

CThostFtdcVerifyFuturePasswordField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "AccountID": "string",
    "Password": "string",
    "BankAccount": "string",
    "BankPassWord": "string",
    "InstallID": "int",
    "TID": "int",
    "CurrencyID": "string",
}

CThostFtdcVerifyCustInfoField = {
    "CustomerName": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "CustType": "char",
    "LongCustomerName": "string",
}

CThostFtdcVerifyFuturePasswordAndCustInfoField = {
    "CustomerName": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "CustType": "char",
    "AccountID": "string",
    "Password": "string",
    "CurrencyID": "string",
    "LongCustomerName": "string",
}

CThostFtdcDepositResultInformField = {
    "DepositSeqNo": "string",
    "BrokerID": "string",
    "InvestorID": "string",
    "Deposit": "double",
    "RequestID": "int",
    "ReturnCode": "string",
    "DescrInfoForReturnCode": "string",
}

CThostFtdcReqSyncKeyField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "InstallID": "int",
    "UserID": "string",
    "Message": "string",
    "DeviceID": "string",
    "BrokerIDByBank": "string",
    "OperNo": "string",
    "RequestID": "int",
    "TID": "int",
}

CThostFtdcRspSyncKeyField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "InstallID": "int",
    "UserID": "string",
    "Message": "string",
    "DeviceID": "string",
    "BrokerIDByBank": "string",
    "OperNo": "string",
    "RequestID": "int",
    "TID": "int",
    "ErrorID": "int",
    "ErrorMsg": "string",
}

CThostFtdcNotifyQueryAccountField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "CustomerName": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "CustType": "char",
    "BankAccount": "string",
    "BankPassWord": "string",
    "AccountID": "string",
    "Password": "string",
    "FutureSerial": "int",
    "InstallID": "int",
    "UserID": "string",
    "VerifyCertNoFlag": "char",
    "CurrencyID": "string",
    "Digest": "string",
    "BankAccType": "char",
    "DeviceID": "string",
    "BankSecuAccType": "char",
    "BrokerIDByBank": "string",
    "BankSecuAcc": "string",
    "BankPwdFlag": "char",
    "SecuPwdFlag": "char",
    "OperNo": "string",
    "RequestID": "int",
    "TID": "int",
    "BankUseAmount": "double",
    "BankFetchAmount": "double",
    "ErrorID": "int",
    "ErrorMsg": "string",
    "LongCustomerName": "string",
}

CThostFtdcTransferSerialField = {
    "PlateSerial": "int",
    "TradeDate": "string",
    "TradingDay": "string",
    "TradeTime": "string",
    "TradeCode": "string",
    "SessionID": "int",
    "BankID": "string",
    "BankBranchID": "string",
    "BankAccType": "char",
    "BankAccount": "string",
    "BankSerial": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "FutureAccType": "char",
    "AccountID": "string",
    "InvestorID": "string",
    "FutureSerial": "int",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "CurrencyID": "string",
    "TradeAmount": "double",
    "CustFee": "double",
    "BrokerFee": "double",
    "AvailabilityFlag": "char",
    "OperatorCode": "string",
    "BankNewAccount": "string",
    "ErrorID": "int",
    "ErrorMsg": "string",
}

CThostFtdcQryTransferSerialField = {
    "BrokerID": "string",
    "AccountID": "string",
    "BankID": "string",
    "CurrencyID": "string",
}

CThostFtdcNotifyFutureSignInField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "InstallID": "int",
    "UserID": "string",
    "Digest": "string",
    "CurrencyID": "string",
    "DeviceID": "string",
    "BrokerIDByBank": "string",
    "OperNo": "string",
    "RequestID": "int",
    "TID": "int",
    "ErrorID": "int",
    "ErrorMsg": "string",
    "PinKey": "string",
    "MacKey": "string",
}

CThostFtdcNotifyFutureSignOutField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "InstallID": "int",
    "UserID": "string",
    "Digest": "string",
    "CurrencyID": "string",
    "DeviceID": "string",
    "BrokerIDByBank": "string",
    "OperNo": "string",
    "RequestID": "int",
    "TID": "int",
    "ErrorID": "int",
    "ErrorMsg": "string",
}

CThostFtdcNotifySyncKeyField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "InstallID": "int",
    "UserID": "string",
    "Message": "string",
    "DeviceID": "string",
    "BrokerIDByBank": "string",
    "OperNo": "string",
    "RequestID": "int",
    "TID": "int",
    "ErrorID": "int",
    "ErrorMsg": "string",
}

CThostFtdcQryAccountregisterField = {
    "BrokerID": "string",
    "AccountID": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "CurrencyID": "string",
}

CThostFtdcAccountregisterField = {
    "TradeDay": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BankAccount": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "AccountID": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "CustomerName": "string",
    "CurrencyID": "string",
    "OpenOrDestroy": "char",
    "RegDate": "string",
    "OutDate": "string",
    "TID": "int",
    "CustType": "char",
    "BankAccType": "char",
    "LongCustomerName": "string",
}

CThostFtdcOpenAccountField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "CustomerName": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "Gender": "char",
    "CountryCode": "string",
    "CustType": "char",
    "Address": "string",
    "ZipCode": "string",
    "Telephone": "string",
    "MobilePhone": "string",
    "Fax": "string",
    "EMail": "string",
    "MoneyAccountStatus": "char",
    "BankAccount": "string",
    "BankPassWord": "string",
    "AccountID": "string",
    "Password": "string",
    "InstallID": "int",
    "VerifyCertNoFlag": "char",
    "CurrencyID": "string",
    "CashExchangeCode": "char",
    "Digest": "string",
    "BankAccType": "char",
    "DeviceID": "string",
    "BankSecuAccType": "char",
    "BrokerIDByBank": "string",
    "BankSecuAcc": "string",
    "BankPwdFlag": "char",
    "SecuPwdFlag": "char",
    "OperNo": "string",
    "TID": "int",
    "UserID": "string",
    "ErrorID": "int",
    "ErrorMsg": "string",
    "LongCustomerName": "string",
}

CThostFtdcCancelAccountField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "CustomerName": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "Gender": "char",
    "CountryCode": "string",
    "CustType": "char",
    "Address": "string",
    "ZipCode": "string",
    "Telephone": "string",
    "MobilePhone": "string",
    "Fax": "string",
    "EMail": "string",
    "MoneyAccountStatus": "char",
    "BankAccount": "string",
    "BankPassWord": "string",
    "AccountID": "string",
    "Password": "string",
    "InstallID": "int",
    "VerifyCertNoFlag": "char",
    "CurrencyID": "string",
    "CashExchangeCode": "char",
    "Digest": "string",
    "BankAccType": "char",
    "DeviceID": "string",
    "BankSecuAccType": "char",
    "BrokerIDByBank": "string",
    "BankSecuAcc": "string",
    "BankPwdFlag": "char",
    "SecuPwdFlag": "char",
    "OperNo": "string",
    "TID": "int",
    "UserID": "string",
    "ErrorID": "int",
    "ErrorMsg": "string",
    "LongCustomerName": "string",
}

CThostFtdcChangeAccountField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "CustomerName": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "Gender": "char",
    "CountryCode": "string",
    "CustType": "char",
    "Address": "string",
    "ZipCode": "string",
    "Telephone": "string",
    "MobilePhone": "string",
    "Fax": "string",
    "EMail": "string",
    "MoneyAccountStatus": "char",
    "BankAccount": "string",
    "BankPassWord": "string",
    "NewBankAccount": "string",
    "NewBankPassWord": "string",
    "AccountID": "string",
    "Password": "string",
    "BankAccType": "char",
    "InstallID": "int",
    "VerifyCertNoFlag": "char",
    "CurrencyID": "string",
    "BrokerIDByBank": "string",
    "BankPwdFlag": "char",
    "SecuPwdFlag": "char",
    "TID": "int",
    "Digest": "string",
    "ErrorID": "int",
    "ErrorMsg": "string",
    "LongCustomerName": "string",
}

CThostFtdcSecAgentACIDMapField = {
    "BrokerID": "string",
    "UserID": "string",
    "AccountID": "string",
    "CurrencyID": "string",
    "BrokerSecAgentID": "string",
}

CThostFtdcQrySecAgentACIDMapField = {
    "BrokerID": "string",
    "UserID": "string",
    "AccountID": "string",
    "CurrencyID": "string",
}

CThostFtdcUserRightsAssignField = {
    "BrokerID": "string",
    "UserID": "string",
    "DRIdentityID": "int",
}

CThostFtdcBrokerUserRightAssignField = {
    "BrokerID": "string",
    "DRIdentityID": "int",
    "Tradeable": "int",
}

CThostFtdcDRTransferField = {
    "OrigDRIdentityID": "int",
    "DestDRIdentityID": "int",
    "OrigBrokerID": "string",
    "DestBrokerID": "string",
}

CThostFtdcFensUserInfoField = {
    "BrokerID": "string",
    "UserID": "string",
    "LoginMode": "char",
}

CThostFtdcCurrTransferIdentityField = {
    "IdentityID": "int",
}

CThostFtdcLoginForbiddenUserField = {
    "BrokerID": "string",
    "UserID": "string",
    "reserve1": "string",
    "IPAddress": "string",
}

CThostFtdcQryLoginForbiddenUserField = {
    "BrokerID": "string",
    "UserID": "string",
}

CThostFtdcTradingAccountReserveField = {
    "BrokerID": "string",
    "AccountID": "string",
    "Reserve": "double",
    "CurrencyID": "string",
}

CThostFtdcQryLoginForbiddenIPField = {
    "reserve1": "string",
    "IPAddress": "string",
}

CThostFtdcQryIPListField = {
    "reserve1": "string",
    "IPAddress": "string",
}

CThostFtdcQryUserRightsAssignField = {
    "BrokerID": "string",
    "UserID": "string",
}

CThostFtdcReserveOpenAccountConfirmField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "CustomerName": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "Gender": "char",
    "CountryCode": "string",
    "CustType": "char",
    "Address": "string",
    "ZipCode": "string",
    "Telephone": "string",
    "MobilePhone": "string",
    "Fax": "string",
    "EMail": "string",
    "MoneyAccountStatus": "char",
    "BankAccount": "string",
    "BankPassWord": "string",
    "InstallID": "int",
    "VerifyCertNoFlag": "char",
    "CurrencyID": "string",
    "Digest": "string",
    "BankAccType": "char",
    "BrokerIDByBank": "string",
    "TID": "int",
    "AccountID": "string",
    "Password": "string",
    "BankReserveOpenSeq": "string",
    "BookDate": "string",
    "BookPsw": "string",
    "ErrorID": "int",
    "ErrorMsg": "string",
}

CThostFtdcReserveOpenAccountField = {
    "TradeCode": "string",
    "BankID": "string",
    "BankBranchID": "string",
    "BrokerID": "string",
    "BrokerBranchID": "string",
    "TradeDate": "string",
    "TradeTime": "string",
    "BankSerial": "string",
    "TradingDay": "string",
    "PlateSerial": "int",
    "LastFragment": "char",
    "SessionID": "int",
    "CustomerName": "string",
    "IdCardType": "char",
    "IdentifiedCardNo": "string",
    "Gender": "char",
    "CountryCode": "string",
    "CustType": "char",
    "Address": "string",
    "ZipCode": "string",
    "Telephone": "string",
    "MobilePhone": "string",
    "Fax": "string",
    "EMail": "string",
    "MoneyAccountStatus": "char",
    "BankAccount": "string",
    "BankPassWord": "string",
    "InstallID": "int",
    "VerifyCertNoFlag": "char",
    "CurrencyID": "string",
    "Digest": "string",
    "BankAccType": "char",
    "BrokerIDByBank": "string",
    "TID": "int",
    "ReserveOpenAccStas": "char",
    "ErrorID": "int",
    "ErrorMsg": "string",
}

CThostFtdcAccountPropertyField = {
    "BrokerID": "string",
    "AccountID": "string",
    "BankID": "string",
    "BankAccount": "string",
    "OpenName": "string",
    "OpenBank": "string",
    "IsActive": "int",
    "AccountSourceType": "char",
    "OpenDate": "string",
    "CancelDate": "string",
    "OperatorID": "string",
    "OperateDate": "string",
    "OperateTime": "string",
    "CurrencyID": "string",
}

CThostFtdcQryCurrDRIdentityField = {
    "DRIdentityID": "int",
}

CThostFtdcCurrDRIdentityField = {
    "DRIdentityID": "int",
}

CThostFtdcQrySecAgentCheckModeField = {
    "BrokerID": "string",
    "InvestorID": "string",
}

CThostFtdcQrySecAgentTradeInfoField = {
    "BrokerID": "string",
    "BrokerSecAgentID": "string",
}

CThostFtdcReqUserAuthMethodField = {
    "TradingDay": "string",
    "BrokerID": "string",
    "UserID": "string",
}

CThostFtdcRspUserAuthMethodField = {
    "UsableAuthMethod": "int",
}

CThostFtdcReqGenUserCaptchaField = {
    "TradingDay": "string",
    "BrokerID": "string",
    "UserID": "string",
}

CThostFtdcRspGenUserCaptchaField = {
    "BrokerID": "string",
    "UserID": "string",
    "CaptchaInfoLen": "int",
    "CaptchaInfo": "string",
}

CThostFtdcReqGenUserTextField = {
    "TradingDay": "string",
    "BrokerID": "string",
    "UserID": "string",
}

CThostFtdcRspGenUserTextField = {
    "UserTextSeq": "int",
}

CThostFtdcReqUserLoginWithCaptchaField = {
    "TradingDay": "string",
    "BrokerID": "string",
    "UserID": "string",
    "Password": "string",
    "UserProductInfo": "string",
    "InterfaceProductInfo": "string",
    "ProtocolInfo": "string",
    "MacAddress": "string",
    "reserve1": "string",
    "LoginRemark": "string",
    "Captcha": "string",
    "ClientIPPort": "int",
    "ClientIPAddress": "string",
}

CThostFtdcReqUserLoginWithTextField = {
    "TradingDay": "string",
    "BrokerID": "string",
    "UserID": "string",
    "Password": "string",
    "UserProductInfo": "string",
    "InterfaceProductInfo": "string",
    "ProtocolInfo": "string",
    "MacAddress": "string",
    "reserve1": "string",
    "LoginRemark": "string",
    "Text": "string",
    "ClientIPPort": "int",
    "ClientIPAddress": "string",
}

CThostFtdcReqUserLoginWithOTPField = {
    "TradingDay": "string",
    "BrokerID": "string",
    "UserID": "string",
    "Password": "string",
    "UserProductInfo": "string",
    "InterfaceProductInfo": "string",
    "ProtocolInfo": "string",
    "MacAddress": "string",
    "reserve1": "string",
    "LoginRemark": "string",
    "OTPPassword": "string",
    "ClientIPPort": "int",
    "ClientIPAddress": "string",
}

CThostFtdcReqApiHandshakeField = {
    "CryptoKeyVersion": "string",
}

CThostFtdcRspApiHandshakeField = {
    "FrontHandshakeDataLen": "int",
    "FrontHandshakeData": "string",
    "IsApiAuthEnabled": "int",
}

CThostFtdcReqVerifyApiKeyField = {
    "ApiHandshakeDataLen": "int",
    "ApiHandshakeData": "string",
}

CThostFtdcDepartmentUserField = {
    "BrokerID": "string",
    "UserID": "string",
    "InvestorRange": "char",
    "InvestorID": "string",
}

CThostFtdcQueryFreqField = {
    "QueryFreq": "int",
}

CThostFtdcAuthForbiddenIPField = {
    "reserve1": "string",
    "IPAddress": "string",
}

CThostFtdcQryAuthForbiddenIPField = {
    "reserve1": "string",
    "IPAddress": "string",
}

CThostFtdcSyncDelaySwapFrozenField = {
    "DelaySwapSeqNo": "string",
    "BrokerID": "string",
    "InvestorID": "string",
    "FromCurrencyID": "string",
    "FromRemainSwap": "double",
    "IsManualSwap": "int",
}

CThostFtdcUserSystemInfoField = {
    "BrokerID": "string",
    "UserID": "string",
    "ClientSystemInfoLen": "int",
    "ClientSystemInfo": "string",
    "reserve1": "string",
    "ClientIPPort": "int",
    "ClientLoginTime": "string",
    "ClientAppID": "string",
    "ClientPublicIP": "string",
}

CThostFtdcAuthUserIDField = {
    "BrokerID": "string",
    "AppID": "string",
    "UserID": "string",
    "AuthType": "char",
}

CThostFtdcAuthIPField = {
    "BrokerID": "string",
    "AppID": "string",
    "IPAddress": "string",
}

CThostFtdcQryClassifiedInstrumentField = {
    "InstrumentID": "string",
    "ExchangeID": "string",
    "ExchangeInstID": "string",
    "ProductID": "string",
    "TradingType": "char",
    "ClassType": "char",
}

CThostFtdcQryCombPromotionParamField = {
    "ExchangeID": "string",
    "InstrumentID": "string",
}

CThostFtdcCombPromotionParamField = {
    "ExchangeID": "string",
    "InstrumentID": "string",
    "CombHedgeFlag": "string",
    "Xparameter": "double",
}

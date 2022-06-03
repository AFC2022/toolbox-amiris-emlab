from domain.powerplant import *
import logging

class CandidatePowerPlant(PowerPlant):
    def __init__(self, name):
        super().__init__(name)
        # results from Amiris
        self.AwardedPowerinMWh = 0
        self.CostsinEUR = 0
        self.OfferedPowerinMWH = 0
        self.ReceivedMoneyinEUR = 0
        self.Profit = 0
        # scenario from artificial emlab parameters
        self.Leadtime = 0
        self.Permittime = 0
        self.Lifetime = 0
        self.InvestedCapital = 0
        self.FixedOperatingCost = 0
        self.viableInvestment = True # initially all candidate power plants should be investable
        self.expectedEndOfLife = 0
        self.actualNominalCapacity = 0
        self.capacitytobeInstalled = 0
        self.historicalCvarDummyPlant = 0
        self.electricityOutput = 0
        self.flagOutputChanged = True

    def add_parameter_value(self, reps, parameter_name, parameter_value, alternative):
        if parameter_name == 'Id':
            self.id = parameter_value
        elif parameter_name == 'Technology':
            self.technology = reps.power_generating_technologies[parameter_value]
            self.efficiency = self.technology.efficiency
        elif parameter_name == 'Capacity':
            self.capacitytobeInstalled = int(parameter_value) # the real capacity will be defined once the investment decision is made
        elif parameter_name == 'Owner':
            self.owner = parameter_value

    def add_values_from_df(self, results):
            self.AwardedPowerinMWh = results.PRODUCTION_IN_MWH
            self.CostsinEUR = results.VARIABLE_COSTS_IN_EURO
            self.ReceivedMoneyinEUR = results.REVENUES_IN_EURO

    def get_technology(self, time):
        return self.technology

    def get_Profit(self):
        if not self.Profit:
            Profit = self.ReceivedMoneyinEUR - self.CostsinEUR
        return Profit

    def setInvestedCapital(self):
        pass

    def specifyTemporaryPowerPlant(self, tick, energyProducer, location):
        self.setOwner(energyProducer)
        self.setLocation(location)
        self.setConstructionStartTime()
        self.setActualLeadtime(self.technology.getExpectedLeadtime())
        self.setActualPermittime(self.technology.getExpectedPermittime())
        self.setActualNominalCapacity(self.getCapacity())
        self.setDismantleTime(1000)
        #self.calculateAndSetActualInvestedCapital(tick)
        self.calculateAndSetActualFixedOperatingCosts(tick)
        self.setExpectedEndOfLife(tick + self.getActualPermittime() + self.getActualLeadtime() + self.getTechnology().getExpectedLifetime())
        print("specifyTemporaryPowerPlant tick", tick,  "permit", self.getActualPermittime() ,
              "actuallead" ,self.getActualLeadtime() ,"lifetime",  self.getTechnology().getExpectedLifetime(),
              "setExpectedEndOfLife", self.expectedEndOfLife)
        return self

    def setConstructionStartTime(self):
        self.constructionStartTime = - (self.technology.expected_leadtime +
                                        self.technology.expected_permittime +
                                        round(random() * self.technology.expected_lifetime)) + 2

    # candidate power plants can be invested or not
    def isViableInvestment(self):
        return self.viableInvestment

    def setViableInvestment(self, viableInvestment):
        self.viableInvestment = viableInvestment


class FutureStorageTrader(ImportObject):
    def __init__(self, name):
        super().__init__(name)
        self.AwardedChargePower = 0
        self.AwardedDischargePower = 0
        self.AwardedPower = 0
        self.StoredMWh = 0
        self.Profit = 0
        #self.OfferedChargePrice = None
        #self.OfferedDischargePrice = None
        #self.OfferedPowerinMW

    def add_parameter_value(self, reps, parameter_name, parameter_value, alternative):
        if parameter_name == 'AwardedPowerinMWh':
            self.AwardedPowerinMWh = float(parameter_value)
        elif parameter_name == 'AwardedDischargePower':
            self.AwardedDischargePower = float(parameter_value)
        elif parameter_name == 'AwardedPower':
            self.AwardedPower = float(parameter_value)
        elif parameter_name == 'StoredMWh':
            self.StoredMWh = float(parameter_value)
        elif parameter_name == 'Profit':
            self.Profit = float(parameter_value)



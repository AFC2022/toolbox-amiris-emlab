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
        self.Profit = 0 # operational profits
        # scenario from artificial emlab parameters
        self.Leadtime = 0
        self.Permittime = 0
        self.Lifetime = 0
        self.InvestedCapital = 0
        self.FixedOperatingCost = 0
        self.viableInvestment = True # initially all candidate power plants should be investable
        self.expectedEndOfLife = 0
        self.actualNominalCapacity = 0
        self.capacity = 1 # all power plants are first tested for a capacity of 1
        self.historicalCvarDummyPlant = 0
        self.electricityOutput = 0
        self.flagOutputChanged = True
        self.capacityTobeInstalled = 0

    def add_parameter_value(self, reps, parameter_name, parameter_value, alternative):
        if parameter_name == 'Id':
            self.id = parameter_value
        elif parameter_name == 'Technology':
            self.technology = reps.power_generating_technologies[parameter_value]
            self.efficiency = self.technology.efficiency
        elif reps.realistic_candidate_capacities == True and parameter_name == "Realistic_capacity":
            self.capacityTobeInstalled = int(parameter_value)
            if reps.realistic_candidate_capacities_for_future == True:
                self.capacity = int(parameter_value)
        elif reps.realistic_candidate_capacities == False and parameter_name == 'Capacity':
            self.capacityTobeInstalled = int(parameter_value)
            if reps.realistic_candidate_capacities_for_future == False:
                self.capacity = int(parameter_value)
        elif parameter_name == 'Owner':
            self.owner = parameter_value
        elif parameter_name == 'ViableInvestment':
            self.viableInvestment = bool(parameter_value)

    def setInvestedCapital(self):
        pass

    def specifyTemporaryPowerPlant(self, tick, energyProducer, location):
        self.setOwner(energyProducer)
        self.setLocation(location)
        self.setConstructionStartTime()
        self.setActualLeadtime(self.technology.getExpectedLeadtime())
        self.setActualPermittime(self.technology.getExpectedPermittime())
        self.setActualNominalCapacity(self.getCapacity())
        self.setExpectedEndOfLife(tick + self.getActualPermittime() + self.getActualLeadtime() + self.getTechnology().getExpectedLifetime())
        return self

    def setConstructionStartTime(self):
        self.constructionStartTime = - (self.technology.expected_leadtime +
                                        self.technology.expected_permittime +
                                        round(random() * self.technology.expected_lifetime)) + 2

    # candidate power plants can be invested_in_iteration or not
    def isViableInvestment(self):
        return self.viableInvestment

    def setViableInvestment(self, viableInvestment):
        self.viableInvestment = viableInvestment

    def get_candidate_power_plant_capacity_by_id(self, id):
        return [i.capacity for i in self.candidatePowerPlants.values()
                if i.id == id]

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
        elif parameter_name == 'operationalProfit':
            self.Profit = float(parameter_value)



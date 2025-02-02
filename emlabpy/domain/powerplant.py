"""
This file contains all classes directly related to
PowerPlant
"""
from domain.energyproducer import EnergyProducer
from domain.import_object import *
from random import random
import logging
from domain.actors import EMLabAgent
from domain.loans import Loan
from util import globalNames
import numpy as np

class PowerPlant(EMLabAgent):
    def __init__(self, name):
        super().__init__(name)
        self.name = name
        self.id = 0
        self.technology = None
        self.location = ""
        self.owner = None # change if there are more energyproducers
        self.capacity = 0
        self.efficiency = 0
        # TODO: Implement GetActualEfficiency -> for now the fixed costs are the ones incrementing with the year
        self.banked_allowances = [0 for i in range(100)]
        self.status = globalNames.power_plant_status_not_set  # 'Operational' , 'InPipeline', 'Decommissioned', 'TobeDecommissioned'
        self.fictional_status = globalNames.power_plant_status_not_set
        self.loan = Loan()
        self.loan_payments_in_year = 0
        self.downpayment_in_year = 0
        self.downpayment = Loan()
        self.dismantleTime = 0  # in terms of tick
        self.expectedEndOfLife = 0  # in terms of tick
        # scenario from artificial emlab parameters
        self.constructionStartTime = 0
        self.actualLeadtime = 0
        self.actualPermittime = 0 # todo clear this functionalities
        self.age = 0
        self.commissionedYear = 0
        self.label = ""
        self.actualInvestedCapital = 0
        self.actualFixedOperatingCost = 'NOTSET'
        self.actualEfficiency = 0
        self.actualNominalCapacity = 0
        self.historicalCvarDummyPlant = 0
        self.electricityOutput = 0
        self.flagOutputChanged = True
        # from Amiris results
        self.subsidized = False
        self.AwardedPowerinMWh = 0
        self.CostsinEUR = 0
        self.OfferedPowerinMWH = 0
        self.ReceivedMoneyinEUR = 0
        self.operationalProfit = 0
        self.initialEnergyLevelInMWH = 0
        self.cash = 0

    def add_parameter_value(self, reps, parameter_name, parameter_value, alternative):
        # do not import decommissioned power plants to the repository if it is not the plotting step
        if reps.runningModule != "plotting" and self.name in (
                reps.decommissioned["Decommissioned"]).Decommissioned:
            return
        elif parameter_name == 'Status':
            self.status = str(parameter_value)
        elif parameter_name == 'Efficiency':  # the efficiency stored in the DB is the actual one
            self.actualEfficiency = float(parameter_value)
        elif parameter_name == 'Location':
            self.location = parameter_value
        elif parameter_name == 'Id':
            self.id = int(parameter_value)
        if parameter_name == 'Technology':
            self.technology = reps.power_generating_technologies[parameter_value]
        elif parameter_name == 'Capacity':
            self.capacity = parameter_value
        elif parameter_name == 'Owner':
            self.owner = reps.energy_producers[parameter_value]
        elif parameter_name == 'Age':
            self.age = int(parameter_value) # for emlab data the commissioned year can be read from the age
            if int(self.name) > 1000:
                if self.age >  reps.current_tick:
                    raise Exception("age is higher than it should be " + str(self.id) +" Name " + str(self.name))

            self.commissionedYear = reps.current_year - int(parameter_value)
           #  if int(self.name) > 10000:
           #      a = str(self.id)[0:4]
           #      self.commissionedYear = int(a)
           #  else:
           #      self.commissionedYear = reps.current_year - int(parameter_value)
        elif parameter_name == 'actualFixedOperatingCost':
            self.actualFixedOperatingCost =  float(parameter_value)
        elif parameter_name == 'dismantleTime':
            self.dismantleTime = int(parameter_value)
        elif parameter_name == 'AwardedPowerInMWH':
            self.AwardedPowerinMWh = parameter_value
        elif parameter_name == 'CostsInEUR':
            self.CostsinEUR = float(parameter_value)
        elif parameter_name == 'OfferedPowerInMW':
            self.OfferedPowerinMW = float(parameter_value)
        elif parameter_name == 'ReceivedMoneyInEUR':
            self.ReceivedMoneyinEUR = float(parameter_value)
        elif parameter_name == 'label':
            self.label = parameter_value
        elif parameter_name == 'InitialEnergyLevelInMWH':
            self.initialEnergyLevelInMWH = float(parameter_value)


    def calculate_emission_intensity(self, reps):
        # emission = 0
        # substance_in_fuel_mix_object = reps.get_substances_in_fuel_mix_by_plant(self)
        # for substance_in_fuel_mix in substance_in_fuel_mix_object.substances:
        #     # CO2 Density is a ton CO2 / MWh
        #     co2_density = substance_in_fuel_mix.co2_density * (1 - float(
        #         self.technology.co2_capture_efficiency))
        #
        #     # Returned value is ton CO2 / MWh
        #     emission_for_this_fuel = substance_in_fuel_mix_object.share * co2_density / self.efficiency
        #     emission += emission_for_this_fuel
        # return emission
        if self.technology.fuel != '':
            co2_density = self.technology.fuel.co2_density * (1 - float(
                self.technology.co2_capture_efficiency))
            emission = co2_density / self.technology.efficiency
        else:
            emission = 0
        return emission

    def calculate_fixed_operating_cost(self):
        per_mw = self.technology.get_fixed_operating_cost(self.constructionStartTime +
                                                          int(self.technology.expected_leadtime) +
                                                          int(self.technology.expected_permittime))
        capacity = self.get_actual_nominal_capacity()
        return per_mw * capacity

    def get_Profit(self):
        if not self.operationalProfit:
            self.operationalProfit = self.ReceivedMoneyinEUR - self.CostsinEUR
        return self.operationalProfit

    def get_actual_nominal_capacity(self):
        return self.capacity
        # if self.capacity == 0:
        #     return self.technology.capacity * float(self.location.parameters['CapacityMultiplicationFactor'])
        # else:
        #     return self.capacity

    def calculate_marginal_fuel_cost_per_mw_by_tick(self, reps, time):
        # fc = 0
        # substance_in_fuel_mix_object = reps.get_substances_in_fuel_mix_by_plant(self)
        # for substance_in_fuel_mix in substance_in_fuel_mix_object.substances:
        #     # Fuel price is Euro / MWh
        #     fc += substance_in_fuel_mix_object.share * substance_in_fuel_mix.get_price_for_tick(time) / self.efficiency
        # return fc
        if self.technology.fuel != '':
            xp = [2020, 2050]
            fp = [self.technology.fuel.initialprice2020, self.technology.fuel.initialprice2050]
            newSimulatedPrice = np.interp(reps.current_year, xp, fp)
            fc = newSimulatedPrice / self.technology.efficiency
            # fc = self.technology.fuel.futurePrice.values[0] / self.technology.efficiency
        else:
            fc = 0
        return fc

    def calculate_co2_tax_marginal_cost(self, reps):
        co2_intensity = self.calculate_emission_intensity(reps)
        co2_tax = 0  # TODO: Retrieve CO2 Market Price
        return co2_intensity * co2_tax

    def calculate_marginal_cost_excl_co2_market_cost(self, reps, time):
        mc = 0
        mc += self.calculate_marginal_fuel_cost_per_mw_by_tick(reps, time)
        mc += self.calculate_co2_tax_marginal_cost(reps)
        return mc

    def get_load_factor_for_production(self, production):
        if self.capacity != 0:
            return production / self.capacity
        else:
            return 0

    def add_values_from_df(self, results):
        self.AwardedPowerinMWh = results.PRODUCTION_IN_MWH
        self.CostsinEUR = results.VARIABLE_COSTS_IN_EURO
        self.ReceivedMoneyinEUR = results.REVENUES_IN_EURO
        self.operationalProfit = results.CONTRIBUTION_MARGIN_IN_EURO

    # createPowerPlant from target investment or from investment algorithm chosen power plant
    def specifyPowerPlantforInvest(self, tick, year, energyProducer, location, capacity, pgt):
        self.dischargingEfficiency = 0
        self.setCapacity(capacity)
        self.setTechnology(pgt)
        self.setOwner(energyProducer)
        self.setLocation(location)
        self.setActualLeadtime(self.technology.getExpectedLeadtime())
        self.setActualPermittime(self.technology.getExpectedPermittime())
        self.commissionedYear = year + pgt.getExpectedLeadtime() + pgt.getExpectedPermittime()
        self.age = - pgt.getExpectedLeadtime() - pgt.getExpectedPermittime()
        self.constructionStartTime = tick
        self.calculateAndSetActualEfficiency(self.getConstructionStartTime())
        self.calculateAndSetActualFixedOperatingCosts()
        self.calculateAndSetActualInvestedCapital(self.getConstructionStartTime())
        #self.setDismantleTime(1000) # put very high so that its not considered to be dismantled?
        self.setExpectedEndOfLife(
            tick + self.getTechnology().getExpectedLifetime() - self.age)
        self.status = globalNames.power_plant_status_inPipeline

    def set_loans_installed_pp(self, reps):
        amountPerPayment = reps.determineLoanAnnuities(
            self.getActualInvestedCapital() * self.owner.getDebtRatioOfInvestments(),
            self.getTechnology().getDepreciationTime(), self.owner.getLoanInterestRate())
        # todo : check in emlab
        done_payments = self.age
        startpayments = - self.age
        reps.createLoan(self.owner.name, reps.bigBank.name, amountPerPayment, self.getTechnology().getDepreciationTime(),
                        startpayments , done_payments, self)

    # createPowerPlant from initial database
    def specifyPowerPlantsInstalled(self, tick ):
        self.setActualLeadtime(self.technology.getExpectedLeadtime())
        self.setActualPermittime(self.technology.getExpectedPermittime())
        self.setActualNominalCapacity(self.getCapacity())
        self.setConstructionStartTime()  # minus age, permit and lead time
        self.calculateAndSetActualInvestedCapital(self.getConstructionStartTime())
        if self.actualEfficiency == 0: # if there is not initial efficiency, then assign the efficiency by the technology
           self.calculateAndSetActualEfficiency(self.getConstructionStartTime())
        if self.actualFixedOperatingCost == 'NOTSET': # old power plants have set their fixed costs
            self.calculateAndSetActualFixedOperatingCosts()
        # as a default the expected end of life is assigned by the technology expected lifetime
        self.setExpectedEndOfLife( # set in terms of tick
            tick + self.getTechnology().getExpectedLifetime() - self.age)
        self.setPowerPlantsStatusforInstalledPowerPlants()
        return

    def setPowerPlantsStatusforInstalledPowerPlants(self):
        # todo if the plant is in strategic reserve. Then the status shouldnt change? this is better kept through the list of power plants
        # and self.status != globalNames.power_plant_status_strategic_reserve
        if self.age is not None:
            if self.status == globalNames.power_plant_status_decommissioned:
                pass
            elif self.age >= self.technology.expected_lifetime:
                self.status = globalNames.power_plant_status_to_be_decommissioned
            elif self.age < 0:
                self.status = globalNames.power_plant_status_inPipeline

            else:
                self.status = globalNames.power_plant_status_operational
        else:
            print("power plant dont have an age ", self.name)

    def is_new_installed(self):
        if int(self.name) > 100000:
            return True
        else:
            return False

    def is_invested_by_target_investor(self):
        if len(str(self.id)) == 12:
            return True
        else:
            return False

    # def isOperational(self, currentTick):
    #     finishedConstruction = self.getConstructionStartTime() + self.calculateActualPermittime() + self.calculateActualLeadtime()
    #     if finishedConstruction <= currentTick:
    #         # finished construction
    #         if self.getDismantleTime() == 1000:
    #             # No dismantletime set, therefore must be not yet dismantled.
    #             return True
    #         elif self.getDismantleTime() > currentTick:
    #             # Dismantle time set, but not yet reached
    #             return True
    #         elif self.getDismantleTime() <= currentTick:
    #             # Dismantle time passed so not operational
    #             return False
    #     # Construction not yet finished.
    #     return False

    def isExpectedToBeOperational(self, futuretick, futureyear):
        # if the plants commissioned year is less than the future tick,
        # then passes from in pipeline to operational
        if self.commissionedYear <= futureyear:
            # also plants that are not having a
            if self.getExpectedEndOfLife() > futuretick:
                # Powerplant is not expected to be dismantled
                return True
        else: # plant is expected to be dismantled
            return False

    def calculateActualLeadtime(self):
        actual = None
        actual = self.actualLeadtime
        if actual <= 0:
            actual = self.technology.expected_leadtime
        return actual

    def calculateActualPermittime(self):
        actual = None
        actual = self.actualPermittime
        if actual <= 0:
            actual = self.technology.expected_permittime
        return actual

    def calculateActualLifetime(self):
        actual = None
        actual = self.age
        if actual <= 0:
            actual = self.technology.expected_lifetime
        return actual

    def isWithinTechnicalLifetime(self, currentTick):
        endOfTechnicalLifetime = self.constructionStartTime + \
                                 self.actualPermittime + \
                                 self.actualLeadtime + \
                                 self.age
        if endOfTechnicalLifetime <= currentTick:
            return False
        return True

    def calculateAndSetActualInvestedCapital(self, timeOfPermitorBuildingStart):
        self.setActualInvestedCapital(self.technology.getInvestmentCost(
            timeOfPermitorBuildingStart + self.getActualPermittime() + self.getActualLeadtime()) * self.get_actual_nominal_capacity())

    # the growth trend
    def calculateAndSetActualFixedOperatingCosts(self): # get fixed costs according to age
        self.setActualFixedOperatingCost(self.getTechnology().get_fixed_operating_cost_trend(self.age)\
                                         * self.getActualNominalCapacity())

    def calculateAndSetActualEfficiency(self, timeOfPermitorBuildingStart):
        self.setActualEfficiency(self.getTechnology().getEfficiency(
            timeOfPermitorBuildingStart + self.getActualLeadtime() + self.getActualPermittime()))

    def calculateEmissionIntensity(self):
        emission = 0
        for sub in self.getFuelMix():
            substance = sub.getSubstance()
            fuelAmount = sub.getShare()
            co2density = substance.getCo2Density() * (1 - self.getTechnology().getCo2CaptureEffciency())
            # determine the total cost per MWh production of this plant
            emissionForThisFuel = fuelAmount * co2density
            emission += emissionForThisFuel

        return emission

    def getActualNominalCapacity(self):
        return self.actualNominalCapacity

    def getActualFixedOperatingCost(self):
        return self.actualFixedOperatingCost

    def setActualFixedOperatingCost(self, actualFixedOperatingCost):
        self.actualFixedOperatingCost = actualFixedOperatingCost

    def getIntermittentTechnologyNodeLoadFactor(self):
        return self.reps.findIntermittentTechnologyNodeLoadFactorForNodeAndTechnology(self.getLocation(),
                                                                                      self.getTechnology())

    def getTechnology(self):
        return self.technology

    def setTechnology(self, technology):
        self.technology = technology

    def setLocation(self, location):
        self.location = location

    def getLocation(self):
        return self.location

    def setOwner(self, owner):
        self.owner = owner

    def getCapacity(self):
        return self.capacity

    def setCapacity(self, capacity):
        self.capacity = capacity

    def setConstructionStartTime(self):  # in terms of tick
        self.constructionStartTime = - (self.technology.expected_leadtime +
                                        self.technology.expected_permittime +
                                        self.age)

    def getConstructionStartTime(self):
        return self.constructionStartTime

    def setActualLeadtime(self, actualLeadtime):
        self.actualLeadtime = actualLeadtime

    def getActualLeadtime(self):
        return self.actualLeadtime

    def setActualPermittime(self, actualPermittime):
        self.actualPermittime = actualPermittime

    def getActualPermittime(self):
        return self.actualPermittime

    def setActualEfficiency(self, actualEfficiency):
        self.actualEfficiency = actualEfficiency

    def getActualInvestedCapital(self):
        return self.actualInvestedCapital

    def setActualInvestedCapital(self, actualInvestedCapital):
        self.actualInvestedCapital = actualInvestedCapital

    def dismantlePowerPlant(self, dismantleTime):
        self.dismantleTime = dismantleTime

    def setExpectedEndOfLife(self, expectedEndOfLife):
        self.expectedEndOfLife = expectedEndOfLife

    def getExpectedEndOfLife(self):
        return self.expectedEndOfLife

    def setActualNominalCapacity(self, actualNominalCapacity):
        # self.setActualNominalCapacity(self.getCapacity() * location.getCapacityMultiplicationFactor())
        if actualNominalCapacity < 0:
            raise ValueError("ERROR: " + self.name + " power plant is being set with a negative capacity!")
        self.actualNominalCapacity = actualNominalCapacity

    def getFuelMix(self):
        return self.fuelMix

    def getLoan(self):
        return self.loan

    def setLoan(self, loan):
        self.loan = loan

    def setDownpayment(self, downpayment):
        self.downpayment = downpayment


class Decommissioned(ImportObject):
    def __init__(self, name):
        super().__init__(name)

    def add_parameter_value(self, reps, parameter_name: str, parameter_value, alternative: str):
        if parameter_value == 0.0:
            self.Decommissioned = []
        else:
            setattr(self, parameter_name, parameter_value)

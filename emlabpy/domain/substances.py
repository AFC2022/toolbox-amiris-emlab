from domain.import_object import *
from domain.trends import GeometricTrendRegression
import pandas as pd
import numpy as np
import random

class Substance(ImportObject):
    def __init__(self, name):
        super().__init__(name)
        self.co2_density = 0
        self.energy_density = 1
        self.quality = 0
        self.price = 0
        self.trend = None
        self.all_years_price = dict()
        self.initialprice2020 = 0
        self.initialprice2050 = 0
        self.futurePrice = []
        self.futurePrice_inYear = 0
        self.simulatedPrice = []
        self.simulatedPrice_inYear = 0
        self.resource_limit2020 = 0
        self.values = []
        self.geometricRegression = None
        self.newSimulatedPrice = 0
        self.newFuturePrice = 0

    def add_parameter_value(self, reps, parameter_name, parameter_value, alternative):
        if parameter_name == 'AmirisFuelSpecificCo2EmissionsInTperMWH': # todo: AMIRIS add this as an input parameter 'co2Density'
            self.co2_density = float(parameter_value)
        elif parameter_name == 'energyDensity':
            self.energy_density = float(parameter_value)
        elif parameter_name == 'quality':
            self.quality = float(parameter_value)
        elif parameter_name == 'price2020': # TODO take out the hardcoded price
            self.initialprice2020 = float(parameter_value)
        elif parameter_name == 'price2050':
            if reps.fix_prices_to_2020 == True: # for verification runs. If its indicated fuel prices, CO2 prices and electricity demand is fix to 2020
                self.initialprice2050 = self.initialprice2020
            else:
                self.initialprice2050 = float(parameter_value)
        elif parameter_name == 'annual_resource_limit' and alternative == "biopotential_2020":# TODO take out the hardcoded scenario
            self.resource_limit2020 = float(parameter_value)
        elif parameter_name == 'trend':
            self.trend = reps.trends[parameter_value]
        elif parameter_name == 'futurePrice':
            self.futurePrice = parameter_value
        elif parameter_name == 'simulatedPrice':
            self.simulatedPrice = parameter_value
        else: #
            if alternative == reps.country:
                year = int(parameter_name)
                self.all_years_price[year] = float(parameter_value)

    def get_price_for_next_tick(self, reps, tick, year, substance):
        if reps.fix_prices_to_2030 == True: # attention this shouldnt be neede once all data is there
            if  substance.name == "CO2":
                self.newSimulatedPrice = self.all_years_price[reps.fix_price_year]
                return self.newSimulatedPrice
            else:
                xp = [2020, 2050]
                fp = [substance.initialprice2020, substance.initialprice2050]
                self.newSimulatedPrice = np.interp(reps.fix_price_year, xp, fp)
                return self.newSimulatedPrice

        elif  substance.name == "CO2" and reps.country == "NL":
            self.newSimulatedPrice = self.all_years_price[year]
            return self.newSimulatedPrice

        elif tick < reps.start_year_fuel_trends:
            # electricity is also considered as a fuel. Input
            xp = [2020, 2050]
            fp = [substance.initialprice2020, substance.initialprice2050]
            self.newSimulatedPrice = np.interp(year, xp, fp)
            return self.newSimulatedPrice
        else:
            calculatedPrices = reps.dbrw.get_calculated_simulated_fuel_prices(substance.name, "simulatedPrice")
            df = pd.DataFrame(calculatedPrices['data'])
            df.set_index(0, inplace=True)
            last_value = df.loc[str(year - 1)][1]
            random_number = random.triangular(self.trend.min, self.trend.max,  self.trend.top) # low, high, mode
            self.newSimulatedPrice = last_value * random_number
        return self.newSimulatedPrice

    def get_price_for_future_tick(self, reps, futureYear, substance):
        if reps.fix_prices_to_2030 == True: # attention this shouldnt be neede once all data is there
            if  substance.name == "CO2":
                self.newFuturePrice = self.all_years_price[reps.fix_price_year]
                return self.newFuturePrice
            else:
                xp = [2020, 2050]
                fp = [substance.initialprice2020, substance.initialprice2050]
                self.newFuturePrice = np.interp(reps.fix_price_year, xp, fp)
                return self.newFuturePrice

        elif substance.name == "CO2" and reps.country == "NL":
            self.newFuturePrice = self.all_years_price[futureYear]
            return self.newFuturePrice

        elif substance.name == "CO2":
            xp = [2020, 2050]
            fp = [substance.initialprice2020, substance.initialprice2050]
            self.newFuturePrice = np.interp(futureYear, xp, fp)
            return self.newFuturePrice

        elif reps.current_tick >= reps.start_year_fuel_trends:
            self.initializeGeometricTrendRegression(reps, substance)
            self.newFuturePrice = self.geometricRegression.predict(futureYear)
            return self.newFuturePrice

        else:
            xp = [2020, 2050]
            fp = [substance.initialprice2020, substance.initialprice2050]
            self.newFuturePrice = np.interp(futureYear, xp, fp)
            return self.newFuturePrice

    def initializeGeometricTrendRegression(self, reps, substance):
        self.geometricRegression = GeometricTrendRegression("geometrictrendRegression" + self.name)
        calculatedfuturePrices =  reps.dbrw.get_calculated_simulated_fuel_prices(substance.name, "futurePrice")
        x = []
        y = []
        for i in calculatedfuturePrices['data']:
            x.append(int(i[0]))
            y.append(i[1])
        self.geometricRegression.addData(x,y)


class SubstanceInFuelMix(ImportObject):
    def __init__(self, name: str):
        super().__init__(name)
        self.substance = None
        self.substances = list()
        self.share = 1

    def add_parameter_value(self, reps, parameter_name: str, parameter_value, alternative: str):
        if parameter_name == 'FUELNEW':
            self.substances.append(reps.substances[parameter_value])

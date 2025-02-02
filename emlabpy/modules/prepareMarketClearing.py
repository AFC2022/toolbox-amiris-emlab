from modules.defaultmodule import DefaultModule
import pandas as pd
from datetime import datetime, timedelta
from util import globalNames
import os

class PrepareMarket(DefaultModule):
    """
    This function prepares the information for next years market clearing:
    -fuel prices and demand. the demand is as the node "electricity".
    The fuel prices are stochastically simulated with a triangular trend

    """

    def __init__(self, reps):
        super().__init__("Next year prices", reps)
        self.tick = 0
        self.simulation_year = 0
        self.empty = None
        self.Years = []
        self.writer = None
        self.path = globalNames.amiris_data_path
        self.power_plants_list = []
        reps.dbrw.stage_init_bids_structure()
        reps.dbrw.stage_init_next_prices_structure()

    def act(self):
        # look for all power plants, except for decommissioned and in pipeline
        self.power_plants_list =  self.reps.get_power_plants_by_status([globalNames.power_plant_status_operational,
                                                                        globalNames.power_plant_status_to_be_decommissioned,
                                                                        globalNames.power_plant_status_strategic_reserve,
                                                                        ])
        self.sort_power_plants_by_age()
        self.setTimeHorizon()
        self.setExpectations()
        self.openwriter()
        self.write_conventionals()
        self.write_renewables()
        self.write_storage()
        self.write_biogas()
        self.write_scenario_data_emlab("next_year_price")
        self.write_times()
        self.writer.save()
        self.writer.close()
        print("saved to ", self.path)

    def sort_power_plants_by_age(self):
        ##print(self.power_plants_list[0].age)
        self.power_plants_list.sort(key=lambda x:x.age)
        ##print(self.power_plants_list[0].age)

    def setTimeHorizon(self):
        self.tick = self.reps.current_tick
        self.simulation_year = self.reps.current_year
        #self.Years = (list(range(self.reps.start_simulation_year, self.simulation_year + 1, 1)))
        self.Years =  [self.simulation_year]

    def setExpectations(self):
        for k, substance in self.reps.substances.items():
            fuel_price = substance.get_price_for_next_tick(self.reps, self.tick, self.simulation_year, substance)
            substance.simulatedPrice_inYear = fuel_price
            self.reps.dbrw.stage_simulated_fuel_prices(self.simulation_year, fuel_price, substance)

    def write_times(self):
        startime = datetime(self.simulation_year, 1, 1) - timedelta(minutes=2)
        stoptime = datetime(self.simulation_year, 12, 31) - timedelta(minutes=2)
        d = {'StartTime': startime, 'StopTime': stoptime}
        df = pd.DataFrame.from_dict(d, orient='index')
        df.to_excel(self.writer, sheet_name="times")

    def write_scenario_data_emlab(self, calculatedprices):
        Co2Prices = []
        FuelPrice_NUCLEAR = []
        FuelPrice_LIGNITE = []
        FuelPrice_HARD_COAL = []
        FuelPrice_NATURAL_GAS = []
        FuelPrice_OIL = []

        #demand = ["./timeseries/demand/load.csv"] * len(self.Years)
        wholesale_market = self.reps.get_electricity_spot_market_for_country(self.reps.country)
        demand = wholesale_market.hourlyDemand
        write_demand = ["./amiris_workflow/amiris-config/data/load.csv"]
        demand_file_for_amiris = globalNames.load_file_for_amiris

        for k, substance in self.reps.substances.items():
            if calculatedprices == "next_year_price":
                fuel_price = substance.simulatedPrice_inYear
            else:
                fuel_price = substance.futurePrice_inYear
            if substance.name == "nuclear":
                FuelPrice_NUCLEAR.append(fuel_price)
            elif substance.name == "lignite":
                FuelPrice_LIGNITE.append(fuel_price)
            elif substance.name == "hard_coal":
                FuelPrice_HARD_COAL.append(fuel_price)
            elif substance.name == "natural_gas":
                FuelPrice_NATURAL_GAS.append(fuel_price)
            elif substance.name == "light_oil":
                FuelPrice_OIL.append(fuel_price)
            elif substance.name == "CO2":
                Co2Prices.append(fuel_price)
            elif substance.name == "electricity":
                if self.reps.country == "DE": # for germany the load is calculated with a trend.
                    new_demand = demand.copy()
                    new_demand[1] = new_demand[1].apply(lambda x: x * fuel_price)
                    new_demand.to_csv(demand_file_for_amiris, header=False, sep=';', index=False)
                else: # for now, only have dynamic data for NL case
                    if self.reps.runningModule == "run_prepare_next_year_market_clearing":
                        # the load was already updated in the clock step
                        pass
                    elif self.reps.runningModule == "run_future_market":
                        wholesale_market.future_demand.to_csv(demand_file_for_amiris, header=False, sep=';', index=False)
                        # the write_demand_path continue being the same, as this is overwritten.


        d = {'Co2Prices': Co2Prices,
             'FuelPrice_NUCLEAR': FuelPrice_NUCLEAR, 'FuelPrice_LIGNITE': FuelPrice_LIGNITE,
             'FuelPrice_HARD_COAL': FuelPrice_HARD_COAL, 'FuelPrice_NATURAL_GAS': FuelPrice_NATURAL_GAS,
             'FuelPrice_OIL': FuelPrice_OIL,
             'DemandSeries': write_demand}

        df = pd.DataFrame.from_dict(d, orient='index',  columns=self.Years)
        df.to_excel(self.writer, sheet_name="scenario_data_emlab")

    def write_conventionals(self):
        identifier = []
        FuelType = []
        OpexVarInEURperMWH = []
        Efficiency = []
        BlockSizeInMW = []
        InstalledPowerInMW = []
        operator = self.reps.get_strategic_reserve_operator(self.reps.country)

        for pp in self.power_plants_list:
            if pp.technology.type == "ConventionalPlantOperator":
                identifier.append(pp.id)
                FuelType.append(self.reps.dictionaryFuelNames[pp.technology.fuel.name])
                if pp.name in operator.list_of_plants:
                    OpexVarInEURperMWH.append(operator.reservePriceSR)
                else:
                    OpexVarInEURperMWH.append(pp.technology.variable_operating_costs)
                Efficiency.append(pp.technology.efficiency)
                BlockSizeInMW.append(pp.capacity)
                InstalledPowerInMW.append(pp.capacity)

        d = {'identifier': identifier, 'FuelType': FuelType, 'OpexVarInEURperMWH': OpexVarInEURperMWH,
             'Efficiency': Efficiency, 'BlockSizeInMW': BlockSizeInMW,
             'InstalledPowerInMW': InstalledPowerInMW}

        df = pd.DataFrame(data=d)
        df.to_excel(self.writer, sheet_name="conventionals")

    def write_renewables(self):
        identifier = []
        InstalledPowerInMW = []
        OpexVarInEURperMWH = []
        Set = []
        SupportInstrument = []
        FIT = []
        Premium = []
        Lcoe = []
        operator = self.reps.get_strategic_reserve_operator(self.reps.country)

        for pp in self.power_plants_list:
            if pp.technology.type == "VariableRenewableOperator" and self.reps.dictionaryTechSet[
                pp.technology.name] != "Biogas":
                identifier.append(pp.id)
                InstalledPowerInMW.append(pp.capacity)
                # todo: make exception for forward Capacity market.
                if pp.name in operator.list_of_plants:
                    OpexVarInEURperMWH.append(operator.reservePriceSR)
                else:
                    OpexVarInEURperMWH.append(pp.technology.variable_operating_costs)
                Set.append(self.reps.dictionaryTechSet[pp.technology.name])
                SupportInstrument.append("-")
                FIT.append("-")
                Premium.append("-")
                Lcoe.append("-")

        d = {'identifier': identifier, 'InstalledPowerInMW': InstalledPowerInMW,
             'OpexVarInEURperMWH': OpexVarInEURperMWH,
             'Set': Set, 'SupportInstrument': SupportInstrument, 'FIT': FIT, 'Premium': Premium, 'Lcoe': Lcoe}

        df = pd.DataFrame(data=d)
        df.to_excel(self.writer, sheet_name="renewables")

    def write_biogas(self):
        identifier = []
        InstalledPowerInMW = []
        OpexVarInEURperMWH = []
        Set = []
        SupportInstrument = []
        FIT = []
        Premium = []
        Lcoe = []
        operator = self.reps.get_strategic_reserve_operator(self.reps.country)

        for pp in self.power_plants_list:
            if pp.technology.type == "VariableRenewableOperator" and self.reps.dictionaryTechSet[
                pp.technology.name] == "Biogas":
                identifier.append(pp.id)
                InstalledPowerInMW.append(pp.capacity)
                if pp.name in operator.list_of_plants:
                    OpexVarInEURperMWH.append(operator.reservePriceSR)
                else:
                    OpexVarInEURperMWH.append(pp.technology.variable_operating_costs)
                Set.append(self.reps.dictionaryTechSet[pp.technology.name])
                SupportInstrument.append("-")
                FIT.append("-")
                Premium.append("-")
                Lcoe.append("-")

        d = {'identifier': identifier, 'InstalledPowerInMW': InstalledPowerInMW,
             'OpexVarInEURperMWH': OpexVarInEURperMWH,
             'Set': Set, 'SupportInstrument': SupportInstrument, 'FIT': FIT, 'Premium': Premium, 'Lcoe': Lcoe}

        df = pd.DataFrame(data=d)
        df.to_excel(self.writer, sheet_name="biogas")

    def write_storage(self):
        identifier = []
        EnergyToPowerRatio = []
        ChargingEfficiency = []
        DischargingEfficiency = []
        InitialEnergyLevelInMWH = []
        InstalledPowerInMW = []
        StorageType = []
        for pp in self.power_plants_list:
            if pp.technology.type == "StorageTrader":
                identifier.append(pp.id)
                ChargingEfficiency.append(pp.technology.chargingEfficiency)
                DischargingEfficiency.append(pp.technology.dischargingEfficiency)
                InitialEnergyLevelInMWH.append(pp.initialEnergyLevelInMWH)
                EnergyToPowerRatio.append(pp.technology.energyToPowerRatio)
                InstalledPowerInMW.append(pp.capacity)
                StorageType.append("STORAGE")

        d = {'identifier': identifier, 'StorageType': StorageType, 'EnergyToPowerRatio': EnergyToPowerRatio,
             'ChargingEfficiency': ChargingEfficiency,
             'DischargingEfficiency': DischargingEfficiency, 'InitialEnergyLevelInMWH': InitialEnergyLevelInMWH,
             'InstalledPowerInMW': InstalledPowerInMW, }
        # @DLR: missing SelfDischargeRatePerHour in excel

        df = pd.DataFrame(data=d)
        print(self.path)
        df.to_excel(self.writer, sheet_name="storages")

    def openwriter(self):
        self.writer = pd.ExcelWriter(self.path, mode="a", engine='openpyxl', if_sheet_exists='replace')

import numpy_financial as npf
import pandas as pd
from domain.powerplantDispatchPlan import PowerPlantDispatchPlan
from modules.defaultmodule import DefaultModule
from domain.financialReports import FinancialPowerPlantReport

from util import globalNames


class CreatingFinancialReports(DefaultModule):

    def __init__(self, reps):
        super().__init__("Creating Financial Reports", reps)
        self.agent = reps.energy_producers[reps.agent]
        if reps.current_tick == 0:
            reps.dbrw.stage_init_financial_results_structure()
            reps.dbrw.stage_init_cash_agent()

    def act(self):
        # TODO WHY findAllPowerPlantsWhichAreNotDismantledBeforeTick(self.reps.current_tick - 2)
        self.createFinancialReportsForPowerPlantsAndTick()
        self.addingMarketClearingIncome()
        print("finished financial report")

    def createFinancialReportsForPowerPlantsAndTick(self):
        financialPowerPlantReports = []
        for powerplant in self.reps.get_power_plants_by_status([globalNames.power_plant_status_operational,
                                                                globalNames.power_plant_status_to_be_decommissioned,
                                                                globalNames.power_plant_status_strategic_reserve,
                                                                ]):

            financialPowerPlantReport = self.reps.get_financial_report_for_plant(powerplant.name)

            if financialPowerPlantReport is None:
                # PowerPlantDispatchPlan not found, so create a new one
                financialPowerPlantReport = FinancialPowerPlantReport(powerplant.name)

            dispatch = self.reps.get_power_plant_electricity_dispatch(powerplant.id)
            if dispatch == None:
                dispatch = PowerPlantDispatchPlan(powerplant.id)
                dispatch.variable_costs = 0
                dispatch.accepted_amount = 0
                dispatch.revenues = 0

            fixed_on_m_cost = powerplant.getActualFixedOperatingCost()
            financialPowerPlantReport.setTime(self.reps.current_tick)
            financialPowerPlantReport.setPowerPlant(powerplant.name)  # this can be ignored, its already in the name
            financialPowerPlantReport.setPowerPlantStatus(powerplant.status)
            financialPowerPlantReport.setFixedCosts(fixed_on_m_cost) # saved as fixedCosts

            self.agent.CF_FIXEDOMCOST -= fixed_on_m_cost

            loans = powerplant.loan_payments_in_year + powerplant.downpayment_in_year
            # # attention: this is only to check
            # if powerplant.downpayment_in_year> 0:
            #     print("downpayment is paid during construction. why is it paid here")
            yearly_costs = - dispatch.variable_costs - fixed_on_m_cost  # without loans

            financialPowerPlantReport.setVariableCosts(dispatch.variable_costs) # saved as variableCosts
            self.agent.CF_COMMODITY -= dispatch.variable_costs


            financialPowerPlantReport.totalCosts =  yearly_costs # saved as totalCosts
            financialPowerPlantReport.setProduction(dispatch.accepted_amount)

            financialPowerPlantReport.setSpotMarketRevenue(dispatch.revenues)
            self.agent.CF_ELECTRICITY_SPOT += dispatch.revenues

            financialPowerPlantReport.setOverallRevenue( # saved as overallRevenue
                financialPowerPlantReport.capacityMarketRevenues_in_year +  dispatch.revenues)

            self.agent.CF_CAPMARKETPAYMENT += financialPowerPlantReport.capacityMarketRevenues_in_year
            # total profits are used to decide for decommissioning saved as totalProfits
            operational_profit = financialPowerPlantReport.capacityMarketRevenues_in_year + dispatch.revenues +  yearly_costs
            financialPowerPlantReport.totalProfits= operational_profit

            # total profits with loans are to calculate RES support. saved as totalProfitswLoans
            operational_profit_with_loans = operational_profit - loans
            financialPowerPlantReport.totalProfitswLoans = operational_profit_with_loans

            irr, npv = self.getProjectIRR(powerplant, operational_profit ,loans, self.agent)
            financialPowerPlantReport.irr = irr
            financialPowerPlantReport.npv = npv
            financialPowerPlantReports.append(financialPowerPlantReport)
        self.reps.dbrw.stage_financial_results(financialPowerPlantReports)
        self.reps.dbrw.stage_cash_agent(self.agent, self.reps.current_tick)


    def getProjectIRR(self, pp, operational_profit_withFixedCosts ,loans , agent):
        totalInvestment = pp.getActualInvestedCapital()
        depreciationTime = pp.technology.depreciation_time
        buildingTime = pp.technology.expected_leadtime
        # get average profits per technology
        equity = (1 -agent.debtRatioOfInvestments)
        equalTotalDownPaymentInstallment = (totalInvestment * equity) / buildingTime
        # the rest payment was considered in the loans
        debt= totalInvestment * (agent.debtRatioOfInvestments)
        restPayment =debt / depreciationTime

        # operational_profit considers already fixed costs
        wacc = (1 - self.agent.debtRatioOfInvestments) * self.agent.equityInterestRate + self.agent.debtRatioOfInvestments * self.agent.loanInterestRate
        investmentCashFlow = [0 for i in range(depreciationTime + buildingTime)]

        # print("total investment cost in MIll", totalInvestment / 1000000)
        if self.reps.npv_with_annuity == True:
            for i in range(0, buildingTime):
                investmentCashFlow[i] = - equalTotalDownPaymentInstallment
            for i in range(buildingTime, depreciationTime + buildingTime):
                investmentCashFlow[i] = operational_profit_withFixedCosts - loans
        else:
            for i in range(0, buildingTime):
                investmentCashFlow[i] = - equalTotalDownPaymentInstallment
            for i in range(buildingTime, depreciationTime + buildingTime):
                investmentCashFlow[i] = operational_profit_withFixedCosts  - restPayment

        npv = npf.npv(wacc, investmentCashFlow)

        investmentCashFlow_with_loans = [0 for i in range(depreciationTime + buildingTime)]
        for i in range(0, buildingTime):
            investmentCashFlow_with_loans[i] = - equalTotalDownPaymentInstallment
        for i in range(buildingTime, depreciationTime + buildingTime):
            investmentCashFlow_with_loans[i] = operational_profit_withFixedCosts - loans

        IRR = npf.irr(investmentCashFlow_with_loans)
        if pd.isna(IRR):
            return -100, npv
        else:
            return round(IRR, 4), npv

    def addingMarketClearingIncome(self):
        print("adding again dispatch revenues????")
        all_dispatch = self.reps.power_plant_dispatch_plans_in_year
        SRO = self.reps.get_strategic_reserve_operator(self.reps.country)
        all_revenues = 0
        for k, dispatch in all_dispatch.items():
            if k not in SRO.list_of_plants:
                all_revenues += dispatch.revenues
                self.agent.CF_ELECTRICITY_SPOT += dispatch.revenues

        # adding market revenues to energy producer
        # wholesale_market = self.reps.get_electricity_spot_market_for_country(self.reps.country)
        # self.reps.createCashFlow(wholesale_market, self.agent, all_revenues,
        #                          globalNames.CF_ELECTRICITY_SPOT, self.reps.current_tick, "all")

            # TODO add CO2 costs
            # financialPowerPlantReport.setVariableCosts(financialPowerPlantReport.getCommodityCosts() + financialPowerPlantReport.getCo2Costs())
            # financialPowerPlantReport.setOverallRevenue(financialPowerPlantReport.getCapacityMarketRevenue() + financialPowerPlantReport.getCo2HedgingRevenue() + financialPowerPlantReport.getSpotMarketRevenue() + financialPowerPlantReport.getStrategicReserveRevenue())

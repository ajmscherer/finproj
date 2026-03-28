# finproj - Stochastic Financial Projections to optimize asset management
# Copyright (C) 2025-2026 Alex Scherer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


from inv_proj import rc, Risk, Projection, StatisticalObserver, ps, AuditObserver, CSV_Observer

# ---------------------------------------------------------------------------------------
#
#            Portfolfio size and liquidity assumptions
#
# ---------------------------------------------------------------------------------------

CAPITAL = '1M'
WITHDRAWALS = '40k'
CASH_BUFFER= '100k'
MAXYEAR=15
NB_PROJECTIONS = 1000


# ---------------------------------------------------------------------------------------
#
#            Portfolfio Mix assumptions
#
# ---------------------------------------------------------------------------------------

risk_mix = {
    'safe': {rc.BOND:80, rc.EQUITY:20 , rc.PMETAL:1, rc.CRYPTO:0, rc.REAL_ESTATE:0},
    'moderate': {rc.BOND:45, rc.EQUITY:45,rc.PMETAL:8, rc.CRYPTO:2, rc.REAL_ESTATE:0},
    'performance': {rc.BOND:30, rc.EQUITY:40,rc.PMETAL:5, rc.CRYPTO:5, rc.REAL_ESTATE:20},
}


# ---------------------------------------------------------------------------------------
#
#            Financial performance assumptions (based on Grok prompted on 12/29/2025)
#
# ---------------------------------------------------------------------------------------

risk_param = {
    rc.MONEY_MARKET: [{'from_year':1, 'rv':'norm', 'mu':0.5, 'sigma': 4.0}],
    rc.BOND: [{'from_year':1, 'rv':'norm', 'mu':2.0, 'sigma': 10.0},],
    rc.EQUITY:[{'from_year':1, 'rv':'norm', 'mu':6.5, 'sigma': 20.0},],
    rc.CRYPTO:[{'from_year':1, 'rv':'norm', 'mu':50.0, 'sigma':100.0},],
    rc.PMETAL:[{'from_year':1, 'rv':'norm', 'mu':1.0, 'sigma':18},],
    rc.REAL_ESTATE:[{'from_year':1, 'rv':'norm', 'mu':3.0, 'sigma':15.0},],
}


# ---------------------------------------------------------------------------------------
#
#            Create observers to collect data when simulation is ran
#
# ---------------------------------------------------------------------------------------

def define_observers(simulation):
    # NAV observer at each EOP
    nav = {}
    for year in [1, 5, MAXYEAR]:
        navObserver = StatisticalObserver(
                    quantity=lambda projection, **param:projection.ptf_eop.total_value(), 
                    condition=lambda projection, step, y=year,**params:(projection.period==y) & (step==ps.EOP))
        nav[f'Net Asset Value @ year {year:>2}'] = navObserver
        simulation.registerObserver(navObserver)

    # audit observer
    auditObserver = AuditObserver(out=open('output.txt', mode="w"))
    simulation.registerObserver(auditObserver)

    # csv file observer
    csv = CSV_Observer('output.csv')
    simulation.registerObserver(csv)

    return nav


# ---------------------------------------------------------------------------------------
#
#            Main procedure to run investment projection simulation
#
# ---------------------------------------------------------------------------------------

def run():
    '''Main procedure to run investment projection simulation'''

    # create risk distribution
    distributions = Risk.buildRisks(risk_param, max_year=MAXYEAR)

    # create simulation
    simulation = Projection(
            initial_capital=CAPITAL, 
            withdrawals=WITHDRAWALS,
            cashBuffer=CASH_BUFFER,
            risk_mix=risk_mix['performance'],
            risk_distrib=distributions,
            nb_years=MAXYEAR,
            nb_projections=NB_PROJECTIONS)
    
    # create observers
    nav = define_observers(simulation)

    # run simulation
    for i in range(NB_PROJECTIONS):
        simulation.run(i+1)

    # print moment of wealthObserver   
    for period in nav:
        print(f"{period:<20}: {nav[period]}")


run() 
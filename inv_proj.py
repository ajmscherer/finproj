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

from enum import Enum
from abc import abstractmethod, ABC
import random
import re
import math
import sys


class rc(Enum):
    '''Risk class'''
    INFLATION = 'inflation'
    MONEY_MARKET = 'liquidity(liquidités[fr])'
    BOND = 'bond(obligataire[fr])'
    EQUITY = 'equity(actions[fr])'
    CRYPTO = 'crypto currencies(crypto monnaies[fr])'
    PMETAL = 'precious metal(métaux précieux[fr])'
    REAL_ESTATE = 'real_estate(immobilier[fr])'


    @staticmethod
    def getDescription_o(risk_class, langage='en'):
        '''return a description of risk_class'''

        def build_translation():

            nst = risk_class.value
            trs = {}
            
            # init translations
            
            p1 = re.compile(r"(.*)\((.*)\)")
            m1 = p1.match(nst)

            if m1:
                default_name, translations = m1.groups()
                trs[''] = default_name

                p2 = re.compile(r"(.*)\[(.*)\]")
                for translation_info in translations.split(","):
                    m2=p2.match(translation_info)
                    if m2:
                        translation, language = m2.groups()
                        trs[language] = translation

            else:
                trs[''] = nst

            rc.risk_names[risk_class] = trs


        if risk_class not in rc.risk_names:
            build_translation()

        trs = rc.risk_names[risk_class]
        
        result = trs[langage] if langage in trs else trs['']
            
        return result

    def getDescription(self, language='en'):

        return rc.getDescription_o(self, language)

rc.risk_names = {}


''' 

Helper functions

'''

def cv(value_str):
    """
    Converts a string to a float, handling thousand comma separators
    and 'k', 'm', 'b' suffixes for thousands, millions, and billions.
    Also handles percentage strings.

    Args:
        value_str (str): The input string to convert.

    Returns:
        float: The converted float value.

    Raises:
        ValueError: If the string cannot be converted to a float.
    """

    if isinstance(value_str, (int, float)):
        return float(value_str)
    elif not isinstance(value_str, str):
        raise ValueError("Input must be a string.")

    s = value_str.replace(',', '').strip().lower()

    multiplier = 1.0

    if s.endswith('%'):
        s = s[:-1]
        try:
            return float(s) / 100
        except ValueError:
            raise ValueError(f"Could not convert '{value_str}' to a float.")

    if s.endswith('k'):
        multiplier = 1e3
        s = s[:-1]
    elif s.endswith('m'):
        multiplier = 1e6
        s = s[:-1]
    elif s.endswith('b'):
        multiplier = 1e9
        s = s[:-1]

    try:
        return float(s) * multiplier
    except ValueError:
        raise ValueError(f"Could not convert '{value_str}' to a float.")

def header(text, pattern="-", width = 80):
    text = f" {text} "
    left = (width - len(text)) // 2
    right = width - left - len(text)
    return pattern * left + text + pattern * right


"""
Random variables
"""

class RV(ABC):

    @abstractmethod
    def draw():
        pass

class Norm(RV):
    '''Normal distribition'''

    def __init__(self, mu =0.0, sigma =1.0):
        self.mu = mu
        self.sigma = sigma

        self.rn = random.Random()

    def draw(self):
        return self.rn.gauss(mu=self.mu, sigma=self.sigma)

"""
Risks
"""

class Risk:

    def __init__(self, name, rc,  quantifications, max_year):
        self.name = name
        self.rc = rc

        # init distribution
        self.distribution=init_distrib(quantifications, max_year=max_year)

        
    @staticmethod
    def buildRisks(risk_param, max_year):
        '''
        Static method to create a set of risks
        
        :param risk_param: assumptions for risk distribution
        :param max_year: the number of years to project
        '''
        result = {}
        for rc in risk_param:
            result[rc] = Risk(name=rc.name, rc=rc, quantifications=risk_param[rc], max_year=max_year)
        return result
    
def init_distrib(distrib_info_list, max_year):
    result={}
    y2 = max_year+1
    for distrib_info in distrib_info_list[::-1]:
        rvn = distrib_info['rv']
        if rvn == 'norm':
            rv = Norm(mu=distrib_info['mu'], sigma=distrib_info['sigma'])
        else:
            raise Exception(f"Unknown random variable class '{rvn}'")
        y1 = distrib_info['from_year']
        items ={y:rv for y in range(y1,y2)}
        y2=y1
        result.update(items)

    return result


class Portfolio:

    def __init__(self, lines):
        self.lines = lines

    @staticmethod
    def create(amount, composition):
        lines = {key:value*amount for key, value in composition.items()}
        return Portfolio(lines)

    @staticmethod
    def create_100pct_cash(amount):
        return Portfolio.create(amount=amount, composition={rc.MONEY_MARKET:1.0})

    @staticmethod
    def create_non_cash(amount, risk_mix):
        '''
        Docstring for create_non_cash
        
        :param capital: portfolio amount
        :param risk_mix: Description
        '''

        # get the key of the first risk 
        k=list(risk_mix.keys())[0]

        # create non cash with all capital on the first risk
        p = Portfolio.create(amount=amount,composition={k:1})

        # rebalance across all rosks
        p. rebalance(targetMix=risk_mix)

        return p

    def dup(self):
        return Portfolio(self.lines.copy())

    def __add__(self, otherPortfolio):
        '''
        operator + overriden to allow the addition of two portfolios.
        
        :param self: Description
        :param otherPortfolio: Description
        '''
        lines1, lines2 = self.lines, otherPortfolio.lines    
        keys1 = list(lines1.keys())
        keys2 = list(lines2.keys())
        keys = set(keys1+keys2)
        s = {}
        for key in keys:
            t=lines1[key] if key in lines1 else 0.0
            if key in lines2:
                t+=lines2[key]
            s[key]=t

        return Portfolio.create(amount=1.0, composition=s)
        

    def applyReturns(self, returns={}):
        for risk_class in returns:
            if risk_class in self.lines:
                self.lines[risk_class] *= 1 + returns[risk_class]

    def growByPeriodMovement(self, movements={}):
        for risk_class in movements:
            if risk_class in self.lines:
                self.lines[risk_class] += movements[risk_class]

    def rebalance(self, targetMix={}):
        v = self.value(targetMix.keys())
        total_weight = sum(targetMix.values())
        for risk_class in targetMix:
            self.lines[risk_class] = v * targetMix[risk_class] / total_weight


    def value(self, lines={}):
        v = 0.0
        for line in lines:
            if line in self.lines:
                v+= self.lines[line]
        return v
    
    def total_value(self):
        lines = self.lines.keys()
        return self.value(lines)
    
    def getComposition(self):
        tv = self.total_value()
        result = {}
        for risk_class in self.lines:
            rcv = self.lines[risk_class]
            result[risk_class] = (f"{rcv:,.0f}", f"{rcv/tv:,.1%}")
        return result
    
    def getCompoStr(self):
        result = ''
        fs = r"{:<15} {:>20} ({:>6})"
        for k,v in self.getComposition().items():
            result+= f"{fs.format(k.name, v[0],v[1])}\n"
        result += "-"*len(fs.format('',"","100.0%")) + '\n'
        result += fs.format("total",f"{self.total_value():,.0f}", "100.0%") + "\n"
        return result

class Observer(ABC):
    '''An abstract class that observe things when its process method is invoked'''

    @abstractmethod
    def processNotification(self, observed, **params):
        '''Method that get info and do something with it'''

class Observable:

    def __init__(self):
        self.observers=[]

    def registerObserver(self, observer:Observer):
        self.observers.append(observer)

    def notifyObservers(self, **params):
        for observer in self.observers:
            observer.processNotification(self, **params)


class ps(Enum):
    START = 'Beginning of Simulation'
    BOP = 'Beginning of Period'
    EOP = 'End of Period'
    WRAPUP = 'End of Simulation'



class Projection(Observable):
    '''
    A class that projects a P&L over multiple years using specified assumptions
    '''
    
    def __init__(self, initial_capital, withdrawals, cashBuffer, risk_mix, risk_distrib, nb_years, nb_projections):
        '''
        arguments:
            capital:        the initial amount of capital
            withdrawals:    the amount of money spent in each period
            cashBuffer:     the target amount of cash that needs to be held when possible
            risk_mix:       the allocation of capital by risk class
            risk_distrib:   the risk distributions
            nb_years:       the number of years to run
            nb_projections: the number of projections to run

        '''

        super().__init__()
        self.initial_capital = cv(initial_capital)
        self.withdrawals = cv(withdrawals)
        self.cashBuffer = cv(cashBuffer)
        self.risk_mix = risk_mix
        self.risk_distribution = risk_distrib
        self.nb_years = nb_years
        self.nb_projections = nb_projections
        
    def run(self,id):
        '''Method to run a single projection'''

        # init simulation
        self.start(id)

        # run all periods
        for period in range(1,self.nb_years+1):
            self.processPeriod(period)

        # wrap up
        self.wrapUp()

    def start(self,id):

        # init id
        self.id =id
        
        # initiate period
        self.period = 0

        # creata a portfolio made 100% of cash
        cashAmount = self.cashBuffer
        cash_ptf=Portfolio.create_100pct_cash(amount=cashAmount)

        # create non cash portfolio
        nonCashAmount = self.initial_capital - cashAmount
        nonCash_ptf = Portfolio.create_non_cash(amount=nonCashAmount,risk_mix=self.risk_mix)

        # define portfolio as cash + non cash portfolios
        self.ptf_eop = cash_ptf + nonCash_ptf

        # notify observers
        self.notifyObservers(step=ps.START)


    def processPeriod(self, period):

        # retrieve period
        self.period = period

        # notify observers
        self.notifyObservers(step=ps.BOP)

        # retrieve parameters
        self.ptf_bop = self.ptf_eop.dup()

        # determine how much cash is available
        self.availableCash=self.ptf_bop.lines[rc.MONEY_MARKET]
        self.cashDepletion = min(self.withdrawals,self.availableCash)
        self.availableCash-=self.cashDepletion

        # reflect cash depletion
        
        self.ptf1 = self.ptf_bop.dup()
        self.shortfall = self.withdrawals - self.cashDepletion
        self.ptf1.lines[rc.MONEY_MARKET] -= self.cashDepletion
        self.ptf1.lines[rc.BOND] -= self.shortfall

        # rebalance portfolio
        self.ptf2 = self.ptf1.dup()
        self.ptf2.rebalance(self.risk_mix)
        v1 = self.ptf2.total_value()

        # investment income
        self.returns = {k:self.risk_distribution[k].distribution[period].draw()/100.0 for k in self.risk_distribution}
    
        # Apply returns
        self.ptf3 = self.ptf2.dup()
        self.ptf3.applyReturns(self.returns)
        v2= self.ptf3.total_value()
    
        # Financial Gain Loss
        self.financialGainLoss = v2 - v1

        # determine if replenishment of cash is needed
        if self.financialGainLoss>0:
            self.cashReplenishment = min(self.cashBuffer-self.ptf3.lines[rc.MONEY_MARKET], v2-v1)
            self.ptf4 = self.ptf3.dup()
            self.ptf4.growByPeriodMovement({rc.MONEY_MARKET :+self.cashReplenishment,
                                      rc.BOND         :-self.cashReplenishment})
            self.ptf5 = self.ptf4.dup()
            self.ptf5.rebalance(self.risk_mix)
        else:
            self.cashReplenishment = 0
            self.ptf5 = self.ptf4 = self.ptf3

        self.ptf_eop = self.ptf5

        self.notifyObservers(step=ps.EOP)
        
    def wrapUp(self):
        '''this method to run at the end'''

        self.notifyObservers(step=ps.WRAPUP)




class StatisticalObserver(Observer):
    '''
    Class to observe quantity in a projection and store value to enable statistic analysis
    '''

    def __init__(self, quantity = lambda : None, condition = lambda :True ):
        self.quantity = quantity
        self.condition = condition
        self.values = []
        self._reset_moment_data()

    def _reset_moment_data(self):
        '''Reset moment data'''
        self._mdata={}

    def processNotification(self, observed, **params):
        '''Method to respond to notification'''

        # test if process should apply
        if self.condition(observed, **params):

            # reset data used for calculations of all moment
            self._reset_moment_data()
            v = self.quantity(observed, **params)
            if v:
                self.values.append(v)
            else:
                raise(Exception(f"Value not defined"))

    def mean(self):
        if 'mean' not in self._mdata:
            values = self.values
            l = len(values)
            self._mdata['mean'] =  sum(values) / l if l>0 else float('nan')
        return self._mdata['mean']
    
    def std(self):
        if 'std' not in self._mdata:
            values = self.values
            if len(values)==0:
                self._mdata['std']= float('nan')
            else:
                m=self.mean()
                v=sum([v*v for v in values])/len(values) - m*m
                self._mdata['std'] = math.sqrt(v)
        return self._mdata['std']

    def quantile(self, pct):
        '''0<pct<=1 '''
        
        if 'ord' not in self._mdata:
            self._mdata['ord'] = sorted(self.values)
        l=len(self.values)
        i=round(l*pct*l/(l+1))
        return self._mdata['ord'][i]
        
    def min(self):
        return self.quantile(0.0)
    
    def max(self):
        return self.quantile(1.0)

    def __repr__(self):
        details = self.getDetails()
        simplified = " | ".join(details[1:-1].split("|")[0:3]) 
        return f"[{simplified}]"

    def getDetails(self):
        m, s, N, min_, max_ = self.mean(), self.std(), len(self.values), self.min(), self.max()
        s = f"[mean = {m:,.0f} | std = {s:,.0f} | N={N:,.0f} | min={min_:,.0f} | max={max_:,.0f}"
        for pct in [.01, .1 , .5]:
            s += f" | q({pct*100}%)={self.quantile(pct):,.2f}"
        s+="]"
        return s


class AuditObserver(Observer):

    def __init__(self, out=sys.stdout):
        super().__init__()
        self.out = out

    def processNotification(self, observed, **params):
        step = params['step']
        id = observed.id
        period = observed.period
        out = self.out

        if step == ps.START:
            
            print(header(f"Period 0 ( simulation {id:0>5})",pattern="#")+"\n", file = out)
            print(observed.ptf_eop.getCompoStr(), file=out)
            print(file=out)

        elif step == ps.BOP:
            print(header(f"Period {period: >2}", pattern="*")+"\n", file = out)
        elif step == ps.EOP:
            print(observed.ptf_eop.getCompoStr(), file=out)
        elif step == ps.WRAPUP:
            print("\n"*2, file=out)
        else:
            raise(Exception(f'No code for step {step}'))


class CSV_Observer(Observer):

    def __init__(self, file_name):
        super().__init__()
        self.file_name = file_name
        self.lines =[]
        self.ptfs =['ptf_bop','ptf_eop',     'ptf1', 'ptf2', 'ptf3', 'ptf4', 'ptf5']
        self.vars = [ 'withdrawals', 'availableCash', 'cashBuffer', 'cashDepletion','shortfall', 'cashReplenishment','financialGainLoss']

    def _addLine(self, items):
        line = ",".join(items)
        self.lines.append(line)

    def addHeader(self, observed):
        if observed.id == 1:
            self._addLine(['simulation', 'period', 'variable', 'risk', 'value'])

    def write_data(self, observed):

        def newLine(variable, risk, value):
            self._addLine([f"{observed.id}", f"{observed.period}", variable, risk, f"{value}"])

        # write portfolios
        for item in self.ptfs:
            lines = observed.__dict__[item].lines
            for line in lines:
                value=lines[line]
                newLine(item, line.name, value)

        # write returns
        for line in observed.returns:
            value = observed.returns[line]
            newLine('returns', line.name, value)

        # write withdrawals and other quantities
        for var in self.vars:
            newLine(var,'',observed.__dict__[var])
        
        pass

    def save(self, observed):

        # check if current projection is the last
        if observed.id == observed.nb_projections:

            f = open(self.file_name, 'w')
            for line in self.lines:
                print(line, file=f)
            f.close()

    def processNotification(self, observed, **params):
        step = params['step']
        
        indirection = {ps.START:self.addHeader, ps.EOP: self.write_data,ps.WRAPUP:self.save}

        if step in indirection:
            indirection[step](observed)

if __name__ == '__main__':
    raise(Exception('This code is meant to be used as a library, not to be run. Run inv_proj_run.py instead.'))
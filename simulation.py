"""Illustrative deterministic manufacturing simulator, not a fitted AI model.
All constants, distributions and units below define an invented demo scenario.
"""
import itertools
import math
import numpy as np
import pandas as pd

VERSION='synthetic_demo_v1'
BOUNDS={'rpm':(2000,8000),'feed':(300,1800),'depth':(.3,2.5),'wear':(0,100)}

def simulate(rpm,feed,depth,wear,ra_limit=1.6):
    vals={'rpm':rpm,'feed':feed,'depth':depth,'wear':wear}
    for k,v in vals.items():
        if not np.isfinite(v) or not BOUNDS[k][0]<=v<=BOUNDS[k][1]:raise ValueError(k+' 입력 범위를 확인하세요.')
    if not np.isfinite(ra_limit) or ra_limit<=0:raise ValueError('Ra 기준은 양수여야 합니다.')
    # Fictional 4-flute cutter, 8 mm engagement, 6000 mm³ removal per product.
    w=wear/100;fz=feed/(4*rpm);mrr=feed*depth*8
    ra=.25+.5*(fz/.06)**1.4+.2*depth**1.5+.3*w+.1*((rpm-5000)/3000)**2
    sigma=.12+.1*w
    roughness_reject=.5*math.erfc((ra_limit-ra)/(sigma*math.sqrt(2)))
    other_reject=.004+.025*w*w
    defect=1-(1-roughness_reject)*(1-other_reject)
    time_min=6000/mrr+.15
    idle_power=.7+.00022*rpm
    cutting_power=idle_power+.00018*mrr*(1+.5*w)
    energy=(cutting_power*(6000/mrr)+idle_power*.15)/60
    power=energy*60/time_min
    return dict(rpm=float(rpm),feed=float(feed),depth=float(depth),wear=float(wear),ra=ra,
                defect_pct=100*defect,yield_pct=100*(1-defect),power_kw=power,
                cycle_sec=time_min*60,energy_kwh=energy,ra_limit=float(ra_limit),data_origin=VERSION)

def optimize(current,ra_limit,min_yield,delay_pct,objective):
    if not 0<=min_yield<=100 or not 0<=delay_pct<=100:raise ValueError('목표 범위를 확인하세요.')
    rows=[]
    grids=[sorted(set(np.linspace(*BOUNDS[k],13).tolist()+[current[k]])) for k in ['rpm','feed','depth']]
    for rpm,feed,depth in itertools.product(*grids):
        rows.append(simulate(rpm,feed,depth,current['wear'],ra_limit))
    df=pd.DataFrame(rows)
    max_time=current['cycle_sec']*(1+delay_pct/100)
    df['feasible']=(df.ra<=ra_limit)&(df.yield_pct>=min_yield)&(df.cycle_sec<=max_time+1e-9)
    # Even an efficient starting condition remains a valid candidate; ties preserve it.
    if objective=='양품률 우선':keys=['defect_pct','energy_kwh']
    elif objective=='전력 절감 우선':keys=['energy_kwh','defect_pct']
    else:
        df['balance_score']=.5*(df.defect_pct/100)+.3*(df.energy_kwh/current['energy_kwh'])+.2*(df.cycle_sec/current['cycle_sec'])
        keys=['balance_score','energy_kwh']
    df=df.sort_values(keys).reset_index(drop=True)
    valid=df[df.feasible]
    return (None if valid.empty else valid.iloc[0].to_dict()),df

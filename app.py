import json
import numpy as np
import pandas as pd
import streamlit as st
from simulation import simulate, optimize, VERSION

st.set_page_config(page_title='가공조건 최적화 시뮬레이터',page_icon='⚙️',layout='wide')
st.markdown('''<style>.stApp{background:#f5f7fb}h1,h2,h3{color:#152b46}div[data-testid="stMetric"]{background:white;border:1px solid #e0e6ef;border-radius:12px;padding:18px}div[data-testid="stMetricValue"]{font-size:1.8rem}</style>''',unsafe_allow_html=True)
st.title('가공조건 최적화 시뮬레이터')
st.caption('조건 입력 → 최적 조건 찾기 → 품질 · 전력 · 생산성 비교')
st.info('SIMULATION · 모든 결과는 가상 공정의 계산값입니다. 실제 제조 데이터로 학습한 AI나 현장 성능 예측이 아닙니다.')
with st.form('conditions'):
    st.subheader('1. 현재 가공조건을 입력하세요')
    a,b,c,d=st.columns(4)
    rpm=a.number_input('주축 회전속도 (rpm)',min_value=2000,max_value=8000,value=4200,step=100,key='rpm')
    feed=b.number_input('이송속도 (mm/min)',min_value=300,max_value=1800,value=1000,step=50,key='feed')
    depth=c.number_input('절삭 깊이 (mm)',min_value=.3,max_value=2.5,value=1.8,step=.1,key='depth')
    wear=d.slider('공구 마모도 (%)',0,100,35,key='wear')
    st.caption('가상 설정: 동일 소재 · 4날 공구 · 절삭 폭 8 mm · 제품당 제거 체적 6,000 mm³. 공구 마모도는 상태값으로 고정하며 추천 과정에서 임의로 낮추지 않습니다.')
    st.subheader('2. 원하는 품질과 개선 목표를 정하세요')
    a,b,c,d=st.columns(4)
    ra_limit=a.number_input('허용 표면 거칠기 Ra (μm)',min_value=.1,max_value=5.,value=1.6,step=.1,key='ra_limit')
    min_yield=b.number_input('목표 양품률 (%)',min_value=50.,max_value=100.,value=95.,step=1.,key='min_yield')
    delay=c.slider('허용 가공시간 증가 (%)',0,100,15,key='delay')
    objective=d.selectbox('최적화 우선순위',['균형','양품률 우선','전력 절감 우선'],key='objective')
    submitted=st.form_submit_button('최적 조건 찾기',type='primary',width='stretch')

if submitted:
    current=simulate(rpm,feed,depth,wear,ra_limit)
    best,candidates=optimize(current,ra_limit,min_yield,delay,objective)
    st.session_state['result']={'current':current,'best':best,'candidates':candidates,'settings':{'Ra_limit':ra_limit,'min_yield':min_yield,'delay_pct':delay,'objective':objective}}

if 'result' not in st.session_state:
    st.markdown('### 조건을 입력하고 **최적 조건 찾기**를 눌러주세요')
    st.write('추천 조건과 현재 조건의 차이, 예상 불량률·양품률, 제품당 전력 사용량, 가공시간을 비교합니다.')
else:
    result=st.session_state['result'];cur=result['current'];best=result['best'];df=result['candidates'];settings=result['settings']
    st.caption(f"마지막 계산: {cur['rpm']:,.0f} rpm / 이송 {cur['feed']:,.0f} mm/min / 깊이 {cur['depth']:.2f} mm / 마모 {cur['wear']:.0f}% · {settings['objective']} 우선. 입력을 바꾼 뒤 버튼을 다시 눌러 계산하세요.")
    if best is None:
        st.warning('현재 목표를 모두 만족하는 후보가 없습니다. 품질 목표, 허용 가공시간 또는 공구 상태를 검토하세요. 조건을 만족하지 않는 추천값을 표시하지 않습니다.')
        a,b,c=st.columns(3)
        a.metric('현재 예상 양품률',f"{cur['yield_pct']:.1f}%")
        b.metric('현재 예상 Ra',f"{cur['ra']:.2f} μm")
        c.metric('현재 제품당 전력 사용량',f"{cur['energy_kwh']*1000:.1f} Wh")
    else:
        st.subheader('3. 이렇게 조절해 보세요')
        labels={'rpm':('주축 회전속도','rpm'),'feed':('이송속도','mm/min'),'depth':('절삭 깊이','mm')}
        cols=st.columns(3)
        for col,(key,(label,unit)) in zip(cols,labels.items()):
            diff=best[key]-cur[key]
            action='유지' if abs(diff)<1e-8 else ('높이기' if diff>0 else '낮추기')
            with col:
                st.metric(label,f'{best[key]:,.2f} {unit}',f'{diff:+,.2f} {unit}',delta_color='off')
                st.caption(f"현재 {cur[key]:,.2f} → 추천 {best[key]:,.2f} · {action}")
        st.success(f"탐색한 {len(df):,}개 조건 중 {int(df.feasible.sum()):,}개가 품질·양품률·시간 기준을 충족했습니다. 그중 선택한 목표의 최상위 후보입니다.")
        st.subheader('4. 변경 전후를 한눈에 비교하세요')
        a,b,c,d=st.columns(4)
        a.metric('예상 불량률',f"{best['defect_pct']:.1f}%",f"{best['defect_pct']-cur['defect_pct']:+.1f}%p",delta_color='inverse')
        b.metric('예상 양품률',f"{best['yield_pct']:.1f}%",f"{best['yield_pct']-cur['yield_pct']:+.1f}%p")
        energy_change=100*(best['energy_kwh']/cur['energy_kwh']-1)
        c.metric('제품당 전력 사용량',f"{best['energy_kwh']*1000:.1f} Wh",f'{energy_change:+.1f}%',delta_color='inverse')
        d.metric('제품당 가공시간',f"{best['cycle_sec']:.1f} 초",f"{best['cycle_sec']-cur['cycle_sec']:+.1f} 초",delta_color='inverse')
        metrics=[('평균 표면 거칠기 Ra (μm)','ra',1),('불량률 (%)','defect_pct',1),('양품률 (%)','yield_pct',1),('평균 소비전력 (kW)','power_kw',1),('제품당 전력 사용량 (Wh)','energy_kwh',1000),('1,000개 투입 전력 사용량 (kWh)','energy_kwh',1000),('제품당 가공시간 (초)','cycle_sec',1)]
        comparison=pd.DataFrame([{'항목':label,'현재':cur[k]*scale,'추천':best[k]*scale,'변화':(best[k]-cur[k])*scale} for label,k,scale in metrics])
        st.dataframe(comparison,hide_index=True,width='stretch')
        st.caption('1,000개 투입 기준이며 양품 1,000개 생산 기준이 아닙니다. 소비전력(kW)은 순간적인 부하의 평균, 전력 사용량(kWh)은 가공시간까지 반영한 에너지입니다. 모든 차이는 시뮬레이션 계산값입니다.')
        if energy_change>0:st.warning('이번 목표에서는 품질 또는 생산성을 우선해 전력 사용량이 증가했습니다. 전력 절감 우선으로 비교해 보세요.')
        with st.expander('왜 이런 조절을 추천하나요?',expanded=True):
            st.write('이 시뮬레이션에서는 날당 이송과 절삭 깊이, 공구 마모가 커질수록 표면 거칠기가 증가합니다. 너무 느리게 가공하면 시간이 늘어 대기·회전 전력의 누적 사용량이 커집니다. 추천은 품질을 만족하는 범위에서 이 관계를 비교한 결과입니다.')
            st.write(f"날당 이송: {cur['feed']/(4*cur['rpm']):.4f} → {best['feed']/(4*best['rpm']):.4f} mm/tooth. 공구 마모 {cur['wear']:.0f}%는 동일하게 유지했습니다. 실제 공정의 인과관계나 최적점을 입증하는 설명은 아닙니다.")
        with st.expander('가공조건을 하나씩 바꾸면 어떻게 달라지나요?'):
            key=st.selectbox('살펴볼 변수',['rpm','feed','depth'],format_func=lambda k:labels[k][0])
            bounds={'rpm':(2000,8000),'feed':(300,1800),'depth':(.3,2.5)}
            sweep=[]
            for value in np.linspace(*bounds[key],41):
                inputs={k:cur[k] for k in ['rpm','feed','depth','wear']};inputs[key]=value
                sweep.append(simulate(**inputs,ra_limit=cur['ra_limit']))
            curve=pd.DataFrame(sweep).set_index(key)
            a,b=st.columns(2)
            a.line_chart(curve[['defect_pct','yield_pct']]);b.line_chart(curve.energy_kwh*1000)
            st.caption('왼쪽: 불량률·양품률(%), 오른쪽: 제품당 전력 사용량(Wh). 선택한 변수 외에는 현재 입력값으로 고정합니다.')
        payload={'simulation':True,'version':VERSION,'settings':settings,'current':cur,'recommended':best}
        st.download_button('변경 전후 결과 저장',json.dumps(payload,ensure_ascii=False,indent=2),'simulation_comparison.json','application/json')
    with st.expander('가상 후보 데이터 확인 · 내려받기'):
        st.dataframe(df.head(30),hide_index=True,width='stretch')
        st.download_button('전체 시뮬레이션 데이터 CSV',df.to_csv(index=False).encode('utf-8-sig'),'synthetic_candidates.csv','text/csv')
with st.expander('시뮬레이션 가정과 실제 데이터 전환'):
    st.write('기존 KAMP·AISI 파일과 학습 모델은 이 화면에서 사용하지 않습니다. 모든 후보와 결과는 고정된 가상 수식으로 계산하며, 데이터로 학습한 AI가 아닙니다. 실제 설비 설정값으로 사용하지 마세요.')
    st.write('Ra는 가상 평균값입니다. 정규분포의 가상 산포와 마모에 따른 추가 불량을 가정해 규격 초과 비율을 불량률로 계산합니다. 양품률=100−불량률입니다. 에너지는 평균 소비전력×가공시간으로 계산합니다. 수식·계수·공구·제거 체적은 설명을 위한 임의 가정입니다.')
    st.write('나중에는 같은 가공 건에 조건·센서·검사 합격 여부·Ra·전력 계측값·가공시간을 함께 수집해 이 계산 부분을 학습 모델로 교체합니다. 현재는 제품당 동일 제거 체적, 공구 교환 없음, 가공시간 증가 제한을 적용합니다.')

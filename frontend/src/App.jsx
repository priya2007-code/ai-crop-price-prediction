import { useEffect, useState } from 'react'
import './App.css'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const FILTERS = ['state_name', 'district_name', 'market_center_name', 'commodity_name', 'variety', 'grade']
const LABELS = ['State', 'District', 'Market', 'Commodity', 'Variety', 'Grade']
const OPTION_KEYS = ['states', 'districts', 'markets', 'commodities', 'varieties', 'grades']
const EMPTY_SELECTION = Object.fromEntries(FILTERS.map((key) => [key, '']))
const EMPTY_OPTIONS = Object.fromEntries(OPTION_KEYS.map((key) => [key, []]))
const SCREENS = [
  { id: 'overview', label: 'Overview' },
  { id: 'forecast', label: 'Forecast' },
  { id: 'markets', label: 'Market comparison' },
  { id: 'trends', label: 'Trends & volatility' },
  { id: 'explainability', label: 'Explainable AI' },
  { id: 'decisions', label: 'Decision support' },
]

const readScreen = () => {
  const screen = window.location.hash.slice(1)
  return SCREENS.some((item) => item.id === screen) ? screen : 'overview'
}

function Glyph({ name, size = 16, className }) {
  const common = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' }
  const paths = {
    arrowRight: <><path d="M5 12h14" /><path d="m12 5 7 7-7 7" /></>,
    arrowUpRight: <><path d="M7 17 17 7" /><path d="M8 7h9v9" /></>,
    arrowDownRight: <><path d="M7 7 17 17" /><path d="M8 17h9V8" /></>,
    chart: <><path d="M3 3v18h18" /><path d="m19 9-5 5-4-4-5 5" /></>,
    check: <><path d="m5 12 4 4L19 6" /></>,
    chevron: <><path d="m6 9 6 6 6-6" /></>,
    alert: <><path d="M10.3 3.9 2.5 17.4A2 2 0 0 0 4.2 20h15.6a2 2 0 0 0 1.7-2.6L13.7 3.9a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4" /><path d="M12 17h.01" /></>,
    leaf: <><path d="M20 4c-8 0-14 3-14 10a6 6 0 0 0 6 6c7 0 10-8 8-16Z" /><path d="M4 21c2-5 6-8 12-11" /></>,
    loader: <><path d="M21 12a9 9 0 0 1-9 9" /><path d="M3 12a9 9 0 0 1 9-9" /></>,
    pin: <><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z" /><circle cx="12" cy="10" r="2.5" /></>,
    search: <><circle cx="10.8" cy="10.8" r="6.8" /><path d="m16 16 4.5 4.5" /></>,
    sprout: <><path d="M12 21v-9" /><path d="M12 12C8 12 5 9 5 5c4 0 7 2 7 7Z" /><path d="M12 15c0-4 3-7 7-7 0 4-3 7-7 7Z" /><path d="M7 21h10" /></>,
    trend: <><path d="m3 17 6-6 4 4 8-9" /><path d="M15 6h6v6" /></>,
    wheat: <><path d="M12 22V3" /><path d="M12 7c-4 0-6-2-6-5 4 0 6 2 6 5Z" /><path d="M12 12c-4 0-6-2-6-5 4 0 6 2 6 5Z" /><path d="M12 17c-4 0-6-2-6-5 4 0 6 2 6 5Z" /><path d="M12 9c4 0 6-2 6-5-4 0-6 2-6 5Z" /><path d="M12 14c4 0 6-2 6-5-4 0-6 2-6 5Z" /></>,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden="true" {...common}>{paths[name]}</svg>
}

const ArrowDownRight = (props) => <Glyph name="arrowDownRight" {...props} />
const ArrowRight = (props) => <Glyph name="arrowRight" {...props} />
const ArrowUpRight = (props) => <Glyph name="arrowUpRight" {...props} />
const BarChart3 = (props) => <Glyph name="chart" {...props} />
const Check = (props) => <Glyph name="check" {...props} />
const ChevronDown = (props) => <Glyph name="chevron" {...props} />
const CircleAlert = (props) => <Glyph name="alert" {...props} />
const Leaf = (props) => <Glyph name="leaf" {...props} />
const LoaderCircle = (props) => <Glyph name="loader" {...props} />
const MapPin = (props) => <Glyph name="pin" {...props} />
const Search = (props) => <Glyph name="search" {...props} />
const Sprout = (props) => <Glyph name="sprout" {...props} />
const TrendingUp = (props) => <Glyph name="trend" {...props} />
const Wheat = (props) => <Glyph name="wheat" {...props} />

const money = (value) => Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })
const signed = (value) => `${Number(value) >= 0 ? '+' : ''}${Number(value || 0).toFixed(2)}%`

function PriceChart({ history, prediction }) {
  if (!history.length) {
    return <div className="chart-empty">Run a forecast to see the price history for this market.</div>
  }

  const values = history.map((item) => Number(item.modal_price))
  if (prediction) values.push(Number(prediction.predicted_price))
  const low = Math.min(...values) * 0.96
  const high = Math.max(...values) * 1.04
  const range = high - low || 1
  const width = 760
  const height = 250
  const left = 54
  const right = 18
  const top = 18
  const bottom = 34
  const plotWidth = width - left - right
  const plotHeight = height - top - bottom
  const points = history.map((item, index) => {
    const x = left + (index / Math.max(values.length - 1, 1)) * plotWidth
    const y = top + (1 - (Number(item.modal_price) - low) / range) * plotHeight
    return [x, y]
  })
  if (prediction) {
    points.push([
      left + ((values.length - 1) / Math.max(values.length - 1, 1)) * plotWidth,
      top + (1 - (Number(prediction.predicted_price) - low) / range) * plotHeight,
    ])
  }
  const line = points.map((point) => point.join(',')).join(' ')
  const area = `${left},${height - bottom} ${line} ${left + plotWidth},${height - bottom}`

  return (
    <div className="chart-wrap">
      <svg className="price-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Historical crop prices and next-day forecast">
        <defs>
          <linearGradient id="chart-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#62855a" />
            <stop offset="100%" stopColor="#62855a" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 1, 2, 3].map((step) => {
          const y = top + (step / 3) * plotHeight
          const label = Math.round(high - (step / 3) * range)
          return (
            <g key={step}>
              <line x1={left} y1={y} x2={width - right} y2={y} className="chart-grid" />
              <text x={left - 10} y={y + 4} className="chart-label" textAnchor="end">₹{money(label)}</text>
            </g>
          )
        })}
        <polygon points={area} className="chart-area" />
        <polyline points={line} className="chart-line" />
        {points.filter((_, index) => index === points.length - 1).map(([x, y]) => (
          <g key="forecast-point">
            <circle cx={x} cy={y} r="6" className="chart-point-halo" />
            <circle cx={x} cy={y} r="3.2" className="chart-point" />
          </g>
        ))}
        <text x={left} y={height - 8} className="chart-label">{history[0]?.date || ''}</text>
        <text x={width - right} y={height - 8} className="chart-label" textAnchor="end">{prediction?.forecast_date || history[history.length - 1]?.date || ''}</text>
      </svg>
    </div>
  )
}

function App() {
  const [activeScreen, setActiveScreen] = useState(readScreen)
  const [options, setOptions] = useState(EMPTY_OPTIONS)
  const [selection, setSelection] = useState(EMPTY_SELECTION)
  const [health, setHealth] = useState(null)
  const [prediction, setPrediction] = useState(null)
  const [history, setHistory] = useState([])
  const [markets, setMarkets] = useState([])
  const [marketForecasts, setMarketForecasts] = useState([])
  const [opportunities, setOpportunities] = useState([])
  const [marketSort, setMarketSort] = useState('change')
  const [marketOutlookLoaded, setMarketOutlookLoaded] = useState(false)
  const [marketError, setMarketError] = useState('')
  const [loading, setLoading] = useState(false)
  const [booting, setBooting] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const syncScreen = () => setActiveScreen(readScreen())
    window.addEventListener('hashchange', syncScreen)
    return () => window.removeEventListener('hashchange', syncScreen)
  }, [])

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [activeScreen])

  useEffect(() => {
    let active = true
    Promise.all([
      fetch(`${API_BASE}/health`).then((response) => response.json()),
      fetch(`${API_BASE}/api/options`).then((response) => response.json()),
    ]).then(([healthData, optionData]) => {
      if (!active) return
      setHealth(healthData)
      setOptions((current) => ({ ...current, states: optionData.states || [] }))
      if (optionData.states?.length) setSelection((current) => ({ ...current, state_name: optionData.states[0] }))
    }).catch(() => {
      if (active) setError('Could not connect to the prediction service. Start the FastAPI backend and refresh.')
    }).finally(() => {
      if (active) setBooting(false)
    })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!selection.state_name) return
    let active = true
    const query = new URLSearchParams({ state_name: selection.state_name })
    fetch(`${API_BASE}/api/options?${query}`).then((response) => response.json()).then((data) => {
      if (!active) return
      setOptions((current) => ({ ...current, districts: data.districts || [] }))
      if (data.districts?.length) setSelection((current) => current.district_name ? current : ({ ...current, district_name: data.districts[0] }))
    }).catch(() => {})
    return () => { active = false }
  }, [selection.state_name])

  useEffect(() => {
    if (!selection.state_name || !selection.district_name) return
    let active = true
    const query = new URLSearchParams({ state_name: selection.state_name, district_name: selection.district_name })
    fetch(`${API_BASE}/api/options?${query}`).then((response) => response.json()).then((data) => {
      if (!active) return
      setOptions((current) => ({ ...current, markets: data.markets || [] }))
      if (data.markets?.length) setSelection((current) => current.market_center_name ? current : ({ ...current, market_center_name: data.markets[0] }))
    }).catch(() => {})
    return () => { active = false }
  }, [selection.state_name, selection.district_name])

  useEffect(() => {
    if (!selection.state_name || !selection.district_name || !selection.market_center_name) return
    let active = true
    const query = new URLSearchParams({ state_name: selection.state_name, district_name: selection.district_name, market_center_name: selection.market_center_name })
    fetch(`${API_BASE}/api/options?${query}`).then((response) => response.json()).then((data) => {
      if (!active) return
      setOptions((current) => ({ ...current, commodities: data.commodities || [] }))
      if (data.commodities?.length) setSelection((current) => current.commodity_name ? current : ({ ...current, commodity_name: data.commodities[0] }))
    }).catch(() => {})
    return () => { active = false }
  }, [selection.state_name, selection.district_name, selection.market_center_name])

  useEffect(() => {
    if (!selection.commodity_name) return
    let active = true
    const query = new URLSearchParams({ commodity_name: selection.commodity_name, limit: '12' })
    fetch(`${API_BASE}/api/markets?${query}`).then((response) => response.json()).then((data) => {
      if (active) setMarkets(data.markets || [])
    }).catch(() => {})
    if (!selection.state_name || !selection.district_name || !selection.market_center_name) return () => { active = false }
    const optionQuery = new URLSearchParams({ state_name: selection.state_name, district_name: selection.district_name, market_center_name: selection.market_center_name, commodity_name: selection.commodity_name })
    fetch(`${API_BASE}/api/options?${optionQuery}`).then((response) => response.json()).then((data) => {
      if (!active) return
      setOptions((current) => ({ ...current, varieties: data.varieties || [] }))
      if (data.varieties?.length) setSelection((current) => current.variety ? current : ({ ...current, variety: data.varieties[0] }))
    }).catch(() => {})
    return () => { active = false }
  }, [selection.state_name, selection.district_name, selection.market_center_name, selection.commodity_name])

  useEffect(() => {
    if (!selection.variety || !selection.commodity_name) return
    let active = true
    const query = new URLSearchParams({ state_name: selection.state_name, district_name: selection.district_name, market_center_name: selection.market_center_name, commodity_name: selection.commodity_name, variety: selection.variety })
    fetch(`${API_BASE}/api/options?${query}`).then((response) => response.json()).then((data) => {
      if (!active) return
      setOptions((current) => ({ ...current, grades: data.grades || [] }))
      if (data.grades?.length) setSelection((current) => current.grade ? current : ({ ...current, grade: data.grades[0] }))
    }).catch(() => {})
    return () => { active = false }
  }, [selection.state_name, selection.district_name, selection.market_center_name, selection.commodity_name, selection.variety])

  useEffect(() => {
    if (!selection.commodity_name || !selection.variety || !selection.grade) {
      return
    }
    let active = true
    const query = new URLSearchParams({
      commodity_name: selection.commodity_name,
      variety: selection.variety,
      grade: selection.grade,
      limit: '100',
    })
    fetch(`${API_BASE}/api/market-outlook?${query}`).then(async (response) => {
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Market forecasts are not available.')
      return data
    }).then((data) => {
      if (!active) return
      setMarketForecasts(data.markets || [])
      setOpportunities(data.opportunities || [])
      setMarketOutlookLoaded(true)
    }).catch((fetchError) => {
      if (active) {
        setMarketError(fetchError.message || 'Could not load real market forecasts.')
        setMarketOutlookLoaded(true)
      }
    })
    return () => { active = false }
  }, [selection.commodity_name, selection.variety, selection.grade])

  const updateSelection = (field, value) => {
    const index = FILTERS.indexOf(field)
    const downstream = FILTERS.slice(index + 1)
    const cleared = downstream.reduce((next, key) => ({ ...next, [key]: '' }), {})
    const clearedOptions = downstream.reduce((next, key) => ({ ...next, [OPTION_KEYS[FILTERS.indexOf(key)]]: [] }), {})
    setSelection((current) => ({ ...current, ...cleared, [field]: value }))
    setOptions((current) => ({ ...current, ...clearedOptions }))
    setPrediction(null)
    setHistory([])
    setMarketForecasts([])
    setOpportunities([])
    setMarketOutlookLoaded(false)
    setMarketError('')
    setMarketSort('change')
  }

  const ready = FILTERS.every((field) => selection[field])
  const marketOutlookLoading = Boolean(selection.commodity_name && selection.variety && selection.grade && !marketOutlookLoaded && !marketError)
  const marketRows = selection.grade ? marketForecasts : markets
  const sortedMarketRows = [...marketRows].sort((left, right) => {
    if (marketSort === 'current') return Number(right.current_price ?? right.latest_price) - Number(left.current_price ?? left.latest_price)
    if (marketSort === 'predicted') return Number(right.predicted_price ?? right.latest_price) - Number(left.predicted_price ?? left.latest_price)
    if (marketSort === 'risk') {
      const riskScore = (market) => market.risk ? ({ Low: 0, Medium: 1, High: 2 }[market.risk] ?? 3) : Number(market.volatility_30d ?? Infinity)
      return riskScore(left) - riskScore(right)
    }
    return Number(right.percentage_change ?? right.pct_change_7d) - Number(left.percentage_change ?? left.pct_change_7d)
  })

  const predict = async (event) => {
    event.preventDefault()
    if (!ready) return
    setLoading(true)
    setError('')
    setPrediction(null)
    try {
      const response = await fetch(`${API_BASE}/api/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(selection),
      })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Forecast could not be generated for this selection.')
      setPrediction(result)
      const query = new URLSearchParams({ ...selection, limit: '60' })
      const historyResponse = await fetch(`${API_BASE}/api/history?${query}`)
      if (historyResponse.ok) {
        const historyData = await historyResponse.json()
        setHistory(historyData.history || [])
      }
    } catch (fetchError) {
      setError(fetchError.message || 'Something went wrong while generating the forecast.')
    } finally {
      setLoading(false)
    }
  }

  const movement = Number(prediction?.percentage_change || 0)
  const activeScreenInfo = SCREENS.find((screen) => screen.id === activeScreen)
  const screenDescriptions = {
    forecast: 'Next-day XGBoost price outlook for the selected mandi series.',
    markets: 'Compare real model forecasts for markets with sufficient matching history.',
    trends: 'Historical modal prices, recent direction, and rolling volatility.',
    explainability: 'Signed TreeSHAP contributions and the loaded model’s global feature importance.',
    decisions: 'Anomaly context, forecast risk, and a recommendation grounded in observed signals.',
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#overview" aria-label="Fieldnotes overview">
          <span className="brand-mark"><Sprout size={21} strokeWidth={1.8} /></span>
          <span className="brand-name">fieldnotes<span>.</span></span>
        </a>
        <div className="topbar-right">
          <span className="edition">INDIA · MARKET INTELLIGENCE</span>
          <span className={`service-status ${health?.status === 'ok' ? 'is-live' : ''}`}>
            <span className="status-dot" />{health?.status === 'ok' ? 'Model live' : 'Connecting'}
          </span>
        </div>
      </header>

      <nav className="main-nav" aria-label="Main menu">
        {SCREENS.map((screen) => (
          <a className={`main-nav-link ${activeScreen === screen.id ? 'is-active' : ''}`} href={`#${screen.id}`} key={screen.id} aria-current={activeScreen === screen.id ? 'page' : undefined}>
            {screen.label}
          </a>
        ))}
      </nav>

      <main className={`screen-main screen-${activeScreen}`} id="top">
        {activeScreen === 'overview' && <section className="hero-banner">
          <div className="hero-photo" />
          <div className="hero-content">
            <div className="eyebrow"><span /> THE HARVEST REPORT <span className="eyebrow-date">VOL. 01 / 2026</span></div>
            <h1>Know the worth<br />of what you <em>grow.</em></h1>
            <p>Market signals for India’s next harvest.<br className="desktop-break" /> Grounded in mandi data, built for better decisions.</p>
            <a className="hero-link" href="#forecast">Explore today’s outlook <ArrowRight size={16} /></a>
          </div>
          <div className="hero-caption"><span>01 — 04</span><span>FIELD TO MARKET</span></div>
          <div className="hero-stamp"><Wheat size={19} /><span>GROWN<br />WITH DATA</span></div>
        </section>}

        <div className="page-content">
          {activeScreen !== 'overview' && <div className="screen-title">
            <span className="section-kicker">FIELDNOTES / {String(SCREENS.findIndex((screen) => screen.id === activeScreen) + 1).padStart(2, '0')}</span>
            <h1>{activeScreenInfo?.label}</h1>
            <p>{screenDescriptions[activeScreen]}</p>
          </div>}

          <div className="section-heading">
            <div><span className="section-kicker">YOUR MARKET, IN FOCUS</span><h2>{activeScreen === 'overview' ? 'Build a price outlook' : 'Selected mandi series'}</h2></div>
            <span className="data-note"><span className="data-note-dot" /> {health?.rows ? `${health.rows.toLocaleString()} market records` : 'Live market data'}</span>
          </div>

          {error && <div className="error-banner" role="alert"><CircleAlert size={18} /><span>{error}</span><button type="button" onClick={() => setError('')} aria-label="Dismiss error">×</button></div>}

          <form className="selector-panel" onSubmit={predict}>
            <div className="selector-topline"><div className="selector-label"><Search size={16} /><span>MARKET SELECTOR</span></div><span className="selector-step">01 <i>/</i> 02</span></div>
            <div className="selector-grid">
              {FILTERS.map((field, index) => {
                const parent = index === 0 ? true : Boolean(selection[FILTERS[index - 1]])
                const valueList = options[OPTION_KEYS[index]] || []
                return (
                  <label className={`select-field ${!parent ? 'is-disabled' : ''}`} key={field}>
                    <span>{LABELS[index]}<b>{String(index + 1).padStart(2, '0')}</b></span>
                    <div className="select-wrap">
                      <select value={selection[field]} onChange={(event) => updateSelection(field, event.target.value)} disabled={!parent || booting}>
                        <option value="">{booting ? 'Loading markets…' : `Choose ${LABELS[index].toLowerCase()}`}</option>
                        {valueList.map((value) => <option value={value} key={value}>{value}</option>)}
                      </select>
                      <ChevronDown size={15} aria-hidden="true" />
                    </div>
                  </label>
                )
              })}
              <button className="forecast-button" type="submit" disabled={!ready || loading}>
                {loading ? <><LoaderCircle className="spin" size={17} /> Reading market</> : <>Get price outlook <ArrowRight size={17} /></>}
              </button>
            </div>
            <div className="selector-foot"><MapPin size={13} /><span>{selection.market_center_name ? `${selection.market_center_name}${selection.district_name ? `, ${selection.district_name}` : ''}` : 'Select a market to begin'}</span><span className="secure-note"><Leaf size={13} /> Model-backed forecast</span></div>
          </form>

          {activeScreen === 'overview' && <section className="overview-links" aria-label="Explore app screens">
            {SCREENS.filter((screen) => screen.id !== 'overview').map((screen, index) => <a href={`#${screen.id}`} className="overview-link" key={screen.id}><span className="overview-link-index">0{index + 1}</span><span><strong>{screen.label}</strong><small>{screenDescriptions[screen.id]}</small></span><ArrowRight size={16} /></a>)}
          </section>}

          {prediction ? (
            <section className="outlook-section" id="forecast">
              <div className="outlook-heading">
                <div><span className="section-kicker">NEXT-DAY OUTLOOK · {prediction.forecast_date}</span><h2>The {selection.commodity_name} brief</h2></div>
                <span className={`trend-pill ${movement > 0.5 ? 'positive' : movement < -0.5 ? 'negative' : ''}`}>{movement > 0.5 ? <ArrowUpRight size={15} /> : movement < -0.5 ? <ArrowDownRight size={15} /> : null}{prediction.trend_label} market</span>
              </div>

              {Number(prediction.predicted_price) < 0 && <div className="volatility-alert"><CircleAlert size={17} /><span>Model warning: the estimate is below ₹0. Treat it as an outlier and verify against local market prices before making a decision.</span></div>}
              {Number(prediction.volatility_value) > 8 && <div className="volatility-alert"><CircleAlert size={17} /><span>Elevated volatility: recent price movement is unusually high at {prediction.volatility}.</span></div>}

              <div className="result-grid">
                <article className="price-feature">
                  <div className="feature-top"><span className="section-kicker">PREDICTED MODAL PRICE</span><span className="model-tag"><span /> XGBOOST MODEL</span></div>
                  <div className="feature-price"><span>₹</span>{money(prediction.predicted_price)}<small> / quintal</small></div>
                  <div className="feature-bottom"><span>Current ₹{money(prediction.current_price)} · observed {prediction.last_observed_date}</span><span className={`change-value ${Number(prediction.absolute_change) >= 0 ? 'positive-text' : 'negative-text'}`}>{Number(prediction.absolute_change) >= 0 ? '+' : '−'}₹{money(Math.abs(Number(prediction.absolute_change)))} <i>({signed(movement)})</i></span></div>
                  <div className="feature-rule" />
                  <div className="feature-current"><span>Current modal price</span><strong>₹{money(prediction.current_price)} <small>/ qtl</small></strong></div>
                </article>
                <article className="decision-panel">
                  <div className="decision-icon"><Check size={17} /></div>
                  <span className="section-kicker">MARKET READ</span>
                  <h3>{prediction.decision_support?.recommendation || prediction.recommendation}</h3>
                  <p>Decision support combines predicted change, trend, 30-observation volatility, risk and historical anomaly status.</p>
                  <div className="decision-meta"><span>RISK PROFILE</span><b className={`risk-${prediction.risk?.toLowerCase()}`}>{prediction.risk} <i>·</i> {prediction.volatility} volatility</b></div>
                </article>
              </div>

              <div className="signal-strip">
                <article className="signal-item"><span className="section-kicker">RECENT TREND</span><strong className={`signal-trend ${prediction.recent_trend?.toLowerCase()}`}>{prediction.recent_trend}</strong><small>{signed(prediction.recent_change_7_records_pct)} across recent observations</small></article>
                <article className="signal-item"><span className="section-kicker">ROLLING VOLATILITY</span><strong>{prediction.volatility}</strong><small>30 latest records · <b className={`vol-class ${prediction.volatility_class?.toLowerCase()}`}>{prediction.volatility_class}</b></small></article>
                <article className="signal-item"><span className="section-kicker">FORECAST RISK</span><strong className={`risk-text-${prediction.risk?.toLowerCase()}`}>{prediction.risk}</strong><small>Based on volatility and predicted change</small></article>
                <article className="signal-item"><span className="section-kicker">PRICE ANOMALY</span><strong className={`anomaly-${prediction.anomaly_status?.toLowerCase()}`}>{prediction.anomaly_status}</strong><small>Vs. preceding 30 records · ±2σ</small></article>
              </div>

              <div className="chart-panel">
                <div className="chart-heading"><div><span className="section-kicker">PRICE MOVEMENT</span><h3>History meets forecast</h3><p>Recent trend: <b>{prediction.recent_trend}</b> · Rolling volatility: <b>{prediction.volatility_class}</b> ({prediction.volatility})</p></div><div className="chart-legend"><span><i className="legend-history" />Historical</span><span><i className="legend-forecast" />XGBoost</span></div></div>
                <PriceChart history={history} prediction={prediction} />
              </div>

              <section className="explain-panel">
                <div className="explain-heading"><div><span className="section-kicker">EXPLAINABLE AI</span><h3>What moved this forecast</h3><p>Signed TreeSHAP contributions from the loaded XGBoost booster.</p></div><span className="explain-badge">LOCAL EXPLANATION</span></div>
                {prediction.feature_contributions?.available ? (
                  <>
                    <div className="importance-list">
                      {prediction.feature_contributions.factors.map((factor) => {
                        const maxContribution = Math.max(...prediction.feature_contributions.factors.map((item) => Math.abs(item.contribution)), 1)
                        const width = Math.max(2, Math.abs(factor.contribution) / maxContribution * 100)
                        return <div className="importance-row" key={factor.feature}>
                          <div className="importance-label"><strong>{factor.feature}</strong><span className={factor.contribution >= 0 ? 'positive-text' : 'negative-text'}>{factor.contribution >= 0 ? '+' : '−'}₹{money(Math.abs(factor.contribution))} <i>·</i> {factor.direction} forecast</span></div>
                          <div className="importance-track"><span className={factor.contribution >= 0 ? 'contribution-positive' : 'contribution-negative'} style={{ width: `${width}%` }} /></div>
                        </div>
                      })}
                    </div>
                    <p className="contribution-reconcile">Model base ₹{money(prediction.feature_contributions.base_value)} <ArrowRight size={12} /> forecast ₹{money(prediction.feature_contributions.reconstructed_prediction)} <span>Full contribution vector reconciles; strongest factors shown.</span></p>
                    <p className="explain-caveat">Signed TreeSHAP values describe how each input moves this prediction relative to the model base. They are model attributions, not causal effects.</p>
                  </>
                ) : <div className="importance-unavailable">{prediction.feature_contributions?.reason || 'This model did not return mappable local contributions.'}</div>}
                <details className="global-importance">
                  <summary>Global model importance <span>{prediction.feature_importance?.source || 'unavailable'}</span></summary>
                  {prediction.feature_importance?.available ? <div className="global-factor-list">{prediction.feature_importance.factors.map((factor) => <span key={factor.feature}><b>{factor.feature}</b><i>{factor.importance_pct.toFixed(2)}%</i></span>)}</div> : <p>{prediction.feature_importance?.reason || 'Global importance is unavailable from the loaded model.'}</p>}
                </details>
              </section>
              {activeScreen === 'decisions' && <section className="decision-detail-grid">
                <article className="decision-detail anomaly-detail">
                  <span className="section-kicker">HISTORICAL PRICE ANOMALY</span>
                  <strong className={`anomaly-${prediction.anomaly_status?.toLowerCase()}`}>{prediction.anomaly_status}</strong>
                  <p>Latest modal price: ₹{money(prediction.current_price)}. Prior 30-record mean: ₹{money(prediction.anomaly_baseline_mean)}; standard deviation: ₹{money(prediction.decision_support?.anomaly_baseline_std)}.</p>
                  <small>{prediction.decision_support?.anomaly_method}</small>
                </article>
                <article className="decision-detail risk-detail">
                  <span className="section-kicker">COMBINED RISK CONTEXT</span>
                  <strong className={`risk-text-${prediction.risk?.toLowerCase()}`}>{prediction.risk} risk · {prediction.volatility_class} volatility</strong>
                  <p>{prediction.trend_label} forecast at {signed(movement)}; recent historical trend is {prediction.recent_trend}.</p>
                  {Number(prediction.predicted_price) < 0 && <small>Forecast is below ₹0; verify against local market prices before acting.</small>}
                </article>
              </section>}
            </section>
          ) : ['overview', 'forecast', 'trends', 'explainability', 'decisions'].includes(activeScreen) ? (
            <section className="empty-outlook" id="forecast">
              <div className="empty-icon"><TrendingUp size={21} /></div>
              <div><span className="section-kicker">{activeScreenInfo?.label || 'YOUR NEXT MOVE STARTS HERE'}</span><h3>{ready ? 'Your market is ready for a closer look.' : 'Choose a crop and market to reveal its outlook.'}</h3><p>Generate a real XGBoost forecast to populate this screen’s market data.</p></div>
              <span className="empty-index">OUTLOOK / 01</span>
            </section>
          ) : null}

          <section className="markets-section">
            <div className="markets-heading">
              <div><span className="section-kicker">ACROSS THE COUNTRY</span><h2>Where the market is moving</h2></div>
              <div className="market-tools">
                <div className="markets-context"><BarChart3 size={16} /><span>{selection.commodity_name || 'All commodities'}{selection.variety ? ` · ${selection.variety}` : ''}</span></div>
                <label className="sort-control"><span>SORT</span><select value={marketSort} onChange={(event) => setMarketSort(event.target.value)}><option value="change">% change</option><option value="current">Current price</option><option value="predicted" disabled={!selection.grade}>Predicted price</option><option value="risk">Lowest risk</option></select><ChevronDown size={13} /></label>
              </div>
            </div>
            {marketOutlookLoading && <div className="market-load"><LoaderCircle className="spin" size={15} /> Running the loaded XGBoost model across available market series…</div>}
            {marketError && <div className="market-notice"><CircleAlert size={15} /><span>{marketError} Showing observed market statistics where available.</span></div>}
            {marketForecasts.length > 0 && (
              <div className="opportunity-block">
                <div className="opportunity-head"><div><span className="section-kicker">TOP OPPORTUNITIES</span><p>Markets with positive next-day modelled change</p></div><span>{opportunities.length} identified</span></div>
                {opportunities.length ? <div className="opportunity-grid">{opportunities.slice(0, 3).map((market) => <article className="opportunity-item" key={`opp-${market.state_name}-${market.market_center_name}`}><span>{market.market_center_name} <i>·</i> {market.state_name}</span><strong className="positive-text">{signed(market.percentage_change)}</strong><small>₹{money(market.current_price)} <ArrowRight size={11} /> ₹{money(market.predicted_price)} / qtl</small><span className={`opportunity-risk risk-text-${market.risk.toLowerCase()}`}>{market.trend} · {market.risk} risk</span></article>)}</div> : <div className="no-opportunities">No positive next-day percentage changes in the available market series.</div>}
              </div>
            )}
            {marketRows.length ? (
              <div className="market-list">
                <div className="market-list-head"><span>RANK / MARKET</span><span>{marketForecasts.length ? 'CURRENT / QTL' : 'LATEST / QTL'}</span><span>{marketForecasts.length ? 'NEXT-DAY / QTL' : '30-DAY AVG.'}</span><span>{marketForecasts.length ? 'MODEL CHANGE' : '7-DAY MOVE'}</span><span>{marketForecasts.length ? 'TREND / RISK' : '30D VOLATILITY'}</span><span>ANOMALY</span></div>
                {sortedMarketRows.slice(0, 24).map((market, index) => (
                  <div className="market-row" key={`${market.state_name}-${market.district_name}-${market.market_center_name}`}>
                    <div className="market-name"><span className={`rank-number ${index === 0 ? 'rank-first' : ''}`}>{String(market.opportunity_rank || index + 1).padStart(2, '0')}</span><span><strong>{market.market_center_name}</strong><small>{market.district_name}, {market.state_name}</small></span></div>
                    <span className="market-current"><i>{marketForecasts.length ? 'Current' : 'Latest'}</i><strong>₹{money(market.current_price ?? market.latest_price)}</strong></span>
                    <span className="market-predicted"><i>{marketForecasts.length ? 'Next day' : '30-day avg.'}</i><strong>{marketForecasts.length ? `₹${money(market.predicted_price)}` : `₹${money(market.avg_price_30d)}`}</strong>{marketForecasts.length && Number(market.predicted_price) < 0 ? <small className="below-zero-note">Below ₹0 · verify locally</small> : null}</span>
                    <span className={`market-move ${Number(market.percentage_change ?? market.pct_change_7d) > 0 ? 'positive-text' : Number(market.percentage_change ?? market.pct_change_7d) < 0 ? 'negative-text' : ''}`}>{marketForecasts.length ? <>{Number(market.percentage_change) >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}{signed(market.percentage_change)}</> : signed(market.pct_change_7d)}</span>
                    <span className="market-signal">{marketForecasts.length ? <><b className={`trend-word ${market.trend?.toLowerCase() || 'unavailable'}`}>{market.trend || '—'}</b><small className={`risk-text-${market.risk?.toLowerCase() || 'unavailable'}`}>{market.risk ? `${market.risk} risk` : 'Risk —'}</small></> : <><b className="market-volatility">{market.volatility_30d}%</b><small>observed</small></>}</span>
                    <span className={`market-anomaly anomaly-${(market.anomaly_status || (market.is_anomaly ? 'HIGH' : 'NORMAL')).toLowerCase()}`}><i />{market.anomaly_status || (market.is_anomaly ? 'HIGH' : 'NORMAL')}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="markets-empty"><span className="markets-empty-icon"><BarChart3 size={19} /></span><p>{marketOutlookLoading ? 'Calculating model-backed market forecasts.' : selection.grade && marketOutlookLoaded ? 'No eligible market forecasts returned. Markets without sufficient history are omitted.' : selection.commodity_name ? 'Market comparisons will appear as data loads.' : 'Select a commodity to compare prices across mandis.'}</p></div>
            )}
            <div className="markets-foot"><span>{marketForecasts.length ? 'Next-day prices use the loaded XGBoost model for each market series.' : 'Source: historical mandi arrivals and modal prices'}</span><span>INDIA MARKET WATCH <ArrowRight size={13} /></span></div>
          </section>
        </div>
      </main>

      <footer className="footer"><a className="brand footer-brand" href="#overview"><span className="brand-mark"><Sprout size={18} /></span><span className="brand-name">fieldnotes<span>.</span></span></a><span>Better signals. Stronger harvests.</span><span>© 2026 FIELDNOTES · BUILT FOR INDIA</span></footer>
    </div>
  )
}

export default App
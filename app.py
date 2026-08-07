import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Guru Asset Analyzer", layout="centered")

st.title("📊 Multi-Asset Strategy Analyzer")
st.write("Input any stock ticker, new IPO, or cryptocurrency to evaluate its optimal holding window.")

# User input field
ticker_symbol = st.text_input("Enter Asset Ticker (e.g., AAPL, BTC-USD, KVUE):", "").upper()

if ticker_symbol:
    with st.spinner(f"Scrubbing live market data for {ticker_symbol}..."):
        ticker = yf.Ticker(ticker_symbol)
        
        try:
            info = ticker.info
            financials = ticker.financials
            cashflow = ticker.cashflow
            history = ticker.history(period="1y")
            
            # Detect Asset Class Profile
            is_crypto = info.get('quoteType') == 'CRYPTOCURRENCY' or 'crypto' in str(info.get('market', '')).lower() or '-' in ticker_symbol
            
            if history.empty:
                st.error("No trading history found for this ticker symbol. Please verify the spelling.")
                st.stop()

            # ==========================================
            # 1. TECHNICAL MOMENTUM LAYER (ALL ASSETS)
            # ==========================================
            close_prices = history['Close']
            ma_50 = close_prices.rolling(window=min(50, len(close_prices))).mean().iloc[-1]
            current_price = close_prices.iloc[-1]
            
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=min(14, len(close_prices))).mean().iloc[-1]
            loss = (-delta.where(delta < 0, 0)).rolling(window=min(14, len(close_prices))).mean().iloc[-1]
            rs = gain / (loss if loss != 0 else 1)
            rsi = 100 - (100 / (1 + rs))
            
            short_term_bullish = current_price > ma_50 and rsi < 70

            # ==========================================
            # 2. FUNDAMENTAL CHECKS (STOCKS ONLY)
            # ==========================================
            results = {}
            long_term_score = 0
            total_metrics = 0
            
            if not is_crypto and not financials.empty and not cashflow.empty:
                def get_financial_row(df, possible_names):
                    clean_index = [str(idx).lower().replace(" ", "").replace("_", "") for idx in df.index]
                    for name in possible_names:
                        target = name.lower().replace(" ", "").replace("_", "")
                        if target in clean_index:
                            return df.iloc[clean_index.index(target)]
                    return None

                revenue_row = get_financial_row(financials, ['Total Revenue', 'TotalRevenue', 'Revenue'])
                if revenue_row is not None and len(revenue_row) >= 2:
                    rev_growth = (revenue_row.iloc[0] - revenue_row.iloc[1]) / (revenue_row.iloc[1] if revenue_row.iloc[1] != 0 else 1)
                    results['Revenue Growth (>10%)'] = (rev_growth > 0.10, f"{rev_growth:.1%}")
                elif revenue_row is not None and len(revenue_row) == 1:
                    results['Revenue Growth (>10%)'] = (False, "New IPO (Single Year Data Only)")
                else:
                    results['Revenue Growth (>10%)'] = (False, "Data Missing")

                net_inc_row = get_financial_row(financials, ['Net Income', 'NetIncome', 'Net Income Common Stockholders'])
                if net_inc_row is not None and len(net_inc_row) >= 2:
                    eps_growth_yoy = (net_inc_row.iloc[0] - net_inc_row.iloc[1]) / abs(net_inc_row.iloc[1]) if net_inc_row.iloc[1] != 0 else 0
                    results['EPS Growth (>12%)'] = (eps_growth_yoy > 0.12, f"{eps_growth_yoy:.1%}")
                else:
                    results['EPS Growth (>12%)'] = (False, "Data Missing")
                
                fcf_row = get_financial_row(cashflow, ['Free Cash Flow', 'FreeCashFlow', 'Total Cash From Operating Activities'])
                if fcf_row is not None and revenue_row is not None:
                    fcf_margin = fcf_row.iloc[0] / revenue_row.iloc[0] if revenue_row.iloc[0] != 0 else 0
                    results['FCF Margin (>10%)'] = (fcf_margin > 0.10, f"{fcf_margin:.1%}")
                else:
                    results['FCF Margin (>10%)'] = (False, "Data Missing")
                
                current_ratio = info.get('currentRatio', 0)
                results['Current Ratio (>1.5)'] = (current_ratio > 1.5 if current_ratio else False, f"{current_ratio:.2f}" if current_ratio else "N/A")
                
                pe_ratio = info.get('trailingPE', None)
                results['P/E Ratio (<20)'] = (pe_ratio < 20 if pe_ratio else False, f"{pe_ratio:.1f}" if pe_ratio else "N/A")
                
                long_term_score = sum([1 for passed, _ in results.values() if passed])
                total_metrics = len(results)

            # ==========================================
            # 3. CRITICAL DECISION STRATEGY BANNER
            # ==========================================
            st.markdown("---")
            st.header("🎯 AGENT STRATEGY VERDICT")
            
            # Determine asset maturity to contextualize warnings
            max_hist_len = len(ticker.history(period="max"))
            is_new_asset = max_hist_len < 252
            
            if is_crypto:
                if short_term_bullish:
                    st.warning("### 🪙 RECOMMENDATION: HIGH-RISK CRYPTO TREND TRADE")
                    st.metric(label="Suggested Trading Window", value="Active Momentum Target")
                    st.info(f"**Justification:** Digital asset without corporate fundamental metrics. Immediate short-term momentum patterns are bullish. Track closely using explicit risk stops.")
                else:
                    st.error("### 🔴 RECOMMENDATION: CRYPTO MOMENTUM IS DOWN (AVOID/WAIT)")
                    st.metric(label="Suggested Trading Window", value="0 Days (No Entry Trend)")
                    st.info(f"**Justification:** Digital asset momentum structures are broken. Price is trading beneath structural short-term moving averages. Wait for trend reversal.")
            else:
                if is_new_asset:
                    if short_term_bullish:
                        st.warning("### 🟡 RECOMMENDATION: SHORT-TERM HODL / IPO TREND SWING")
                        st.metric(label="Suggested Holding Duration", value="2 to 8 Weeks (High Volatility)")
                        st.info(f"**Justification:** This equity has less than 1 year of public trading history. Long-term corporate compounding quality cannot be reliably scrubbed yet. However, near-term buying pressure is strong. Play the technical momentum trend, but monitor closely.")
                    else:
                        st.error("### 🔴 RECOMMENDATION: AVOID NEW ASSET (MOMENTUM DOWN)")
                        st.metric(label="Suggested Holding Duration", value="0 Days (Immediate Skip)")
                        st.info(f"**Justification:** New public listing lacking long-term foundational data, and near-term price momentum is downward. Highly dangerous setup; avoid.")
                else:
                    if long_term_score >= 3:
                        st.success("### 🟢 RECOMMENDATION: LONG-TERM INVESTING HOLD")
                        st.metric(label="Suggested Holding Duration", value="3 to 10+ Years")
                        st.info(f"**Justification:** Asset qualifies on mature corporate stability standards ({long_term_score}/{total_metrics}). Built to anchor long-term wealth portfolios.")
                    elif long_term_score < 3 and short_term_bullish:
                        st.warning("### 🟡 RECOMMENDATION: SHORT-TERM MOMENTUM TRADE ONLY")
                        st.metric(label="Suggested Holding Duration", value="2 to 6 Weeks (Strict Stop-Loss)")
                        st.info(f"**Justification:** Weak corporate balance sheets or margins ({long_term_score}/{total_metrics}), but short-term price breakout momentum is strong. Ride the short swing, do not hold permanently.")
                    else:
                        st.error("### 🔴 RECOMMENDATION: DO NOT ENTER (AVOID ASSET)")
                        st.metric(label="Suggested Holding Duration", value="0 Days (Immediate Skip)")
                        st.info(f"**Justification:** Equity fails baseline fundamental checklists and lacks structural short-term buying pressure.")

            # ==========================================
            # 4. EXPANDABLE VIEW DATA
            # ==========================================
            st.markdown("---")
            with st.expander("📊 View Technical & Analytical Indicators"):
                st.write(f"**Current Price:** ${current_price:,.2f} | **Short-Term Baseline MA:** ${ma_50:,.2f}")
                st.write(f"**14-Day RSI Momentum Indicator:** {rsi:.1f}")
                if not is_crypto and results:
                    st.write("---")
                    st.write("### Corporate Fundamental Checklist Summary:")
                    for metric, (passed, value) in results.items():
                        st.write(f"* **{metric}**: {value} — {'✅ PASS' if passed else '❌ FAIL'}")

            # ==========================================
            # 5. HISTORICAL SIMULATION DATA ENGINE
            # ==========================================
            max_hist = ticker.history(period="max")
            if len(max_hist) >= 5:
                total_trading_days = len(max_hist)
                years_trading = total_trading_days / 252.3
                years_trading_capped = max(years_trading, 0.01)
                
                asset_true_cagr = (max_hist['Close'].iloc[-1] / max_hist['Close'].iloc[0]) ** (1 / years_trading_capped) - 1
                
                rolling_max = max_hist['Close'].cummax()
                max_crash = ((max_hist['Close'] - rolling_max) / rolling_max).min()
                
                st.markdown("---")
                st.subheader("💰 Asset Lifespan Risk & Return Simulator")
                
                if years_trading < 1.0:
                    st.caption(f"🚨 **New Asset Profile:** This ticker has a short public footprint of only **{total_trading_days} trading days** (~{years_trading*12:.1f} months). Performance projections are high-risk.")
                else:
                    st.caption(f"Simulating a $1,000 baseline investment across the available **{years_trading:.1f}-year** lifecycle of **{ticker_symbol}**.")
                
                principal = 1000.0
                
                if years_trading < 1.0:
                    v1 = principal * (1 + asset_true_cagr)**(1/12)
                    v2 = principal * (1 + asset_true_cagr)**(3/12)
                    v3 = principal * (1 + asset_true_cagr)**(6/12)
                    
                    c1, c2, c3 = st.columns(3)
                    with c1: st.metric(label="Proj. 1-Month Value", value=f"${v1:,.2f}", delta=f"+${v1 - principal:,.2f}" if v1 >= principal else f"${v1 - principal:,.2f}")
                    with c2: st.metric(label="Proj. 3-Month Value", value=f"${v2:,.2f}", delta=f"+${v2 - principal:,.2f}" if v2 >= principal else f"${v2 - principal:,.2f}")
                    with c3: st.metric(label="Proj. 6-Month Value", value=f"${v3:,.2f}", delta=f"+${v3 - principal:,.2f}" if v3 >= principal else f"${v3 - principal:,.2f}")
                else:
                    v1 = principal * (1 + asset_true_cagr)**1
                    v5 = principal * (1 + asset_true_cagr)**min(5, max(1, int(years_trading)))
                    v10 = principal * (1 + asset_true_cagr)**min(10, max(1, int(years_trading)))
                    
                    label_5y = f"{min(5, max(1, int(years_trading)))} Year Value"
                    label_10y = f"{min(10, max(1, int(years_trading)))} Year Value"
                    
                    c1, c2, c3 = st.columns(3)
                    with c1: st.metric(label="1 Year Value", value=f"${v1:,.2f}", delta=f"+${v1 - principal:,.2f}" if v1 >= principal else f"${v1 - principal:,.2f}")
                    with c2: st.metric(label=label_5y, value=f"${v5:,.2f}", delta=f"+${v5 - principal:,.2f}" if v5 >= principal else f"${v5 - principal:,.2f}")
                    with c3: st.metric(label=label_10y, value=f"${v10:,.2f}", delta=f"+${v10 - principal:,.2f}" if v10 >= principal else f"${v10 - principal:,.2f}")
                
                st.warning(f"⚠️ **Volatility Risk Profile:** The annualized performance trends at **{asset_true_cagr:.1%}**. However, holding this asset meant enduring a maximum peak-to-trough market correction of **{max_crash:.1%}**.")

        except Exception as e:
            st.error(f"Error executing analysis engine metrics: {e}")

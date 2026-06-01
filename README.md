# eCommerce Funnel Drop-off Analyser

## Overview
End-to-end product analytics dashboard analysing 8M+ real eCommerce 
events from a cosmetics store to find where users drop out of the 
purchase funnel and how much revenue is being lost.

## Dataset
REES46 eCommerce Events — Cosmetics Shop  
Source: https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-cosmetics-shop  
Size: 8M+ events | Oct 2019 — Nov 2019

## Tech Stack
- Python + Pandas — loading and cleaning
- DuckDB — SQL CTEs on dataframes
- Plotly — interactive charts
- Streamlit — live dashboard

## How to Run
pip install -r requirements.txt
streamlit run app.py

## Questions Answered
1. Where do users drop off in the funnel?
2. Which categories convert best and worst?
3. Which brands have the highest CVR?
4. Is conversion improving month over month?
5. What time and day converts best?
6. How much revenue is lost to abandoned carts?
7. Do higher-price products convert less?
8. How do repeat buyers differ from one-time buyers?


## Key Findings
(Based on 8,169,123 events — Oct 2019 & Nov 2019)

### Funnel Overview
- Total sessions analysed      : 1,677,368
- View → Cart conversion       : 17.8%  (1,378,454 users left without carting)
- Cart → Purchase conversion   : 16.5%  (248,667 users carted but never bought)
- Overall CVR                  : 2.9%
- Biggest drop-off stage       : Cart → Purchase (83.5% of carters abandon)

## Limitations

### Dataset Limitations
- Dataset covers only October and November 2019 — just 2 months of data — so long-term seasonal trends cannot be identified.
- Data is from one specific cosmetics store only — findings cannot
  be generalised to other industries or product types
- No device type column in the raw data — mobile vs desktop
  analysis is not possible without additional data

### Technical Limitations
- Analysis loads entire dataset into RAM — may be slow or crash
  on machines with less than 8GB of memory
- No real-time data — dashboard shows historical data only,
  not live events
- Checkout stage is missing — the dataset only has view, cart,
  and purchase events so the cart-to-checkout drop cannot be
  measured separately from cart-to-purchase

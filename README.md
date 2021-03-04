# CryptoBot (CRBR)

## Install
`virtualenv venv && source venv/bin/activate && pip install -r requirements.txt`

## Run
- `python run_crawler.py`
- `python run_test.py`

## Terminology
- *Deal* - real deal, what we opened/closed (bought/sold).
- *Trade* - socket trade from stream.
- *Position* - position between min and max buy price represented by price. Can contain deal or be empty. 
- *Judge* - judge that decides whether to keep or close deal when reaches desired profit. 

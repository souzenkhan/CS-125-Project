To run the tests on mac:

python3 -m pip install -r ./server/requirements.txt
python3 ./scripts/validate_restaurants.py ./data/restaurants.json
python3 -m pytest -q

To run the test on windows:

python -m pip install -r .\server\requirements.txt
python .\scripts\validate_restaurants.py .\data\restaurants.json
python -m pytest -q

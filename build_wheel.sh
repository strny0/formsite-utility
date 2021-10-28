rm -r ./dist/*
python3 setup.py sdist bdist_wheel
pip3 install twine
twine upload ./dist/*
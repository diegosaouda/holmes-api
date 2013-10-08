mongodatabase = holmes

test: mongo_test unit integration

unit:
	@coverage run --branch `which nosetests` -vv --with-yanc -s tests/unit/
	@coverage report -m --fail-under=80

integration: mongo kill_run run_daemon
	@`which nosetests` -vv --with-yanc -s tests/integration/

tox:
	@PATH=$$PATH:~/.pythonbrew/pythons/Python-2.6.*/bin/:~/.pythonbrew/pythons/Python-2.7.*/bin/:~/.pythonbrew/pythons/Python-3.0.*/bin/:~/.pythonbrew/pythons/Python-3.1.*/bin/:~/.pythonbrew/pythons/Python-3.2.3/bin/:~/.pythonbrew/pythons/Python-3.3.0/bin/ tox

setup:
	@pip install -U -e .\[tests\]

drop_mongo:
	@rm -rf /tmp/$(mongodatabase)/mongodata

kill_mongo:
	@ps aux | awk '(/mongod/ && $$0 !~ /awk/){ system("kill -9 "$$2) }'

mongo: kill_mongo
	@mkdir -p /tmp/$(mongodatabase)/mongodata
	@mongod --dbpath /tmp/$(mongodatabase)/mongodata --logpath /tmp/$(mongodatabase)/mongolog --port 6685 --quiet &
	@sleep 3

kill_mongo_test:
	@ps aux | awk '(/mongod.+test/ && $$0 !~ /awk/){ system("kill -9 "$$2) }'

mongo_test: kill_mongo_test
	@rm -rf /tmp/$(mongodatabase)/mongotestdata && mkdir -p /tmp/$(mongodatabase)/mongotestdata
	@mongod --dbpath /tmp/$(mongodatabase)/mongotestdata --logpath /tmp/$(mongodatabase)/mongotestlog --port 6686 --quiet &
	@sleep 3

kill_run:
	@ps aux | awk '(/.+holmes-api.+/ && $$0 !~ /awk/){ system("kill -9 "$$2) }'

run_daemon:
	@holmes-api -vvv -c ./holmes/config/local.conf &

run:
	@holmes-api -vvv -c ./holmes/config/local.conf

worker: mongo
	@holmes-worker -vvv -c ./holmes/config/local.conf

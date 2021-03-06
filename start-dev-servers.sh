#!/bin/bash
ps aux | grep [m]ysql
if [ $? -eq 1 ]
then 
	nohup mysql.server start 
fi
mongoversion=`ls -trh /usr/local/Cellar/mongodb/ |  head -n 2 | tail -n 1`
nohup mongod &
pg_ctl -D /usr/local/var/postgres -l /usr/local/var/log/postgres start
echo "I'd suggest installing https://github.com/remysaissy/mongodb-macosx-prefspane instead of using the ./start-dev-servers.sh script
"